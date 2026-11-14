from fastapi import FastAPI

from app.routers import admin, taxonomy

app = FastAPI(title="TRACE API")
app.include_router(taxonomy.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}