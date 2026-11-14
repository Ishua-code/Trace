from fastapi import FastAPI

from app.routers import admin, auth, taxonomy

app = FastAPI(title="TRACE API")
app.include_router(taxonomy.router)
app.include_router(admin.router)
app.include_router(auth.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}