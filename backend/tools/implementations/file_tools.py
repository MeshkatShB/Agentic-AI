"""File-related tools."""

import os
import re
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import pypdf
import docx
import markdown
from bs4 import BeautifulSoup
from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.config import settings
from backend.storage import get_vector_store
import logging

logger = logging.getLogger(__name__)


class SearchLocalFilesTool(BaseTool):
    """Enhanced RAG tool for searching local files with advanced semantic and keyword matching."""
    
    def __init__(self):
        super().__init__()
        self.vector_store = None
        self.embedding_model = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.document_metadata = []
        self._initialized = False
        
    @property
    def name(self) -> str:
        return "search_local_files"
    
    @property
    def description(self) -> str:
        return "Advanced search of indexed local files using semantic and keyword matching, optimized for Persian and multilingual content"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query or question"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of relevant documents to retrieve",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "search_type": {
                    "type": "string",
                    "description": "Type of search to perform",
                    "enum": ["semantic", "keyword", "hybrid"],
                    "default": "hybrid"
                },
                "file_type": {
                    "type": "string",
                    "description": "Filter by file type",
                    "enum": ["html", "pdf", "docx", "txt", "md", "all"],
                    "default": "all"
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum relevance score (0.0-1.0)",
                    "default": 0.3,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "reindex": {
                    "type": "boolean",
                    "description": "Whether to reindex documents",
                    "default": False
                }
            },
            "required": ["query"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def _initialize_models(self):
        """Initialize embedding and TF-IDF models."""
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {settings.EMBEDDING_MODEL}")
            
            # Initialize TF-IDF vectorizer for keyword search
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words=None,  # Keep stop words for Persian
                ngram_range=(1, 3),
                min_df=1,
                max_df=0.95
            )
            
            self._initialized = True
            logger.info("Models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise
    
    async def _semantic_search(self, query: str, k: int, file_type: str = "all") -> List[Dict]:
        """Perform semantic search using embeddings."""
        try:
            # Build filter
            filter_dict = {}
            if file_type != "all":
                filter_dict["file_type"] = file_type
            
            # Search using vector store
            results = await self.vector_store.search(
                query=query,
                k=k * 2,  # Get more results for better ranking
                filter=filter_dict if filter_dict else None,
                collection_name="documents"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def _keyword_search(self, query: str, k: int, file_type: str = "all") -> List[Dict]:
        """Perform keyword search using TF-IDF."""
        try:
            if self.tfidf_matrix is None or self.tfidf_vectorizer is None:
                logger.warning("TF-IDF index not available")
                return []
            
            if not self.document_metadata:
                logger.warning("Document metadata not available, trying to reload...")
                # Try to reload documents
                documents, metadatas, chunk_ids = await self._load_and_chunk_documents()
                if documents:
                    self.document_metadata = metadatas
                    await self._build_tfidf_index(documents)
                    logger.info(f"Reloaded {len(documents)} documents")
                else:
                    logger.warning("No documents found to reload")
                    return []
            
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Transform query
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Get top results
            top_indices = similarities.argsort()[-k:][::-1]
            
            results = []
            for idx in top_indices:
                if similarities[idx] > 0:  # Only include positive similarities
                    # Check if index is valid
                    if idx >= len(self.document_metadata):
                        logger.warning(f"Index {idx} out of bounds for document_metadata (length: {len(self.document_metadata)})")
                        continue
                    
                    # Get chunk_id safely
                    metadata = self.document_metadata[idx]
                    chunk_id = metadata.get("chunk_id")
                    
                    if not chunk_id:
                        logger.warning(f"No chunk_id found for index {idx}")
                        continue
                    
                    # Get document from vector store
                    doc_results = await self.vector_store.get_by_ids(
                        [chunk_id],
                        collection_name="documents"
                    )
                    
                    if doc_results:
                        doc = doc_results[0]
                        results.append({
                            "id": doc["id"],
                            "document": doc["document"],
                            "metadata": doc["metadata"],
                            "score": float(similarities[idx])
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _combine_results(self, semantic_results: List[Dict], keyword_results: List[Dict], 
                        query: str, k: int) -> List[Dict]:
        """Combine semantic and keyword search results with advanced ranking."""
        # Create a combined score for each result
        combined_results = {}
        
        # Process semantic results
        for result in semantic_results:
            doc_id = result.get("id", result.get("metadata", {}).get("chunk_id", ""))
            if doc_id:
                combined_results[doc_id] = {
                    "document": result["document"],
                    "metadata": result["metadata"],
                    "semantic_score": result.get("score", 0.0),
                    "keyword_score": 0.0,
                    "combined_score": 0.0,
                    "source": "semantic"
                }
        
        # Process keyword results
        for result in keyword_results:
            doc_id = result.get("id", result.get("metadata", {}).get("chunk_id", ""))
            if doc_id in combined_results:
                combined_results[doc_id]["keyword_score"] = result.get("score", 0.0)
                combined_results[doc_id]["source"] = "hybrid"
            else:
                combined_results[doc_id] = {
                    "document": result["document"],
                    "metadata": result["metadata"],
                    "semantic_score": 0.0,
                    "keyword_score": result.get("score", 0.0),
                    "combined_score": 0.0,
                    "source": "keyword"
                }
        
        # Calculate combined scores with weighted average
        for doc_id, result in combined_results.items():
            semantic_weight = 0.7  # Favor semantic search
            keyword_weight = 0.3
            
            result["combined_score"] = (
                semantic_weight * result["semantic_score"] + 
                keyword_weight * result["keyword_score"]
            )
        
        # Sort by combined score and return top k
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        return sorted_results[:k]
    
    async def _initialize_vector_store(self, reindex: bool = False):
        """Initialize the vector store with documents."""
        try:
            self.vector_store = get_vector_store()
            await self.vector_store.initialize()
            
            # Check if we need to reindex
            if reindex or not Path(settings.CHROMA_PATH).exists() or not any(Path(settings.CHROMA_PATH).iterdir()):
                logger.info("Indexing documents...")
                
                # Load and chunk documents
                documents, metadatas, chunk_ids = await self._load_and_chunk_documents()
                
                if not documents:
                    logger.warning("No documents found to index")
                    return False
                
                # Add to vector store
                await self.vector_store.add_documents(
                    documents=documents,
                    metadatas=metadatas,
                    ids=chunk_ids,
                    collection_name="documents"
                )
                
                # Build TF-IDF index
                await self._build_tfidf_index(documents)
                self.document_metadata = metadatas
                
                logger.info(f"Successfully indexed {len(documents)} document chunks")
            else:
                # Load existing index
                logger.info("Loading existing document index...")
                
                # Try to load existing TF-IDF index first
                tfidf_path = Path(settings.CHROMA_PATH) / "tfidf_index.pkl"
                if tfidf_path.exists():
                    try:
                        import pickle
                        with open(tfidf_path, 'rb') as f:
                            data = pickle.load(f)
                            self.tfidf_vectorizer = data['vectorizer']
                            self.tfidf_matrix = data['matrix']
                            self.document_metadata = data['metadata']
                        logger.info(f"Loaded existing TF-IDF index with {len(self.document_metadata)} metadata entries")
                        logger.info(f"TF-IDF matrix shape: {self.tfidf_matrix.shape if self.tfidf_matrix is not None else 'None'}")
                    except Exception as e:
                        logger.warning(f"Failed to load existing TF-IDF index: {e}, rebuilding...")
                        # Fall back to rebuilding
                        documents, metadatas, chunk_ids = await self._load_and_chunk_documents()
                        if documents:
                            await self._build_tfidf_index(documents)
                            self.document_metadata = metadatas
                            logger.info(f"Rebuilt TF-IDF index with {len(documents)} chunks")
                        else:
                            logger.warning("No documents found to rebuild index")
                            return False
                else:
                    logger.warning("No existing TF-IDF index found, rebuilding...")
                    # Load documents and rebuild index
                    documents, metadatas, chunk_ids = await self._load_and_chunk_documents()
                    if documents:
                        await self._build_tfidf_index(documents)
                        self.document_metadata = metadatas
                        logger.info(f"Rebuilt TF-IDF index with {len(documents)} chunks")
                    else:
                        logger.warning("No documents found to rebuild index")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            return False
    
    async def _load_and_chunk_documents(self) -> tuple:
        """Load and chunk documents from the data directory."""
        data_dir = Path("data")
        if not data_dir.exists():
            logger.warning("Data directory not found")
            return [], [], []
        
        documents = []
        metadatas = []
        chunk_ids = []
        
        supported_extensions = ['.html', '.pdf', '.docx', '.txt', '.md']
        files_processed = 0
        
        for file_path in data_dir.rglob('*'):
            if not file_path.is_file() or file_path.suffix.lower() not in supported_extensions:
                continue
            
            try:
                content = await self._read_file_content(file_path)
                if not content.strip():
                    continue
                
                # Smart chunking
                chunks = self._smart_chunk_text(content)
                
                for chunk in chunks:
                    documents.append(chunk["text"])
                    metadatas.append({
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_type": file_path.suffix.lower().lstrip('.'),
                        "chunk_id": chunk["chunk_id"],
                        "start_pos": chunk["start_pos"],
                        "end_pos": chunk["end_pos"],
                        "is_complete": chunk["is_complete"],
                        "content_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                        "word_count": len(chunk["text"].split()),
                        "char_count": len(chunk["text"]),
                        "indexed_at": datetime.utcnow().isoformat()
                    })
                    chunk_ids.append(chunk["chunk_id"])
                
                files_processed += 1
                logger.info(f"Processed {file_path.name}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue
        
        logger.info(f"Processed {files_processed} files, created {len(documents)} chunks")
        return documents, metadatas, chunk_ids
    
    def _smart_chunk_text(self, text: str, max_size: int = None) -> List[Dict[str, Any]]:
        """Advanced text chunking with semantic boundaries."""
        if max_size is None:
            max_size = settings.CHUNK_SIZE
            
        if len(text) <= max_size:
            return [{
                "text": text,
                "chunk_id": hashlib.md5(text.encode()).hexdigest()[:8],
                "start_pos": 0,
                "end_pos": len(text),
                "is_complete": True
            }]
        
        chunks = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        for para_idx, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) == 0:
                continue
                
            if len(paragraph) <= max_size:
                chunks.append({
                    "text": paragraph.strip(),
                    "chunk_id": f"para_{para_idx}_{hashlib.md5(paragraph.encode()).hexdigest()[:8]}",
                    "start_pos": text.find(paragraph),
                    "end_pos": text.find(paragraph) + len(paragraph),
                    "is_complete": True
                })
            else:
                # Split long paragraphs by sentences
                sentences = re.split(r'[.!?؟۔]\s+', paragraph)
                current_chunk = ""
                chunk_start = text.find(paragraph)
                
                for sent_idx, sentence in enumerate(sentences):
                    if len(sentence.strip()) == 0:
                        continue
                        
                    if len(current_chunk) + len(sentence) <= max_size:
                        current_chunk += (" " + sentence if current_chunk else sentence)
                    else:
                        if current_chunk:
                            chunks.append({
                                "text": current_chunk.strip(),
                                "chunk_id": f"sent_{para_idx}_{sent_idx}_{hashlib.md5(current_chunk.encode()).hexdigest()[:8]}",
                                "start_pos": chunk_start,
                                "end_pos": chunk_start + len(current_chunk),
                                "is_complete": True
                            })
                        current_chunk = sentence
                        chunk_start = text.find(sentence)
                
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_id": f"sent_{para_idx}_final_{hashlib.md5(current_chunk.encode()).hexdigest()[:8]}",
                        "start_pos": chunk_start,
                        "end_pos": chunk_start + len(current_chunk),
                        "is_complete": True
                    })
        
        return chunks
    
    async def _read_file_content(self, file_path: Path) -> str:
        """Read content from various file types."""
        try:
            if file_path.suffix.lower() == '.html':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                return re.sub(r'\s+', ' ', text)
            
            elif file_path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text.strip()
            
            elif file_path.suffix.lower() == '.docx':
                doc = docx.Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text.strip()
            
            else:  # .txt, .md
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    return re.sub(r'\s+', ' ', content)
        
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return ""
    
    async def _build_tfidf_index(self, documents: List[str]):
        """Build TF-IDF index for keyword search."""
        try:
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
            logger.info(f"Built TF-IDF index with {self.tfidf_matrix.shape[0]} documents")
            
            # Save the TF-IDF index to disk
            tfidf_path = Path(settings.CHROMA_PATH) / "tfidf_index.pkl"
            tfidf_path.parent.mkdir(parents=True, exist_ok=True)
            
            import pickle
            with open(tfidf_path, 'wb') as f:
                pickle.dump({
                    'vectorizer': self.tfidf_vectorizer,
                    'matrix': self.tfidf_matrix,
                    'metadata': self.document_metadata
                }, f)
            
            logger.info(f"Saved TF-IDF index to {tfidf_path}")
            
        except Exception as e:
            logger.error(f"Failed to build TF-IDF index: {e}")
            self.tfidf_matrix = None
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the enhanced RAG search."""
        query = kwargs.get("query", "").strip()
        top_k = min(kwargs.get("top_k", 5), settings.MAX_RETRIEVAL_RESULTS)
        search_type = kwargs.get("search_type", "hybrid")
        file_type = kwargs.get("file_type", "all")
        min_score = kwargs.get("min_score", 0.3)
        reindex = kwargs.get("reindex", False)
        
        if not query:
            return ToolResult(
                success=False,
                output=None,
                error="Query cannot be empty"
            )
        
        try:
            # Initialize models if needed
            if not self._initialized:
                await self._initialize_models()
            
            # Initialize vector store if needed
            if not self.vector_store or reindex:
                success = await self._initialize_vector_store(reindex=reindex)
                if not success:
                    return ToolResult(
                        success=False,
                        output=None,
                        error="Failed to initialize document index"
                    )
            
            # Perform search based on type
            if search_type == "semantic":
                results = await self._semantic_search(query, top_k, file_type)
            elif search_type == "keyword":
                results = await self._keyword_search(query, top_k, file_type)
            else:  # hybrid
                semantic_results = await self._semantic_search(query, top_k, file_type)
                keyword_results = await self._keyword_search(query, top_k, file_type)
                results = self._combine_results(semantic_results, keyword_results, query, top_k)
            
            # Filter by minimum score (but be more lenient for debugging)
            filtered_results = [
                result for result in results 
                if result.get("combined_score", result.get("score", 0)) >= (min_score * 0.1)  # Lower threshold for debugging
            ]
            
            # Log debugging information
            logger.info(f"Search query: '{query}'")
            logger.info(f"Total results before filtering: {len(results)}")
            logger.info(f"Results after filtering (min_score={min_score * 0.1}): {len(filtered_results)}")
            
            if results:
                logger.info(f"Top result scores: {[r.get('combined_score', r.get('score', 0)) for r in results[:3]]}")
                logger.info(f"Top result content preview: {results[0].get('document', '')[:200]}...")
            
            # Format results
            formatted_results = []
            for i, result in enumerate(filtered_results[:top_k]):
                formatted_results.append({
                    "rank": i + 1,
                    "file_name": result["metadata"].get("file_name", "Unknown"),
                    "file_path": result["metadata"].get("file_path", "Unknown"),
                    "file_type": result["metadata"].get("file_type", "Unknown"),
                    "content": result["document"][:500] + "..." if len(result["document"]) > 500 else result["document"],
                    "relevance_score": round(result.get("combined_score", result.get("score", 0)), 3),
                    "semantic_score": round(result.get("semantic_score", 0), 3),
                    "keyword_score": round(result.get("keyword_score", 0), 3),
                    "word_count": result["metadata"].get("word_count", 0),
                    "chunk_id": result["metadata"].get("chunk_id", ""),
                    "is_complete": result["metadata"].get("is_complete", True)
                })
            
            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "search_type": search_type,
                    "results": formatted_results,
                    "total_found": len(formatted_results),
                    "min_score": min_score
                },
                metadata={
                    "search_type": search_type,
                    "file_type_filter": file_type,
                    "min_score": min_score,
                    "total_results": len(formatted_results)
                }
            )
            
        except Exception as e:
            logger.error(f"Enhanced RAG search failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=f"Search failed: {str(e)}"
            )


class ReadFileTool(BaseTool):
    """Tool for reading file contents."""
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read the contents of a specific file"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Start line number (for text files)",
                    "default": 1
                },
                "end_line": {
                    "type": "integer",
                    "description": "End line number (for text files)",
                    "default": -1
                }
            },
            "required": ["file_path"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def execute(self, **kwargs) -> ToolResult:
        """Read the file."""
        file_path = kwargs.get("file_path")
        start_line = kwargs.get("start_line", 1)
        end_line = kwargs.get("end_line", -1)
        
        try:
            path = Path(file_path).resolve()
            
            # Check if path is allowed
            if not settings.is_path_allowed(path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Access denied: {file_path}"
                )
            
            # Check if file exists
            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}"
                )
            
            # Read file
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Apply line filtering
            if end_line == -1:
                content = ''.join(lines[start_line-1:])
            else:
                content = ''.join(lines[start_line-1:end_line])
            
            return ToolResult(
                success=True,
                output=content,
                metadata={
                    "file_path": str(path),
                    "total_lines": len(lines),
                    "size_bytes": path.stat().st_size
                }
            )
            
        except Exception as e:
            logger.error(f"Read file failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class ParseDocumentTool(BaseTool):
    """Tool for parsing various document formats."""
    
    @property
    def name(self) -> str:
        return "parse_document"
    
    @property
    def description(self) -> str:
        return "Extract text from PDF, DOCX, or other document formats"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the document to parse"
                },
                "extract_metadata": {
                    "type": "boolean",
                    "description": "Extract document metadata",
                    "default": False
                }
            },
            "required": ["file_path"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def execute(self, **kwargs) -> ToolResult:
        """Parse the document."""
        file_path = kwargs.get("file_path")
        extract_metadata = kwargs.get("extract_metadata", False)
        
        try:
            path = Path(file_path).resolve()
            
            # Check if path is allowed
            if not settings.is_path_allowed(path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Access denied: {file_path}"
                )
            
            # Check if file exists
            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}"
                )
            
            # Determine file type and parse
            ext = path.suffix.lower()
            content = ""
            metadata = {}
            
            if ext == ".pdf":
                content, metadata = self._parse_pdf(path, extract_metadata)
            elif ext == ".docx":
                content, metadata = self._parse_docx(path, extract_metadata)
            elif ext == ".md":
                content, metadata = self._parse_markdown(path, extract_metadata)
            elif ext in [".txt", ".log", ".csv"]:
                content = path.read_text(encoding='utf-8')
                if extract_metadata:
                    metadata = {
                        "lines": len(content.splitlines()),
                        "characters": len(content)
                    }
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unsupported file type: {ext}"
                )
            
            return ToolResult(
                success=True,
                output={
                    "content": content,
                    "metadata": metadata if extract_metadata else {}
                },
                metadata={
                    "file_type": ext,
                    "file_size": path.stat().st_size
                }
            )
            
        except Exception as e:
            logger.error(f"Parse document failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
    
    def _parse_pdf(self, path: Path, extract_metadata: bool):
        """Parse PDF file."""
        content = []
        metadata = {}
        
        with open(path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            
            if extract_metadata:
                info = reader.metadata
                if info:
                    metadata = {
                        "title": info.get('/Title', ''),
                        "author": info.get('/Author', ''),
                        "subject": info.get('/Subject', ''),
                        "pages": len(reader.pages)
                    }
            
            for page in reader.pages:
                content.append(page.extract_text())
        
        return '\n'.join(content), metadata
    
    def _parse_docx(self, path: Path, extract_metadata: bool):
        """Parse DOCX file."""
        doc = docx.Document(path)
        content = []
        metadata = {}
        
        for para in doc.paragraphs:
            content.append(para.text)
        
        if extract_metadata:
            props = doc.core_properties
            metadata = {
                "title": props.title or '',
                "author": props.author or '',
                "created": props.created.isoformat() if props.created else '',
                "modified": props.modified.isoformat() if props.modified else '',
                "paragraphs": len(doc.paragraphs)
            }
        
        return '\n'.join(content), metadata
    
    def _parse_markdown(self, path: Path, extract_metadata: bool):
        """Parse Markdown file."""
        content = path.read_text(encoding='utf-8')
        html = markdown.markdown(content)
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        metadata = {}
        if extract_metadata:
            metadata = {
                "headings": len(soup.find_all(['h1', 'h2', 'h3'])),
                "links": len(soup.find_all('a')),
                "code_blocks": len(soup.find_all('code'))
            }
        
        return text, metadata
