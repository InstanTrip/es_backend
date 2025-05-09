from pydantic import BaseModel

class Taste(BaseModel):
    accommodation_taste: list[str]
    destination_taste: list[str]
    restaurant_taste: list[str]

class CreateTripData(BaseModel):
    start_date: str
    end_date: str
    location: list[str]
    taste: Taste