from typing import List
from fastapi import APIRouter
from app.schemas import User

router = APIRouter(prefix="/users", tags=["Business API"])

SAMPLE_USERS: List[User] = [
    User(id=1, username="alex_observability", email="alex@example.com", role="DevOps Lead", is_active=True),
    User(id=2, username="sara_sre", email="sara@example.com", role="Site Reliability Engineer", is_active=True),
    User(id=3, username="marcus_backend", email="marcus@example.com", role="Backend Architect", is_active=True),
    User(id=4, username="elena_cloud", email="elena@example.com", role="Cloud Platform Engineer", is_active=True),
    User(id=5, username="jordan_secops", email="jordan@example.com", role="Security Analyst", is_active=False),
]


@router.get(
    "",
    response_model=List[User],
    summary="List fictional sample users",
)
async def get_users() -> List[User]:
    """Retrieves a list of sample registered users."""
    return SAMPLE_USERS
