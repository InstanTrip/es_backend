import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from server.routes import create_trip

from server import WEB_HOST, WEB_PORT

origins = ["*",]
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_trip.router)

if __name__ == "__main__":
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)