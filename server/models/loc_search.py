from pydantic import BaseModel

class Search(BaseModel):
    lat: float
    lon: float
    location: str
    query: str