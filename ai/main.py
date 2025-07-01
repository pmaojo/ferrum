from fastapi import FastAPI
from ai.router import router

app = FastAPI()
app.include_router(router)
