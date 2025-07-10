from fastapi import FastAPI

try:
    from router import router
except ImportError:  # when executed as a script
    from router import router

app = FastAPI()
app.include_router(router)
