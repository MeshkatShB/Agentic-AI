"""File-related tools."""

import os
from pathlib import Path
from typing import Dict, Any, List
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
    """Tool for searching local files."""
    
    @property
    def name(self) -> str:
        return "search_local_files"
    
    @property
    def description(self) -> str:
        return "Search indexed local files by query"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5
                },
                "file_type": {
                    "type": "string",
                    "description": "Filter by file type (pdf, docx, txt, md)",
                    "enum": ["pdf", "docx", "txt", "md", "all"],
                    "default": "all"
                }
            },
            "required": ["query"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the search."""
        query = kwargs.get("query")
        top_k = kwargs.get("top_k", 5)
        file_type = kwargs.get("file_type", "all")
        
        try:
            # Get vector store
            vector_store = get_vector_store()
            
            # Build filter
            filter_dict = {}
            if file_type != "all":
                filter_dict["file_type"] = file_type
            
            # Search documents
            results = await vector_store.search(
                query=query,
                k=top_k,
                filter=filter_dict if filter_dict else None,
                collection_name="documents"
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "file": result["metadata"].get("file_path", ""),
                    "content": result["document"][:500],  # First 500 chars
                    "score": result["score"],
                    "metadata": result["metadata"]
                })
            
            return ToolResult(
                success=True,
                output=formatted_results,
                metadata={"count": len(formatted_results)}
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
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
