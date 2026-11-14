from fastapi import FastAPI

from app.routers import taxonomy

app = FastAPI(title="TRACE API")
app.include_router(taxonomy.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}