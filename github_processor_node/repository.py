import logging
import os
from typing import Optional, Dict, Any

from . import index_db
from .utils import (
    repo_rid_to_owner_repo,
    owner_repo_to_repo_rid,
    summarize_event,
)

logger = logging.getLogger(__name__)


class RepositoryService:
    def __init__(self, config):
        self.config = config

    def list_repositories(self):
        """List all tracked repositories."""
        return index_db.get_repositories(self.config.index_db_path)

    def get_events(
        self, repo_rid: str, limit: int = 50, offset: int = 0
    ):
        """Get events for a specific repository."""
        return index_db.get_events_for_repo(
            self.config.index_db_path, repo_rid, limit, offset
        )

    def prune_old_data(self, days_to_keep: int = 90):
        """Remove old events and related data beyond a certain age."""
        return index_db.prune_old_data(
            self.config.index_db_path, days_to_keep
        )

    async def process_github_event_bundle(
        self, kobj_rid: str, payload: Dict[str, Any]
    ):
        """Processes a GitHubEvent bundle and stores metadata only, without Git operations."""
        logger.info(f"Processing GitHubEvent bundle: {kobj_rid}")

        try:
            # Handle different event formats (webhook vs backfill)
            if "repository" in payload:
                # Standard webhook format with top-level repository field
                owner = payload["repository"]["owner"]["login"]
                repo = payload["repository"]["name"]
                repo_url = payload["repository"]["clone_url"]
                event_source = payload.get("event_type", "push")
            elif "event_source_type" in payload and "payload" in payload:
                # Backfill format with nested payload
                logger.info(f"Processing backfill event: {payload['event_source_type']} for {kobj_rid}")
                
                if payload["event_source_type"] == "backfill_repo_details":
                    # Repository details backfill
                    owner = payload["payload"]["owner"]["login"]
                    repo = payload["payload"]["name"]
                    repo_url = payload["payload"]["clone_url"]
                    event_source = "repository"
                elif payload["event_source_type"] == "backfill_commit":
                    # Commit backfill - extract repo info from URL parts
                    # URL format is typically: https://api.github.com/repos/owner/repo/...
                    commit_url = payload["payload"]["url"]
                    url_parts = commit_url.split('/')
                    if "repos" in url_parts:
                        repos_index = url_parts.index("repos")
                        if len(url_parts) > repos_index + 2:
                            owner = url_parts[repos_index + 1]
                            repo = url_parts[repos_index + 2]
                            repo_url = f"https://github.com/{owner}/{repo}.git"
                            event_source = "commit"
                        else:
                            raise ValueError(f"Cannot parse owner/repo from URL: {commit_url}")
                    else:
                        raise ValueError(f"Cannot parse repository from commit URL: {commit_url}")
                else:
                    logger.warning(f"Unknown backfill event type: {payload['event_source_type']}")
                    return {
                        "status": "skipped",
                        "message": f"Unknown backfill event type: {payload['event_source_type']}",
                        "details": {"kobj_rid": kobj_rid}
                    }
            else:
                logger.info(f"Skipping malformed event bundle: {kobj_rid}")
                return {
                    "status": "skipped",
                    "message": "Event doesn't match any known format",
                    "details": {"kobj_rid": kobj_rid}
                }

            repo_rid_str = owner_repo_to_repo_rid(owner, repo)
            logger.info(f"Processing event for repository {owner}/{repo}")

            # Store basic repository information 
            index_db.add_repository(
                self.config.index_db_path, repo_rid_str, repo_url
            )

            # Extract commit info based on event type if present
            commit_sha = None
            commit_timestamp = ""
            commit_message = ""
            
            if "event_source_type" in payload and payload["event_source_type"] == "backfill_commit":
                # For backfill commits, the SHA is directly in the payload
                commit_sha = payload["payload"]["sha"]
                commit_info = payload["payload"]["commit"]
                commit_timestamp = commit_info["author"]["date"]
                commit_message = commit_info["message"]
            elif "head_commit" in payload:
                # Standard webhook format
                commit_payload = payload.get("head_commit", {})
                commit_sha = commit_payload.get("id")
                commit_timestamp = commit_payload.get("timestamp", "")
                commit_message = commit_payload.get("message", "")
                
            # Determine event type
            if "event_source_type" in payload:
                event_type_str = event_source  # Use what we determined earlier for backfill
            else:
                event_type_str = payload.get("event_type", "push")  # Default for webhooks
                
            # Store event metadata
            if commit_sha:
                # Store event with commit reference
                index_db.add_event_metadata(
                    self.config.index_db_path,
                    kobj_rid,
                    repo_rid_str,
                    event_type_str,
                    commit_timestamp,
                    commit_sha,
                    summarize_event(
                        event_type_str, repo_rid_str, commit_sha, payload
                    ),
                    kobj_rid,
                )
            else:
                # Store event without commit reference
                index_db.add_event_metadata(
                    self.config.index_db_path,
                    kobj_rid,
                    repo_rid_str,
                    event_type_str,
                    "",  # No timestamp
                    None,  # No commit SHA
                    summarize_event(
                        event_type_str, repo_rid_str, None, payload
                    ),
                    kobj_rid,
                )

            logger.info(f"Successfully stored metadata for event {kobj_rid} (repo: {owner}/{repo})")
            return {
                "status": "success",
                "message": "Event metadata stored",
                "details": {
                    "kobj_rid": kobj_rid,
                    "repo_rid": repo_rid_str,
                    "commit_sha": commit_sha,
                },
            }

        except Exception as e:
            logger.error(
                f"Error processing GitHubEvent bundle {kobj_rid}: {e}"
            )
            return {"status": "error", "message": str(e), "details": {"kobj_rid": kobj_rid}}
