import logging
import asyncio
from typing import Dict, Any
from rid_types import GitHubEvent
from koi_net.processor.handler import HandlerType, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject, KnowledgeSource
from koi_net.processor.interface import ProcessorInterface
from koi_net.protocol.event import EventType
from koi_net.protocol.node import NodeProfile
from koi_net.protocol.edge import EdgeType
from koi_net.protocol.helpers import generate_edge_bundle
from rid_lib.types import KoiNetNode, KoiNetEdge

from .core import node
from .repository import RepositoryService

# Global service reference - will be populated in server.py lifespan
repository_service = None


logger = logging.getLogger(__name__)

# Function to set repository service from server.py
def set_repository_service(service: RepositoryService):
    """Set the repository service for handlers to use."""
    global repository_service
    repository_service = service
    logger.info("Repository service initialized for handlers")


@node.processor.register_handler(HandlerType.Manifest, rid_types=[GitHubEvent])
def handle_event_manifest(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    On incoming GitHubEvent manifest, trigger bundle fetch from a state provider.
    """
    logger.info(f"Handling manifest for event {kobj.rid}")

    # If we already have the contents, skip fetch
    if kobj.contents is not None:
        logger.debug("Bundle already present, skipping fetch attempt.")
        return kobj

    # Let the pipeline handle bundle fetching
    logger.debug(f"Manifest for {kobj.rid} received, relying on pipeline to fetch bundle.")
    return kobj

@node.processor.register_handler(HandlerType.Bundle, rid_types=[GitHubEvent])
def handle_event_bundle(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    Process GitHubEvent bundles, storing event metadata only without Git operations.
    """
    logger.info(f"Processing bundle for event {kobj.rid}")

    # Check for existing event and compare hashes
    prev = proc.cache.read(kobj.rid)
    is_update = prev is not None
    if prev and prev.manifest and kobj.manifest:
        hash_changed = prev.manifest.sha256_hash != kobj.manifest.sha256_hash
    else:
        hash_changed = True

    if is_update and not hash_changed:
        logger.info(f"Event {kobj.rid} unchanged (same hash), skipping processing")
        return STOP_CHAIN

    # Set the normalized event type
    kobj.normalized_event_type = EventType.UPDATE if is_update else EventType.NEW
    event_type_str = "updated" if is_update else "new"
    logger.info(f"Processing {event_type_str} event {kobj.rid}")

    # Access global repository service - this will be set in server.py lifespan
    global repository_service
    if repository_service is None:
        logger.error("Repository service not initialized. Cannot process bundle.")
        # Still return kobj to allow caching
        return kobj

    try:
        # Extract data from the bundle contents
        bundle = kobj.bundle
        if not bundle:
            logger.error(f"No bundle available for {kobj.rid}")
            return kobj

        payload = bundle.contents
        if not payload:
            logger.error(f"Empty bundle contents for {kobj.rid}")
            return kobj

        # Create a new event loop just for this operation
        loop = asyncio.new_event_loop()
        try:
            # Run the async function synchronously - store metadata only
            result = loop.run_until_complete(_process_event_async(repository_service, kobj.rid, payload))
            # Process result
            if result.get("status") == "success":
                logger.info(f"Successfully stored metadata for event {kobj.rid}")
            else:
                logger.warning(f"Event processing status: {result.get('status')}. Message: {result.get('message')}")
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"Error processing GitHubEvent bundle: {e}")

    return kobj

# Helper functions for async processing
async def _process_event_async(repo_service, kobj_rid, payload):
    """Process event asynchronously, storing metadata only."""
    try:
        return await repo_service.process_github_event_bundle(
            kobj_rid=str(kobj_rid),
            payload=payload
        )
    except Exception as e:
        logger.error(f"Async processing error for {kobj_rid}: {e}")
        return {"status": "error", "message": str(e)}


@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def handle_network_discovery(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    Discover sensors that provide GitHubEvent, propose edge, and fetch historical bundles.
    """
    if kobj.normalized_event_type != EventType.NEW:
        return

    # Skip internal events
    if kobj.source != KnowledgeSource.External:
        return

    try:
        # Extract the node profile
        bundle = kobj.bundle
        if bundle is None:
            return

        profile: NodeProfile = bundle.validate_contents(NodeProfile)

        # Check if this node provides GitHubEvent
        if GitHubEvent not in profile.provides.event:
            return  # not a GitHub Sensor

        logger.info(f"GitHub Sensor discovered - requesting subscription to {kobj.rid}")
        if isinstance(kobj.rid, KoiNetNode):
            edge_bundle = generate_edge_bundle(
                source=proc.identity.rid,
                target=kobj.rid,
                edge_type=EdgeType.WEBHOOK,
                rid_types=[GitHubEvent],
            )
            proc.handle(bundle=edge_bundle)

        # Cold-start catch-up (fetch all historical events from sensor)
        try:
            logger.info(f"Fetching historical events from sensor {kobj.rid}")
            rid_payload = proc.network.request_handler.fetch_rids(kobj.rid, rid_types=[GitHubEvent])
            if rid_payload and rid_payload.rids:
                logger.info(f"Found {len(rid_payload.rids)} historical events")
                bundle_payload = proc.network.request_handler.fetch_bundles(kobj.rid, rids=rid_payload.rids)
                for bundle in bundle_payload.bundles:
                    proc.handle(bundle=bundle, source=KnowledgeSource.External)
        except Exception as e:
            logger.error(f"Error fetching historical events: {e}")
    except Exception as e:
        logger.error(f"Error processing node {kobj.rid}: {e}")

    return kobj

@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetEdge])
def handle_edge_negotiation(proc: ProcessorInterface, kobj: KnowledgeObject):
    """
    Handle edge negotiation responses from sensors.
    This ensures connections are properly established and tracked.
    """
    logger.debug(f"Processing edge: {kobj.rid}")

    # Only process edges that are responses to our subscription requests
    if kobj.source != KnowledgeSource.External:
        return

    try:
        # Extract edge details from bundle
        bundle = kobj.bundle
        if not bundle:
            return

        edge = bundle.contents

        # Check if this is an edge approval targeting us
        if (edge.get("target") == str(proc.identity.rid) and
            edge.get("status") == "approved"):

            sensor_rid = edge.get("source")
            logger.info(f"Edge approved by sensor {sensor_rid} for GitHub events")

    except Exception as e:
        logger.error(f"Error processing edge: {e}")

    return kobj
