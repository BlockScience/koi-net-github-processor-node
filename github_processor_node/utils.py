import os
import re
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def repo_rid_to_dirname(repo_rid: str) -> str:
    """
    Convert a repository RID to a sanitized directory name.

    Args:
        repo_rid: The repository RID (orn:github.repo:owner/repo)

    Returns:
        Sanitized directory name (owner__repo.git)
    """
    if not repo_rid.startswith("orn:github.repo:"):
        raise ValueError(f"Invalid GitHub repository RID format: {repo_rid}")

    # Extract owner/repo part
    owner_repo = repo_rid.split("orn:github.repo:", 1)[1]

    # Convert slashes to double underscores for filesystem safety
    dir_name = owner_repo.replace("/", "__") + ".git"

    return dir_name

# RID conversion utilities
def owner_repo_to_repo_rid(owner: str, repo: str) -> str:
    """Convert GitHub owner and repo to a repository RID."""
    return f"orn:github.repo:{owner}/{repo}"

def repo_rid_to_owner_repo(repo_rid: str) -> Tuple[str, str]:
    """Extract GitHub owner and repo from a repository RID."""
    if not repo_rid.startswith("orn:github.repo:"):
        raise ValueError(f"Invalid GitHub repository RID format: {repo_rid}")

    owner_repo = repo_rid.split("orn:github.repo:", 1)[1]
    try:
        owner, repo = owner_repo.split("/", 1)
        return owner, repo
    except ValueError:
        raise ValueError(f"Invalid GitHub repository RID format: {repo_rid}")

def get_repo_dir_from_rid(base_path: str, repo_rid: str) -> str:
    """Convert a repository RID to a local directory path."""
    if not repo_rid.startswith("orn:github.repo:"):
        raise ValueError(f"Invalid GitHub repository RID format: {repo_rid}")

    # Extract owner/repo part and create path
    owner_repo = repo_rid.split("orn:github.repo:", 1)[1]
    # Use slashes directly as directory structure
    return os.path.join(base_path, owner_repo + ".git")

def get_repo_rid_from_url(repo_url: str) -> str:
    """Extract repository RID from a GitHub URL."""
    # Handle various GitHub URL formats
    parsed = urlparse(repo_url)

    # Only handle github.com URLs
    if not parsed.netloc.endswith("github.com"):
        raise ValueError(f"Not a GitHub URL: {repo_url}")

    # Remove .git suffix if present
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]

    # Split the path, remove empty parts
    parts = [p for p in path.split("/") if p]

    # Need at least owner/repo
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL format: {repo_url}")

    # Extract owner and repo
    owner = parts[0]
    repo = parts[1]

    return owner_repo_to_repo_rid(owner, repo)

def sanitize_git_reference(reference: str) -> str:
    """Sanitize a Git reference to prevent command injection."""
    # Only allow alphanumeric, dash, underscore, slash, and dot in references
    if not re.match(r'^[a-zA-Z0-9\-_.\/]+$', reference):
        raise ValueError(f"Invalid Git reference format: {reference}")
    return reference

def parse_commit_message(message: str) -> Dict[str, Any]:
    """Parse a Git commit message into structured components."""
    lines = message.strip().split("\n")

    result = {
        "subject": lines[0] if lines else "",
        "body": "\n".join(lines[1:]).strip() if len(lines) > 1 else "",
        "references": [],
        "categories": []
    }

    # Extract issue references
    issue_refs = re.findall(r'(#[0-9]+)', message)
    result["references"] = list(set(issue_refs))

    # Extract potential categories from conventional commit format
    if result["subject"] and ":" in result["subject"]:
        category = result["subject"].split(":", 1)[0].lower()
        if re.match(r'^[a-z]+(\([a-z0-9_-]+\))?$', category):
            result["categories"].append(category)

    return result

def format_unix_path(path: str) -> str:
    """Normalize a path to use forward slashes."""
    return path.replace("\\", "/")

def get_file_extension(path: str) -> str:
    """Extract file extension from path."""
    _, ext = os.path.splitext(path)
    return ext.lower()[1:] if ext else ""  # Remove leading dot

def format_timestamp(timestamp: str) -> str:
    """Normalize a timestamp to ISO format."""
    # Simple implementation assuming timestamp is already in a sensible format
    # A more robust implementation would handle different input formats
    return timestamp

def is_binary_extension(extension: str) -> bool:
    """Check if a file extension typically indicates binary content."""
    binary_extensions = {
        # Images
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'ico', 'svg',
        # Audio/Video
        'mp3', 'wav', 'ogg', 'mp4', 'avi', 'mov', 'webm', 'flac',
        # Archives
        'zip', 'tar', 'gz', 'bz2', 'xz', '7z', 'rar',
        # Documents
        'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
        # Executables
        'exe', 'dll', 'so', 'dylib',
        # Other binaries
        'bin', 'dat', 'iso', 'class'
    }
    return extension.lower() in binary_extensions

def summarize_event(event_type: str, repo_rid: str, commit_sha: Optional[str] = None, additional_info: Optional[Dict[str, Any]] = None) -> str:
    """Generate a human-readable summary of a GitHub event."""
    try:
        owner, repo = repo_rid_to_owner_repo(repo_rid)
    except ValueError:
        owner, repo = "unknown", "unknown"

    # Basic summary based on event type
    if event_type == "push":
        if commit_sha:
            return f"Push to {owner}/{repo}: {commit_sha[:7]}"
        return f"Push to {owner}/{repo}"
    elif event_type == "pull_request":
        action = additional_info.get("action", "updated") if additional_info else "updated"
        pr_number = additional_info.get("number", "unknown") if additional_info else "unknown"
        return f"Pull request #{pr_number} {action} in {owner}/{repo}"
    elif event_type == "issues":
        action = additional_info.get("action", "updated") if additional_info else "updated"
        issue_number = additional_info.get("number", "unknown") if additional_info else "unknown"
        return f"Issue #{issue_number} {action} in {owner}/{repo}"
    elif event_type == "release":
        tag = additional_info.get("tag_name", "unknown") if additional_info else "unknown"
        return f"Release {tag} created in {owner}/{repo}"
    else:
        # Generic summary for other event types
        return f"{event_type.replace('_', ' ').title()} event in {owner}/{repo}"
