from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import auth, crm, leads, reports, research, scoring, settings, sources
from app.core.config import get_settings

settings_obj = get_settings()

app = FastAPI(title="Hermes Lead-Generation Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_obj.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(scoring.router)
app.include_router(sources.router)
app.include_router(research.router)
app.include_router(crm.router)
app.include_router(reports.router)
app.include_router(settings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
