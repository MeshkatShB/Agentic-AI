"""Database-related tools."""

from typing import Dict, Any, List
import sqlite3
import json
from pathlib import Path
from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class DatabaseQueryTool(BaseTool):
    """Tool for querying local SQLite databases."""
    
    @property
    def name(self) -> str:
        return "query_database"
    
    @property
    def description(self) -> str:
        return "Query a local SQLite database (read-only by default)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "database_path": {
                    "type": "string",
                    "description": "Path to the SQLite database file"
                },
                "query": {
                    "type": "string",
                    "description": "SQL query to execute"
                },
                "parameters": {
                    "type": "array",
                    "description": "Query parameters for parameterized queries",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                    "default": []
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return",
                    "default": 100
                }
            },
            "required": ["database_path", "query"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        # Default to read permission, but check query for write operations
        return ToolPermission.DATABASE_READ
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute database query."""
        database_path = kwargs.get("database_path")
        query = kwargs.get("query")
        parameters = kwargs.get("parameters", [])
        limit = kwargs.get("limit", 100)
        
        try:
            # Check if path is allowed
            db_path = Path(database_path).resolve()
            if not settings.is_path_allowed(db_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Access denied: {database_path}"
                )
            
            # Check if database exists
            if not db_path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Database not found: {database_path}"
                )
            
            # Check if query is read-only
            is_write_query = self._is_write_query(query)
            if is_write_query:
                # Would need DATABASE_WRITE permission
                return ToolResult(
                    success=False,
                    output=None,
                    error="Write queries require DATABASE_WRITE permission"
                )
            
            # Execute query
            result = self._execute_query(db_path, query, parameters, limit)
            
            return ToolResult(
                success=True,
                output=result,
                metadata={
                    "database": str(db_path),
                    "row_count": len(result.get("rows", []))
                }
            )
            
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
    
    def _is_write_query(self, query: str) -> bool:
        """Check if query is a write operation."""
        query_upper = query.upper().strip()
        write_keywords = [
            "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
            "ALTER", "TRUNCATE", "REPLACE", "MERGE"
        ]
        
        for keyword in write_keywords:
            if query_upper.startswith(keyword):
                return True
        
        return False
    
    def _execute_query(
        self,
        db_path: Path,
        query: str,
        parameters: List,
        limit: int
    ) -> Dict:
        """Execute the SQL query."""
        
        conn = None
        cursor = None
        
        try:
            # Connect to database
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Apply limit if not already in query
            if limit and "LIMIT" not in query.upper():
                query = f"{query} LIMIT {limit}"
            
            # Execute query
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to dictionaries
            result_rows = []
            columns = []
            
            if rows:
                columns = list(rows[0].keys())
                for row in rows:
                    result_rows.append(dict(row))
            
            return {
                "columns": columns,
                "rows": result_rows
            }
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class DatabaseWriteTool(BaseTool):
    """Tool for writing to local SQLite databases."""
    
    @property
    def name(self) -> str:
        return "write_database"
    
    @property
    def description(self) -> str:
        return "Execute write operations on a local SQLite database"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "database_path": {
                    "type": "string",
                    "description": "Path to the SQLite database file"
                },
                "query": {
                    "type": "string",
                    "description": "SQL query to execute (INSERT, UPDATE, DELETE, etc.)"
                },
                "parameters": {
                    "type": "array",
                    "description": "Query parameters for parameterized queries",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                    "default": []
                },
                "transaction": {
                    "type": "boolean",
                    "description": "Execute in a transaction",
                    "default": True
                }
            },
            "required": ["database_path", "query"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.DATABASE_WRITE
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute database write operation."""
        database_path = kwargs.get("database_path")
        query = kwargs.get("query")
        parameters = kwargs.get("parameters", [])
        use_transaction = kwargs.get("transaction", True)
        
        try:
            # Check if path is allowed
            db_path = Path(database_path).resolve()
            if not settings.is_path_allowed(db_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Access denied: {database_path}"
                )
            
            # Execute write operation
            affected_rows = self._execute_write(
                db_path,
                query,
                parameters,
                use_transaction
            )
            
            return ToolResult(
                success=True,
                output={
                    "affected_rows": affected_rows,
                    "query": query
                },
                metadata={
                    "database": str(db_path),
                    "operation": self._get_operation_type(query)
                }
            )
            
        except Exception as e:
            logger.error(f"Database write failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
    
    def _get_operation_type(self, query: str) -> str:
        """Get the type of write operation."""
        query_upper = query.upper().strip()
        
        if query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        elif query_upper.startswith("CREATE"):
            return "CREATE"
        elif query_upper.startswith("DROP"):
            return "DROP"
        elif query_upper.startswith("ALTER"):
            return "ALTER"
        else:
            return "OTHER"
    
    def _execute_write(
        self,
        db_path: Path,
        query: str,
        parameters: List,
        use_transaction: bool
    ) -> int:
        """Execute the write operation."""
        
        conn = None
        cursor = None
        
        try:
            # Connect to database
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Start transaction if requested
            if use_transaction:
                conn.execute("BEGIN")
            
            # Execute query
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            
            affected_rows = cursor.rowcount
            
            # Commit transaction
            if use_transaction:
                conn.commit()
            
            return affected_rows
            
        except Exception as e:
            # Rollback on error
            if conn and use_transaction:
                conn.rollback()
            raise e
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
