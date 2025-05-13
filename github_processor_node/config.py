from koi_net.config import NodeConfig, KoiNetConfig, EnvConfig
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from pydantic import Field


class GitCredentialsEnvConfig(EnvConfig):
    """Environment variables configuration for Git credentials."""
    github_token: str | None = "GITHUB_TOKEN"

class ProcessorNodeConfig(NodeConfig):
    """Configuration for the GitHub Processor Node."""
    # Inherits server and koi_net from NodeConfig
    koi_net: KoiNetConfig = Field(
        default_factory=lambda:
        KoiNetConfig(
            node_name="processor_github",
            node_profile=NodeProfile(
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[],
                    state=[]
                ),
            ),
        )
    )

    index_db_path: str = Field(description="Path to the SQLite index database file")
    env: GitCredentialsEnvConfig = Field(default_factory=GitCredentialsEnvConfig)
