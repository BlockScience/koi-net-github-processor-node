import logging
import os
from koi_net import NodeInterface
# Import necessary RID types for the GitHubProcessor


from .config import ProcessorNodeConfig

logger = logging.getLogger(__name__)

# Instantiate the NodeInterface directly at import time
node = NodeInterface(
    config=ProcessorNodeConfig.load_from_yaml("config.yaml"),
    use_kobj_processor_thread=True
)

logger.info(f"Node initialized with RID: {node.identity.rid}")
logger.info(f"Node type: {node.config.koi_net.node_profile.node_type}")
logger.info(f"Node server config: {node.config.server.host}:{node.config.server.port}")

# Import handlers to register them
# NOTE: This is imported after node is created so decorators can register
# with the node.processor instance
import processor_github_node.handlers  # noqa
