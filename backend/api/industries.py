from fastapi import APIRouter
from data_fetcher import get_industries

router = APIRouter()


@router.get("/industries")
def list_industries():
    """Return distinct industries from the database (not hardcoded)."""
    return {"industries": get_industries()}
