"""Advanced and interesting tools."""

import os
import json
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
import base64
from datetime import datetime, timedelta
import re
import hashlib
import tempfile

from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class SystemInfoTool(BaseTool):
    """Tool to get system information."""
    
    @property
    def name(self) -> str:
        return "get_system_info"
    
    @property
    def description(self) -> str:
        return "Get system information including OS, CPU, memory, disk usage, and running processes"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "detailed": {
                    "type": "boolean",
                    "description": "Whether to include detailed information",
                    "default": False
                },
                "include_processes": {
                    "type": "boolean", 
                    "description": "Whether to include running processes",
                    "default": False
                }
            }
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.SYSTEM_READ
    
    async def execute(self, **kwargs) -> ToolResult:
        """Get system information."""
        detailed = kwargs.get("detailed", False)
        include_processes = kwargs.get("include_processes", False)
        
        try:
            import psutil
            import platform
            
            # Basic system info
            system_info = {
                "os": platform.system(),
                "os_version": platform.version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            
            # CPU info
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "cpu_usage_percent": psutil.cpu_percent(interval=1),
                "cpu_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None
            }
            
            # Memory info
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "usage_percent": memory.percent
            }
            
            # Disk info
            disk = psutil.disk_usage('/')
            disk_info = {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "usage_percent": round((disk.used / disk.total) * 100, 2)
            }
            
            result = {
                "system": system_info,
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info
            }
            
            if detailed:
                # Network info
                network_info = {}
                for interface, addrs in psutil.net_if_addrs().items():
                    network_info[interface] = [
                        {"family": addr.family.name, "address": addr.address}
                        for addr in addrs
                    ]
                result["network"] = network_info
            
            if include_processes:
                # Top processes by memory usage
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                    try:
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Sort by memory usage and take top 10
                processes.sort(key=lambda x: x['memory_percent'], reverse=True)
                result["top_processes"] = processes[:10]
            
            return ToolResult(
                success=True,
                output=result,
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Failed to get system info: {str(e)}"
            )


