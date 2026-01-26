"""
MRS Server - Metaverse Registry System

A federated spatial registry protocol implementation.
"""

import argparse
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mrs_server import __version__
from mrs_server.api import api_router
from mrs_server.auth.keys import ensure_server_key
from mrs_server.config import settings
from mrs_server.database import close_database, init_database
from mrs_server.federation import add_peer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mrs_server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info(f"Starting MRS Server v{__version__}")
    logger.info(f"Server URL: {settings.server_url}")
    logger.info(f"Database: {settings.database_path}")

    # Initialize database
    init_database(settings.database_path)
    logger.info("Database initialized")

    # Ensure server has a signing key
    server_key = ensure_server_key()
    logger.info(f"Server key: {server_key['key_id']}")

    # Load configured bootstrap peers
    for peer_url in settings.bootstrap_peers:
        add_peer(peer_url, is_configured=True)
        logger.info(f"Added bootstrap peer: {peer_url}")

    yield

    # Shutdown
    logger.info("Shutting down MRS Server")
    close_database()


# Create the FastAPI application
app = FastAPI(
    title="MRS Server",
    description="Metaverse Registry System - A federated spatial registry protocol",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes
app.include_router(api_router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with basic server info."""
    return {
        "name": "MRS Server",
        "version": __version__,
        "server": settings.server_url,
        "docs": f"{settings.server_url}/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


def run():
    """Run the server using uvicorn."""
    parser = argparse.ArgumentParser(description="MRS Server - Metaverse Registry System")
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=None,
        help=f"Port to listen on (default: {settings.port}, or MRS_PORT env var)"
    )
    parser.add_argument(
        "-H", "--host",
        type=str,
        default=None,
        help=f"Host to bind to (default: {settings.host}, or MRS_HOST env var)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    args = parser.parse_args()

    # Command line args override config/env vars
    host = args.host if args.host is not None else settings.host
    port = args.port if args.port is not None else settings.port

    uvicorn.run(
        "mrs_server.main:app",
        host=host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    run()
