"""
Routers package for glbaguni backend.
Contains FastAPI route definitions.
"""

from backend.routers.health import router as health_router
from backend.routers.summarize import router as summarize_router

__all__ = [
    "health_router",
    "summarize_router",
]