class CodeAnalyzerTool(BaseTool):
    """Tool to analyze code files."""
    
    @property
    def name(self) -> str:
        return "analyze_code"
    
    @property
    def description(self) -> str:
        return "Analyze code files for complexity, structure, and potential issues"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the code file to analyze"
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis to perform",
                    "enum": ["basic", "complexity", "security", "all"],
                    "default": "basic"
                }
            },
            "required": ["file_path"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def execute(self, **kwargs) -> ToolResult:
        """Analyze code file."""
        file_path = kwargs.get("file_path")
        analysis_type = kwargs.get("analysis_type", "basic")
        
        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"File not found: {file_path}"
                )
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Basic analysis
            basic_stats = {
                "file_name": path.name,
                "file_extension": path.suffix,
                "total_lines": len(lines),
                "non_empty_lines": len([line for line in lines if line.strip()]),
                "comment_lines": len([line for line in lines if line.strip().startswith(('#', '//', '/*', '*'))]),
                "file_size_bytes": len(content.encode('utf-8'))
            }
            
            result = {"basic_stats": basic_stats}
            
            if analysis_type in ["complexity", "all"]:
                # Complexity analysis
                complexity_stats = {
                    "function_count": len(re.findall(r'def\s+\w+|function\s+\w+|class\s+\w+', content)),
                    "class_count": len(re.findall(r'class\s+\w+', content)),
                    "import_count": len(re.findall(r'import\s+|from\s+.*import', content)),
                    "max_line_length": max(len(line) for line in lines) if lines else 0,
                    "avg_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0
                }
                result["complexity"] = complexity_stats
            
            if analysis_type in ["security", "all"]:
                # Basic security analysis
                security_issues = []
                
                # Check for common security issues
                if 'eval(' in content:
                    security_issues.append("Found eval() usage - potential security risk")
                if 'exec(' in content:
                    security_issues.append("Found exec() usage - potential security risk")
                if re.search(r'password\s*=\s*["\'][^"\']*["\']', content, re.IGNORECASE):
                    security_issues.append("Found hardcoded password")
                if re.search(r'api[_-]?key\s*=\s*["\'][^"\']*["\']', content, re.IGNORECASE):
                    security_issues.append("Found hardcoded API key")
                
                result["security"] = {
                    "issues_found": len(security_issues),
                    "issues": security_issues
                }
            
            return ToolResult(
                success=True,
                output=result,
                metadata={
                    "analysis_type": analysis_type,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Code analysis failed: {str(e)}"
            )


class ImageAnalyzerTool(BaseTool):
    """Tool to analyze images."""
    
    @property
    def name(self) -> str:
        return "analyze_image"
    
    @property
    def description(self) -> str:
        return "Analyze image files for metadata, properties, and basic content analysis"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file"
                },
                "include_metadata": {
                    "type": "boolean",
                    "description": "Whether to include EXIF metadata",
                    "default": True
                }
            },
            "required": ["image_path"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def execute(self, **kwargs) -> ToolResult:
        """Analyze image file."""
        image_path = kwargs.get("image_path")
        include_metadata = kwargs.get("include_metadata", True)
        
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            path = Path(image_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Image file not found: {image_path}"
                )
            
            with Image.open(path) as img:
                # Basic image properties
                basic_info = {
                    "filename": path.name,
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                    "file_size_bytes": path.stat().st_size
                }
                
                result = {"basic_info": basic_info}
                
                if include_metadata and hasattr(img, '_getexif'):
                    # Extract EXIF metadata
                    exifdata = img.getexif()
                    metadata = {}
                    
                    for tag_id in exifdata:
                        tag = TAGS.get(tag_id, tag_id)
                        data = exifdata.get(tag_id)
                        if isinstance(data, bytes):
                            data = data.decode()
                        metadata[tag] = data
                    
                    result["metadata"] = metadata
                
                # Color analysis
                if img.mode == 'RGB':
                    # Get dominant colors (simplified)
                    img_small = img.resize((50, 50))
                    colors = img_small.getcolors(maxcolors=256*256*256)
                    if colors:
                        dominant_color = max(colors, key=lambda item: item[0])
                        result["color_analysis"] = {
                            "dominant_color_rgb": dominant_color[1],
                            "color_count": len(colors)
                        }
            
            return ToolResult(
                success=True,
                output=result,
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Image analysis failed: {str(e)}"
            )


class NetworkToolkit(BaseTool):
    """Network utilities toolkit."""
    
    @property
    def name(self) -> str:
        return "network_tools"
    
    @property
    def description(self) -> str:
        return "Network utilities: ping, port scan, DNS lookup, IP geolocation"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Network action to perform",
                    "enum": ["ping", "port_scan", "dns_lookup", "ip_geolocation"]
                },
                "target": {
                    "type": "string",
                    "description": "Target hostname or IP address"
                },
                "port": {
                    "type": "integer",
                    "description": "Port number (for port_scan)",
                    "minimum": 1,
                    "maximum": 65535
                },
                "port_range": {
                    "type": "string",
                    "description": "Port range (e.g., '80-443' for port_scan)"
                }
            },
            "required": ["action", "target"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute network tool."""
        action = kwargs.get("action")
        target = kwargs.get("target")
        port = kwargs.get("port")
        port_range = kwargs.get("port_range")
        
        try:
            if action == "ping":
                return await self._ping(target)
            elif action == "port_scan":
                return await self._port_scan(target, port, port_range)
            elif action == "dns_lookup":
                return await self._dns_lookup(target)
            elif action == "ip_geolocation":
                return await self._ip_geolocation(target)
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Network operation failed: {str(e)}"
            )
    
    async def _ping(self, target: str) -> ToolResult:
        """Ping a target."""
        try:
            import platform
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            result = subprocess.run(
                ['ping', param, '4', target],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return ToolResult(
                success=result.returncode == 0,
                output={
                    "target": target,
                    "reachable": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Ping failed: {str(e)}"
            )
    
    async def _port_scan(self, target: str, port: Optional[int], port_range: Optional[str]) -> ToolResult:
        """Scan ports on target."""
        import socket
        
        ports_to_scan = []
        
        if port:
            ports_to_scan = [port]
        elif port_range:
            start, end = map(int, port_range.split('-'))
            ports_to_scan = list(range(start, end + 1))
        else:
            # Common ports
            ports_to_scan = [21, 22, 23, 25, 53, 80, 110, 443, 993, 995]
        
        open_ports = []
        closed_ports = []
        
        for p in ports_to_scan:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            
            try:
                result = sock.connect_ex((target, p))
                if result == 0:
                    open_ports.append(p)
                else:
                    closed_ports.append(p)
            except:
                closed_ports.append(p)
            finally:
                sock.close()
        
        return ToolResult(
            success=True,
            output={
                "target": target,
                "open_ports": open_ports,
                "closed_ports": closed_ports,
                "total_scanned": len(ports_to_scan)
            }
        )
    
    async def _dns_lookup(self, target: str) -> ToolResult:
        """Perform DNS lookup."""
        import socket
        
        try:
            # Forward lookup
            ip_address = socket.gethostbyname(target)
            
            # Reverse lookup
            try:
                hostname = socket.gethostbyaddr(ip_address)[0]
            except:
                hostname = None
            
            return ToolResult(
                success=True,
                output={
                    "hostname": target,
                    "ip_address": ip_address,
                    "reverse_hostname": hostname
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"DNS lookup failed: {str(e)}"
            )
    
    async def _ip_geolocation(self, target: str) -> ToolResult:
        """Get IP geolocation information."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://ip-api.com/json/{target}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return ToolResult(
                            success=data.get("status") == "success",
                            output=data
                        )
                    else:
                        return ToolResult(
                            success=False,
                            output=None,
                            error=f"Geolocation API returned status {response.status}"
                        )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Geolocation lookup failed: {str(e)}"
            )


