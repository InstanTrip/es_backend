import datetime
from fastapi import APIRouter

from server.models.locations import LocationList
from server.utils.get_location import get_location

router = APIRouter(prefix="")

@router.post("/get-location-data/")
async def get_location_data(data: LocationList):
    """
    id로 장소 정보 가져오기
    """
    res = await get_location(data)
    return res