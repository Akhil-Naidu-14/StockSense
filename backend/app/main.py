from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    auth_router,
    categories_router,
    health_router,
    inventory_router,
    locations_router,
    products_router,
    warehouses_router,
)
# Import all models so SQLAlchemy metadata registers them for table creation
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create database tables for SQLite / development startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="StockSense API",
    description="Modular Inventory Management System Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware setup
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

if settings.APP_ENV == "development":
    origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(warehouses_router)
app.include_router(locations_router)
app.include_router(products_router)
app.include_router(inventory_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to StockSense API",
        "docs": "/docs",
        "health": "/api/health",
    }
