from pydantic import BaseModel

class Location(BaseModel):
    type: str
    id: str

class LocationList(BaseModel):
    ids: list[Location]