from fastapi import APIRouter

from .crud import db
from .views import lnpos_generic_router
from .views_api import lnpos_api_router
from .views_lnurl import lnpos_lnurl_router
from .views_lnurl_legacy import lnpos_lnurl_legacy_router

lnpos_ext: APIRouter = APIRouter(prefix="/lnpos", tags=["lnpos"])
lnpos_ext.include_router(lnpos_generic_router)
lnpos_ext.include_router(lnpos_api_router)
lnpos_ext.include_router(lnpos_lnurl_router)
lnpos_ext.include_router(lnpos_lnurl_legacy_router)

lnpos_static_files = [
    {
        "path": "/lnpos/static",
        "name": "lnpos_static",
    }
]

__all__ = [
    "db",
    "lnpos_ext",
    "lnpos_static_files",
]
