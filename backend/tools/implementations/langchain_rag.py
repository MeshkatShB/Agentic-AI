"""LangChain-based RAG tools."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    Docx2txtLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
import requests
import json

from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class OllamaLLM(LLM):
    """Custom LangChain LLM for Ollama."""
    
    model: str = "qwen3:latest"
    base_url: str = "http://localhost:11434"
    
    @property
    def _llm_type(self) -> str:
        return "ollama"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Ollama API."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.7),
                        "top_p": kwargs.get("top_p", 0.9),
                        "max_tokens": kwargs.get("max_tokens", 2000)
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return f"Error: {str(e)}"


class RAGTool(BaseTool):
    """Advanced RAG tool using LangChain."""
    
    def __init__(self):
        super().__init__()
        self.vectorstore = None
        self.qa_chain = None
        self.documents_path = Path("data")
        self.chroma_path = Path("chroma_db")
        
    @property
    def name(self) -> str:
        return "rag_search"
    
    @property
    def description(self) -> str:
        return "Search and retrieve information from indexed documents using advanced RAG (Retrieval-Augmented Generation)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question or search query"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of relevant documents to retrieve",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "reindex": {
                    "type": "boolean",
                    "description": "Whether to reindex documents before searching",
                    "default": False
                }
            },
            "required": ["query"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def _load_documents(self) -> List[Document]:
        """Load documents from the data directory."""
        documents = []
        
        if not self.documents_path.exists():
            logger.warning(f"Documents path {self.documents_path} does not exist")
            return documents
        
        for file_path in self.documents_path.rglob("*"):
            if not file_path.is_file():
                continue
                
            try:
                loader = None
                suffix = file_path.suffix.lower()
                
                if suffix == ".txt":
                    loader = TextLoader(str(file_path), encoding="utf-8")
                elif suffix == ".pdf":
                    loader = PyPDFLoader(str(file_path))
                elif suffix == ".docx":
                    loader = Docx2txtLoader(str(file_path))
                elif suffix == ".html":
                    loader = UnstructuredHTMLLoader(str(file_path))
                elif suffix == ".md":
                    loader = UnstructuredMarkdownLoader(str(file_path))
                else:
                    # Try as text file
                    try:
                        loader = TextLoader(str(file_path), encoding="utf-8")
                    except:
                        continue
                
                if loader:
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata["source"] = str(file_path)
                        doc.metadata["filename"] = file_path.name
                        doc.metadata["file_type"] = suffix.lstrip(".")
                    documents.extend(docs)
                    logger.info(f"Loaded {len(docs)} documents from {file_path}")
                    
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                continue
        
        return documents
    
    async def _initialize_vectorstore(self, reindex: bool = False) -> bool:
        """Initialize the vector store."""
        try:
            # Create embeddings
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Check if we need to reindex or if vectorstore doesn't exist
            if reindex or not self.chroma_path.exists() or not any(self.chroma_path.iterdir()):
                logger.info("Indexing documents...")
                
                # Load documents
                documents = await self._load_documents()
                if not documents:
                    logger.warning("No documents found to index")
                    return False
                
                # Split documents
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len,
                    separators=["\n\n", "\n", " ", ""]
                )
                
                split_docs = text_splitter.split_documents(documents)
                logger.info(f"Split into {len(split_docs)} chunks")
                
                # Create vectorstore
                self.vectorstore = Chroma.from_documents(
                    documents=split_docs,
                    embedding=embeddings,
                    persist_directory=str(self.chroma_path)
                )
                self.vectorstore.persist()
                logger.info("Documents indexed successfully")
            else:
                # Load existing vectorstore
                self.vectorstore = Chroma(
                    persist_directory=str(self.chroma_path),
                    embedding_function=embeddings
                )
                logger.info("Loaded existing vectorstore")
            
            # Initialize QA chain
            llm = OllamaLLM(model=settings.DEFAULT_MODEL)
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=self.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 5}
                ),
                return_source_documents=True,
                verbose=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize vectorstore: {e}")
            return False
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute RAG search."""
        query = kwargs.get("query")
        top_k = kwargs.get("top_k", 5)
        reindex = kwargs.get("reindex", False)
        
        try:
            # Initialize vectorstore if needed
            if not self.vectorstore or reindex:
                success = await self._initialize_vectorstore(reindex=reindex)
                if not success:
                    return ToolResult(
                        success=False,
                        output=None,
                        error="Failed to initialize document index"
                    )
            
            # Update retriever with top_k
            self.qa_chain.retriever.search_kwargs["k"] = top_k
            
            # Run the query
            result = self.qa_chain({"query": query})
            
            # Format the response
            answer = result["result"]
            sources = []
            
            for doc in result.get("source_documents", []):
                sources.append({
                    "filename": doc.metadata.get("filename", "Unknown"),
                    "source": doc.metadata.get("source", "Unknown"),
                    "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                })
            
            return ToolResult(
                success=True,
                output={
                    "answer": answer,
                    "sources": sources,
                    "query": query
                },
                metadata={
                    "sources_count": len(sources),
                    "top_k": top_k
                }
            )
            
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=f"Search failed: {str(e)}"
            )


class DocumentSummarizerTool(BaseTool):
    """Tool to summarize documents."""
    
    @property
    def name(self) -> str:
        return "summarize_document"
    
    @property
    def description(self) -> str:
        return "Summarize a specific document or file"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the document to summarize"
                },
                "summary_length": {
                    "type": "string",
                    "description": "Length of summary",
                    "enum": ["short", "medium", "long"],
                    "default": "medium"
                }
            },
            "required": ["file_path"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute document summarization."""
        file_path = kwargs.get("file_path")
        summary_length = kwargs.get("summary_length", "medium")
        
        try:
            # Load the document
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}"
                )
            
            # Load document content
            loader = None
            suffix = path.suffix.lower()
            
            if suffix == ".txt":
                loader = TextLoader(str(path), encoding="utf-8")
            elif suffix == ".pdf":
                loader = PyPDFLoader(str(path))
            elif suffix == ".docx":
                loader = Docx2txtLoader(str(path))
            elif suffix == ".html":
                loader = UnstructuredHTMLLoader(str(path))
            elif suffix == ".md":
                loader = UnstructuredMarkdownLoader(str(path))
            else:
                loader = TextLoader(str(path), encoding="utf-8")
            
            documents = loader.load()
            content = "\n\n".join([doc.page_content for doc in documents])
            
            # Create summary prompt based on length
            length_instructions = {
                "short": "Provide a brief 2-3 sentence summary.",
                "medium": "Provide a comprehensive paragraph summary.",
                "long": "Provide a detailed summary with key points and main themes."
            }
            
            prompt = f"""Please summarize the following document. {length_instructions[summary_length]}

Document content:
{content[:4000]}  # Limit content to avoid token limits

Summary:"""
            
            # Use Ollama to generate summary
            llm = OllamaLLM(model=settings.DEFAULT_MODEL)
            summary = llm(prompt)
            
            return ToolResult(
                success=True,
                output={
                    "summary": summary,
                    "file_path": file_path,
                    "file_name": path.name,
                    "summary_length": summary_length,
                    "original_length": len(content)
                },
                metadata={
                    "file_type": suffix.lstrip("."),
                    "compression_ratio": len(summary) / len(content) if content else 0
                }
            )
            
        except Exception as e:
            logger.error(f"Document summarization failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=f"Summarization failed: {str(e)}"
            )