class HashCalculatorTool(BaseTool):
    """Tool to calculate file hashes."""
    
    @property
    def name(self) -> str:
        return "calculate_hash"
    
    @property
    def description(self) -> str:
        return "Calculate MD5, SHA1, SHA256, or SHA512 hash of files or text"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input_type": {
                    "type": "string",
                    "description": "Type of input",
                    "enum": ["file", "text"]
                },
                "input_value": {
                    "type": "string",
                    "description": "File path or text to hash"
                },
                "hash_type": {
                    "type": "string",
                    "description": "Hash algorithm to use",
                    "enum": ["md5", "sha1", "sha256", "sha512", "all"],
                    "default": "sha256"
                }
            },
            "required": ["input_type", "input_value"]
        }
    
    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ_FILES
    
    async def execute(self, **kwargs) -> ToolResult:
        """Calculate hash."""
        input_type = kwargs.get("input_type")
        input_value = kwargs.get("input_value")
        hash_type = kwargs.get("hash_type", "sha256")
        
        try:
            if input_type == "file":
                path = Path(input_value)
                if not path.exists():
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"File not found: {input_value}"
                    )
                
                with open(path, 'rb') as f:
                    data = f.read()
            else:  # text
                data = input_value.encode('utf-8')
            
            hashes = {}
            
            if hash_type == "all":
                hash_types = ["md5", "sha1", "sha256", "sha512"]
            else:
                hash_types = [hash_type]
            
            for ht in hash_types:
                if ht == "md5":
                    hashes["md5"] = hashlib.md5(data).hexdigest()
                elif ht == "sha1":
                    hashes["sha1"] = hashlib.sha1(data).hexdigest()
                elif ht == "sha256":
                    hashes["sha256"] = hashlib.sha256(data).hexdigest()
                elif ht == "sha512":
                    hashes["sha512"] = hashlib.sha512(data).hexdigest()
            
            return ToolResult(
                success=True,
                output={
                    "input_type": input_type,
                    "input_value": input_value if input_type == "text" else path.name,
                    "hashes": hashes,
                    "data_size_bytes": len(data)
                },
                metadata={"timestamp": datetime.now().isoformat()}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Hash calculation failed: {str(e)}"
            )
