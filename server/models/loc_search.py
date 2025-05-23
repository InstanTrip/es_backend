from pydantic import BaseModel

class Search(BaseModel):
    lat: float
    lon: float
    query: str