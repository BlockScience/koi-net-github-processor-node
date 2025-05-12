import os
import asyncio
import logging
from typing import Dict, Awaitable, TypeVar
from . import utils

logger = logging.getLogger(__name__)

# Dictionary to hold locks per repository directory
repo_locks: Dict[str, asyncio.Lock] = {}

T = TypeVar('T')  # Generic type for the coroutine return value

def get_repo_base_path(base_path: str) -> str:
    """
    Return the base path for all repositories.
    Creates the directory if it doesn't exist.
    """
    os.makedirs(base_path, exist_ok=True)
    return base_path

def get_repo_dir(base_path: str, repo_rid: str) -> str:
    """
    Convert a repository RID to a local bare repository directory path.

    Args:
        base_path: The base directory for all repositories
        repo_rid: The repository RID (orn:github.repo:owner/repo)

    Returns:
        Path to the bare repository directory (base_path/owner/repo.git)
    """
    if not repo_rid.startswith("orn:github.repo:"):
        raise ValueError(f"Invalid GitHub repository RID format: {repo_rid}")

    # Convert to a sanitized directory name
    dir_name = utils.repo_rid_to_dirname(repo_rid)
    # Return an absolute, normalized path to avoid any path resolution issues
    return os.path.abspath(os.path.normpath(os.path.join(base_path, dir_name)))

async def with_repo_lock(repo_dir: str, coro: Awaitable[T]) -> T:
    """
    Execute an asynchronous coroutine while holding a lock for a specific repository.

    This ensures that only one operation can be performed on a repository at a time.

    Args:
        repo_dir: The repository directory path
        coro: The coroutine to run with the repository lock

    Returns:
        The result of the coroutine
    """
    # Normalize the repository path to ensure consistent lock keys
    repo_dir = os.path.abspath(os.path.normpath(repo_dir))
    
    # Get or create a lock for this repository
    lock = repo_locks.setdefault(repo_dir, asyncio.Lock())

    # Acquire the lock and execute the coroutine
    try:
        async with lock:
            logger.debug(f"Acquired lock for repository: {repo_dir}")
            return await coro
    except Exception as e:
        logger.error(f"Error while executing operation with lock on {repo_dir}: {e}")
        raise
    finally:
        logger.debug(f"Released lock for repository: {repo_dir}")

def get_repo_lock(repo_dir: str) -> asyncio.Lock:
    """
    Get the lock for a specific repository.
    Creates a new lock if one doesn't exist.

    Args:
        repo_dir: The repository directory path

    Returns:
        An asyncio.Lock for the repository
    """
    # Normalize the repository path to ensure consistent lock keys
    repo_dir = os.path.abspath(os.path.normpath(repo_dir))
    return repo_locks.setdefault(repo_dir, asyncio.Lock())

def clear_locks() -> None:
    """Clear all repository locks (typically used in tests)."""
    repo_locks.clear()
    logger.debug("Cleared all repository locks")
