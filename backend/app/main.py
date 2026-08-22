"""
TraceForge 83 - Main Application Entrypoint.
Serves REST API and static Single-Page Application (SPA).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api.routes import router as api_router

app = FastAPI(
    title="TraceForge 83 - Supply Chain Authenticity Engine",
    description="Real-time multi-source supply chain counterfeit & record forgery detection system.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)

@app.get("/health")
async def health_check():
    return {"status": "HEALTHY", "service": "TraceForge 83 Engine", "version": "1.0.0"}

# Mount frontend static directory if exists
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend"))
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))

if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
