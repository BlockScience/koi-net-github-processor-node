import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Core components
from .core import node
from .repository import RepositoryService
from .handlers import set_repository_service  # Import the setter function
from koi_net.protocol.api_models import (
    PollEvents, FetchRids, FetchManifests, FetchBundles,
    EventsPayload, RidsPayload, ManifestsPayload, BundlesPayload
)
from koi_net.protocol.consts import (
    BROADCAST_EVENTS_PATH, POLL_EVENTS_PATH, FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH, FETCH_BUNDLES_PATH
)
from koi_net.processor.knowledge_object import KnowledgeSource

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the lifecycle of the KOI-net node."""
    logger.info("Starting Processor GitHub Node...")
    try:
        # Ensure DB is initialized
        from . import index_db
        index_db.initialize_db(node.config.index_db_path)

        # Start the node
        node.start()
        logger.info(f"Node started with RID: {node.identity.rid}")

        # Instantiate repository service
        repository_service = RepositoryService(config=node.config)

        # Store it in app state and set it for handlers
        app.state.repository_service = repository_service
        set_repository_service(repository_service)

        yield
    finally:
        # Stop the node gracefully
        node.stop()
        logger.info("Processor GitHub Node stopped.")

# Dependency to get the repository service instance
def get_repository_service(request):
    """Dependency to access the RepositoryService instance."""
    # Access the instance stored in app state during lifespan
    return request.app.state.repository_service

# Define API models
class RepositoryInfo(BaseModel):
    """Repository information returned by the API."""
    repo_rid: str
    repo_url: str
    first_indexed: str
    last_updated: str
    latest_commit_sha: Optional[str] = None
    total_commits: int = 0
    total_files: int = 0

class EventInfo(BaseModel):
    """Event information returned by the API."""
    event_rid: str
    event_type: str
    timestamp: str
    commit_sha: Optional[str] = None
    summary: str
    bundle_rid: Optional[str] = None

class StatusResponse(BaseModel):
    """General status response."""
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Create the FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="GitHub Processor API"
)

# Standard router for processor-specific endpoints
router = APIRouter(prefix="/api/processor/github", tags=["GitHub Processor"])

# Router for standard KOI-net endpoints
koi_net_router = APIRouter(
    prefix="/koi-net",
    tags=["KOI-net Protocol"]
)

# Dependency to get the processor node instance
async def get_processor():
    """Dependency to access the processor node instance."""
    if node is None:
        raise HTTPException(status_code=503, detail="Node instance not initialized")
    return node

# Dependency to get database path
async def get_db_path():
    """Dependency to get the database path."""
    if node is None or not hasattr(node, "config"):
        raise HTTPException(status_code=503, detail="Node configuration not available")
    return node.config.index_db_path

# Status endpoint
@router.get("/status", response_model=StatusResponse)
async def get_status(processor=Depends(get_processor)):
    """Get the current status of the GitHub processor node."""
    config = processor.config
    return StatusResponse(
        status="active",
        message="GitHub processor node is running",
        details={
            "node_name": config.koi_net.node_name,
            "node_type": str(config.koi_net.node_profile.node_type),
            "db_path": config.index_db_path
        }
    )

# Repositories endpoints
@router.get("/repositories", response_model=List[RepositoryInfo])
async def list_repositories(
    repo_service: RepositoryService = Depends(get_repository_service) # Inject service
):
    """List all tracked repositories."""
    repos = repo_service.list_repositories()
    return repos

# Events endpoints
@router.get("/repositories/{repo_rid}/events", response_model=List[EventInfo])
async def get_repository_events(
    repo_rid: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get events for a specific repository."""
    # Inject service
    repo_service: RepositoryService = Depends(get_repository_service)
    events = repo_service.get_events(repo_rid, limit, offset)
    if not events:
        raise HTTPException(status_code=404, detail=f"No events found for repository {repo_rid}")
    return events

koi_net_router = APIRouter(
    prefix="/koi-net",
    tags=["KOI-net Protocol"]
)

@koi_net_router.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload):
    logger.info(f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)")
    for event in req.events:
        logger.info(f"{event!r}")
        node.processor.handle(event=event, source=KnowledgeSource.External)


@koi_net_router.post(POLL_EVENTS_PATH)
def poll_events(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {POLL_EVENTS_PATH}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)

@koi_net_router.post(FETCH_RIDS_PATH)
def fetch_rids(req: FetchRids) -> RidsPayload:
    return node.network.response_handler.fetch_rids(req)

@koi_net_router.post(FETCH_MANIFESTS_PATH)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    return node.network.response_handler.fetch_manifests(req)

@koi_net_router.post(FETCH_BUNDLES_PATH)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    return node.network.response_handler.fetch_bundles(req)

app.include_router(router)
app.include_router(koi_net_router)
logger.info("Registered GitHub processor and KOI-net protocol API endpoints")
