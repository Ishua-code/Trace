from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, auth, closure, jobs, audit_log, kpis, ncs, ncs_lifecycle, reindex, taxonomy

app = FastAPI(title="TRACE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(taxonomy.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(ncs.router)
app.include_router(ncs_lifecycle.router)
app.include_router(closure.router)
app.include_router(kpis.router)
app.include_router(reindex.router)
app.include_router(jobs.router)
app.include_router(audit_log.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}