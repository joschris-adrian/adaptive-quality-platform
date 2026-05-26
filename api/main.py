from fastapi import FastAPI
from api.routes import ingest

app = FastAPI(title="Adaptive Quality Platform")
app.include_router(ingest.router, prefix="/api/v1")