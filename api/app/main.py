from fastapi import FastAPI

from app.routers import admin, auth, closure, kpis, ncs, ncs_lifecycle, taxonomy

app = FastAPI(title="TRACE API")
app.include_router(taxonomy.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(ncs.router)
app.include_router(ncs_lifecycle.router)
app.include_router(closure.router)
app.include_router(kpis.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}