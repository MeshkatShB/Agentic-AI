"""API routers."""

from .auth import router as auth_router
from .chat import router as chat_router
from .tools import router as tools_router
from .custom_tools import router as custom_tools_router
from .settings import router as settings_router
from .documents import router as documents_router
from .browser_automation import router as browser_use_router

__all__ = [
    "auth_router",
    "chat_router", 
    "tools_router",
    "custom_tools_router",
    "settings_router",
    "documents_router",
    "browser_use_router"
]
