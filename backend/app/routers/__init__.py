from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.routers.deliveries import router as deliveries_router
from app.routers.health import router as health_router
from app.routers.inventory import router as inventory_router
from app.routers.locations import router as locations_router
from app.routers.products import router as products_router
from app.routers.receipts import router as receipts_router
from app.routers.transfers import router as transfers_router
from app.routers.warehouses import router as warehouses_router

__all__ = [
    "health_router",
    "auth_router",
    "categories_router",
    "warehouses_router",
    "locations_router",
    "products_router",
    "inventory_router",
    "receipts_router",
    "deliveries_router",
    "transfers_router",
]
