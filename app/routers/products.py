from typing import List
from fastapi import APIRouter
from app.schemas import Product

router = APIRouter(prefix="/products", tags=["Business API"])

SAMPLE_PRODUCTS: List[Product] = [
    Product(id=101, name="Enterprise Prometheus Cluster", category="Infrastructure", price=499.00, in_stock=True),
    Product(id=102, name="Grafana Observability Portal", category="Visualization", price=299.00, in_stock=True),
    Product(id=103, name="Alertmanager Multi-Channel Gateway", category="Alerting", price=199.00, in_stock=True),
    Product(id=104, name="High-Throughput ASGI Middleware", category="Networking", price=149.50, in_stock=True),
    Product(id=105, name="Distributed Tracing Collector", category="Tracing", price=349.00, in_stock=False),
]


@router.get(
    "",
    response_model=List[Product],
    summary="List fictional sample products",
)
async def get_products() -> List[Product]:
    """Retrieves a list of sample catalog products."""
    return SAMPLE_PRODUCTS
