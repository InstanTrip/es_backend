import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from server.routes import create_trip
from server.routes import get_location_data

from server import WEB_HOST, WEB_PORT

app = FastAPI(root_path="/pyapi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_trip.router)
app.include_router(get_location_data.router)

if __name__ == "__main__":
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)
