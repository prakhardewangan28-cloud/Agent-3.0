"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes
from app.models.schemas import HealthResponse
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info("Knowledge Intelligence Agent - Starting Up")
    logger.info("=" * 60)
    logger.info(f"MOCK_MODE: {settings.mock_mode}")
    
    # Check Supabase
    try:
        from app.db.supabase_client import supabase
        response = supabase.table("research_sessions").select("id").limit(1).execute()
        logger.info("✓ Supabase connection: OK")
    except Exception as e:
        logger.warning(f"✗ Supabase connection: FAILED - {e}")
    
    # Check SerpAPI key
    if settings.serpapi_key:
        logger.info(f"✓ SerpAPI key: Set ({settings.serpapi_key[:10]}...)")
    else:
        logger.warning("✗ SerpAPI key: NOT SET")
    
    # Check Gemini key
    if settings.gemini_api_key:
        masked = settings.gemini_api_key[:6] + "..." + settings.gemini_api_key[-4:]
        logger.info(f"✓ Gemini API key: Set ({masked})")
    else:
        logger.warning("✗ Gemini API key: NOT SET")
    
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    # Close any open SSE streams
    from app.api.routes import _session_streams
    if _session_streams:
        logger.info(f"Closing {len(_session_streams)} active SSE streams")
        _session_streams.clear()
    logger.info("Shutdown complete")


# ============================================================================
# APPLICATION
# ============================================================================

# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Intelligence Agent",
    description="Track 5 Hackathon - AI-powered research and fact-checking API",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# GLOBAL EXCEPTION HANDLER
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    from uuid import uuid4
    import traceback
    
    error_id = str(uuid4())[:8]
    logger.error(
        f"Unhandled exception {error_id} on {request.method} {request.url}:\n"
        f"{traceback.format_exc()}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_id": error_id
        }
    )


# ============================================================================
# ROUTES
# ============================================================================

# Legacy health check endpoint (external)
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    External health check endpoint.
    
    Returns:
        Health status
    """
    return HealthResponse(status="ok")


# Include API v1 routes
app.include_router(routes.router, prefix="/api/v1", tags=["Research API"])

logger.info("Application initialized successfully")
