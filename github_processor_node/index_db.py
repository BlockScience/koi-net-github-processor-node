import os
import sqlite3
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Define table schemas
SCHEMA_INIT = [
    # Repository tracking table
    """
    CREATE TABLE IF NOT EXISTS repositories (
        repo_rid TEXT PRIMARY KEY,
        repo_url TEXT NOT NULL,
        first_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,

    # GitHub event metadata table
    """
    CREATE TABLE IF NOT EXISTS events (
        event_rid TEXT PRIMARY KEY,
        repo_rid TEXT NOT NULL,
        event_type TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        commit_sha TEXT,
        summary TEXT,
        bundle_rid TEXT,
        FOREIGN KEY (repo_rid) REFERENCES repositories(repo_rid)
    )
    """
]

# Create indexes for efficient querying
SCHEMA_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_events_repo ON events (repo_rid)",
    "CREATE INDEX IF NOT EXISTS idx_events_commit ON events (commit_sha)"
]

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Get a SQLite database connection with row factory set to sqlite3.Row.

    Args:
        db_path: Path to the SQLite database

    Returns:
        A connection to the database with row_factory set
    """
    if not os.path.exists(db_path):
        initialize_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(db_path: str) -> None:
    logger.info(f"Initializing database: {db_path}")
    """Initialize the SQLite database with the required schema if it doesn't exist."""
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Connect to the database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    for table_schema in SCHEMA_INIT:
        cursor.execute(table_schema)

    # Create indexes
    for index_schema in SCHEMA_INDEXES:
        cursor.execute(index_schema)

    # Commit and close
    conn.commit()
    conn.close()

    logger.info(f"Initialized database at {db_path}")

def get_latest_indexed_commit(db_path: str, repo_rid: str) -> Optional[str]:
    """Get the latest indexed commit SHA for a repository. Always returns None in simplified version."""
    return None

def add_repository(db_path: str, repo_rid: str, repo_url: str) -> None:
    """Add or update a repository in the database."""
    if not os.path.exists(db_path):
        initialize_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if repository exists
    cursor.execute("SELECT 1 FROM repositories WHERE repo_rid = ?", (repo_rid,))
    if cursor.fetchone():
        # Update last_updated timestamp
        cursor.execute(
            "UPDATE repositories SET last_updated = CURRENT_TIMESTAMP, repo_url = ? WHERE repo_rid = ?",
            (repo_url, repo_rid)
        )
    else:
        # Insert new repository
        cursor.execute(
            "INSERT INTO repositories (repo_rid, repo_url) VALUES (?, ?)",
            (repo_rid, repo_url)
        )

    conn.commit()
    conn.close()

    logger.info(f"Added/updated repository: {repo_rid}")

def add_event_metadata(
    db_path: str,
    event_rid: str,
    repo_rid: str,
    event_type: str,
    timestamp: str,
    commit_sha: Optional[str],
    summary: str,
    bundle_rid: Optional[str]
) -> None:
    """Add GitHub event metadata to the database."""
    if not os.path.exists(db_path):
        initialize_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add to events table
    cursor.execute(
        """
        INSERT OR REPLACE INTO events
        (event_rid, repo_rid, event_type, timestamp, commit_sha, summary, bundle_rid)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (event_rid, repo_rid, event_type, timestamp, commit_sha, summary, bundle_rid)
    )

    # Make sure the repository exists
    cursor.execute("SELECT 1 FROM repositories WHERE repo_rid = ?", (repo_rid,))
    if not cursor.fetchone():
        # Add basic repository entry if it doesn't exist
        cursor.execute(
            "INSERT INTO repositories (repo_rid, repo_url) VALUES (?, ?)",
            (repo_rid, f"orn:{repo_rid}")  # Using RID as placeholder URL
        )

    conn.commit()
    conn.close()

    logger.info(f"Added event metadata: {event_rid} (type: {event_type}) for repo: {repo_rid}")

def add_commit(
    db_path: str,
    repo_rid: str,
    commit_sha: str,
    author_name: str,
    author_email: str,
    commit_timestamp: str,
    commit_message: str,
    parent_commits: List[str],
    files_changed: int
) -> None:
    """Add a commit to the database - no-op in simplified version."""
    # This function is kept for API compatibility but doesn't do anything
    logger.debug(f"Ignoring commit: {commit_sha} for repo: {repo_rid}")
    pass

def add_file(
    db_path: str,
    repo_rid: str,
    path: str,
    blob_sha: str,
    commit_sha: str,
    timestamp: str,
    file_size: int
) -> None:
    """Add a file reference to the database - no-op in simplified version."""
    # This function is kept for API compatibility but doesn't do anything
    logger.debug(f"Ignoring file: {path} for commit: {commit_sha}")
    pass

def update_repository_latest_commit(db_path: str, repo_rid: str, latest_commit_sha: str, timestamp: str) -> None:
    """Update the repository last updated timestamp."""
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}. Skipping update for {repo_rid}.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE repositories
            SET last_updated = ?
            WHERE repo_rid = ?
            """,
            (timestamp, repo_rid)
        )
        conn.commit()
        logger.debug(f"Updated timestamp for {repo_rid}")
    except Exception as e:
        logger.error(f"Error updating timestamp for {repo_rid}: {e}")
    finally:
        conn.close()


def get_repositories(db_path: str) -> List[Dict[str, Any]]:
    """Get all tracked repositories."""
    if not os.path.exists(db_path):
        initialize_db(db_path)
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT repo_rid, repo_url, first_indexed, last_updated
        FROM repositories
        ORDER BY last_updated DESC
        """
    )

    repos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return repos

def get_commits_for_repo(db_path: str, repo_rid: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get commits for a specific repository, ordered by commit timestamp descending. Always returns empty list in simplified version."""
    return []

def get_events_for_repo(db_path: str, repo_rid: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get events for a specific repository, ordered by timestamp descending."""
    if not os.path.exists(db_path):
        initialize_db(db_path)
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT event_rid, event_type, timestamp, commit_sha, summary, bundle_rid
        FROM events
        WHERE repo_rid = ?
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
        """,
        (repo_rid, limit, offset)
    )

    events = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return events

def get_files_at_commit(db_path: str, repo_rid: str, commit_sha: str, path_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get files for a specific commit. Always returns empty list in simplified version."""
    return []

def search_files(db_path: str, repo_rid: Optional[str], extension: Optional[str], path_fragment: Optional[str], limit: int = 100) -> List[Dict[str, Any]]:
    """Search files by repository, extension, and/or path fragment. Always returns empty list in simplified version."""
    return []

def get_file_history(db_path: str, repo_rid: str, path: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get the history of a specific file path across commits. Always returns empty list in simplified version."""
    return []

def prune_old_data(db_path: str, days_to_keep: int = 90) -> None:
    """Remove old events and related data beyond a certain age."""
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete old events
    cursor.execute(
        """
        DELETE FROM events
        WHERE timestamp < datetime('now', '-' || ? || ' days')
        """,
        (days_to_keep,)
    )

    deleted_events = cursor.rowcount

    # Note: Not deleting commits or files as they are valuable historical data
    # even if the associated events are pruned

    conn.commit()
    conn.close()

    logger.info(f"Pruned {deleted_events} events older than {days_to_keep} days")
