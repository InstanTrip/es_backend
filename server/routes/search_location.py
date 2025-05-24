import datetime
from fastapi import APIRouter

from server.models.loc_search import Search
from server.utils.integrated_search import integrated_search

router = APIRouter(prefix="")

@router.post("/search-location/")
async def search_location(data: Search):
    """
    통합검색
    """
    res = await integrated_search(data.query, data.location, data.lat, data.lon)
    return res