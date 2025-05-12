# GitHub Event Processor for KOI-net v1.0.0

![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Test Coverage](https://img.shields.io/badge/coverage-80%25-yellowgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)
![Support](https://img.shields.io/badge/support-active-brightgreen.svg)

A streamlined Knowledge Organization Infrastructure (KOI) network node that processes GitHub events from a GitHub Sensor node. It extracts and stores repository and event metadata without performing Git operations, providing a lightweight solution for tracking GitHub activity within a KOI-net ecosystem.

## Key Benefits
- **Lightweight Processing**: Stores only metadata without cloning repositories or accessing file contents
- **Low Resource Usage**: Minimal CPU and disk space requirements with no Git operations
- **Fast Event Processing**: Quick event handling without waiting for Git operations
- **KOI-net Integration**: Fully compatible with the KOI-net protocol for distributed knowledge sharing

## Table of Contents
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Examples](#examples)
- [Contributing](#contributing)
- [Testing](#testing)
- [CI/CD & Deployment](#cicd--deployment)
- [Versioning & Changelog](#versioning--changelog)
- [License](#license)
- [Contact & Support](#contact--support)

## Installation

### Using pip

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install koi-net-github-processor
```

### Using Docker

```bash
# Pull the Docker image
docker pull blockscience/koi-net-github-processor:latest

# Run using Docker
docker run -p 8004:8004 -v $(pwd)/config.yaml:/app/config.yaml blockscience/koi-net-github-processor
```

### From Source

```bash
# Clone the repository
git clone https://github.com/BlockScience/koi-net-github-processor.git
cd koi-net-github-processor

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Run tests
pytest
```

## Quick Start

1. Create a configuration file:

```bash
# Create a basic config.yaml
cat > config.yaml << EOF
server:
  host: 127.0.0.1
  port: 8004
  path: /koi-net
koi_net:
  node_name: processor_github
  node_rid: orn:koi-net.node:processor_github+0bf78f28-9f56-4d31-8377-a33f49a0828e
  node_profile:
    base_url: http://127.0.0.1:8004/koi-net
    node_type: FULL
    provides:
      event: []
      state: []
  cache_directory_path: .koi/processor-github/cache
  event_queues_path: .koi/processor-github/queues.json
  first_contact: http://127.0.0.1:8000/koi-net
index_db_path: .koi/processor-github/index.db
env:
  github_token: GITHUB_TOKEN
EOF
```

2. Set environment variables:

```bash
export GITHUB_TOKEN=your_github_personal_access_token
```

3. Start the processor:

```bash
# Using Python module
python -m processor_github_node

# Alternative using make (if available)
make processor-gh
```

## Usage

### Using the CLI

The GitHub Processor comes with a CLI tool for exploring stored events:

```bash
# List all tracked repositories
python cli.py list-repos

# Show events for a specific repository
python cli.py show-events sayertindall/koi-net

# Show detailed information about a specific event
python cli.py event-details orn:github.event:blockscience/koi-net:event123

# Add a repository to track
python cli.py add-repo blockscience/koi-net

# Show a summary of all events in the database
python cli.py summarize-events
```

### Using the API

```python
import requests

# List repositories
response = requests.get("http://localhost:8004/api/processor/github/repositories")
repositories = response.json()
print(f"Tracked repositories: {len(repositories)}")

# Get events for a repository
repo_rid = "orn:github.repo:blockscience/koi-net"
response = requests.get(
    f"http://localhost:8004/api/processor/github/repositories/{repo_rid}/events",
    params={"limit": 10, "offset": 0}
)
events = response.json()
print(f"Found {len(events)} events for {repo_rid}")
```

## Configuration

The processor is configured using a YAML file with the following options:

| Option | Default | Description | Required |
|--------|---------|-------------|----------|
| `server.host` | `127.0.0.1` | Host address to bind the server to | Yes |
| `server.port` | `8004` | Port to listen on | Yes |
| `server.path` | `/koi-net` | Base path for KOI-net API endpoints | Yes |
| `koi_net.node_name` | `processor_github` | Name of this node | Yes |
| `koi_net.node_rid` | Generated | Unique RID for this node | No |
| `koi_net.node_profile.base_url` | Based on server config | Base URL for this node's API | No |
| `koi_net.node_profile.node_type` | `FULL` | Node type (FULL or PARTIAL) | Yes |
| `koi_net.node_profile.provides` | Empty lists | RID types provided by this node | Yes |
| `koi_net.cache_directory_path` | `.koi/processor-github/cache` | Path to cache directory | Yes |
| `koi_net.event_queues_path` | `.koi/processor-github/queues.json` | Path to event queues file | Yes |
| `koi_net.first_contact` | None | URL of first node to contact | No |
| `index_db_path` | `.koi/processor-github/index.db` | Path to SQLite database | Yes |
| `env.github_token` | `GITHUB_TOKEN` | Environment variable name for GitHub token | Yes |

### Sample Configuration File

```yaml
server:
  host: 127.0.0.1
  port: 8004
  path: /koi-net
koi_net:
  node_name: processor_github
  node_rid: orn:koi-net.node:processor_github+0bf78f28-9f56-4d31-8377-a33f49a0828e
  node_profile:
    base_url: http://127.0.0.1:8004/koi-net
    node_type: FULL
    provides:
      event: []
      state: []
  cache_directory_path: .koi/processor-github/cache
  event_queues_path: .koi/processor-github/queues.json
  first_contact: http://127.0.0.1:8000/koi-net
index_db_path: .koi/processor-github/index.db
env:
  github_token: GITHUB_TOKEN
```

## API Reference

### KOI-net Protocol Endpoints

#### POST /koi-net/events/broadcast

Receives events broadcast from other nodes.

**Request Body:**
```json
{
  "events": [
    {
      "rid": "orn:github.event:owner/repo:event123",
      "event_type": "NEW",
      "manifest": {
        "rid": "orn:github.event:owner/repo:event123",
        "timestamp": "2023-01-01T12:00:00Z",
        "sha256_hash": "hash123"
      },
      "contents": {}
    }
  ]
}
```

**Response:** No content (204)

#### POST /koi-net/events/poll

Allows partial nodes to poll for events.

**Request Body:**
```json
{
  "rid": "orn:koi-net.node:some-node+uuid",
  "limit": 50
}
```

**Response:**
```json
{
  "events": [
    {
      "rid": "orn:github.event:owner/repo:event123",
      "event_type": "NEW",
      "manifest": {
        "rid": "orn:github.event:owner/repo:event123",
        "timestamp": "2023-01-01T12:00:00Z",
        "sha256_hash": "hash123"
      },
      "contents": {}
    }
  ]
}
```

#### POST /koi-net/rids/fetch

Retrieves RIDs of a specific type.

**Request Body:**
```json
{
  "rid_types": ["orn:github.event"]
}
```

**Response:**
```json
{
  "rids": [
    "orn:github.event:owner/repo:event123",
    "orn:github.event:owner/repo:event456"
  ]
}
```

#### POST /koi-net/manifests/fetch

Retrieves manifests for specific RIDs.

**Request Body:**
```json
{
  "rids": ["orn:github.event:owner/repo:event123"]
}
```

**Response:**
```json
{
  "manifests": [
    {
      "rid": "orn:github.event:owner/repo:event123",
      "timestamp": "2023-01-01T12:00:00Z",
      "sha256_hash": "hash123"
    }
  ],
  "not_found": []
}
```

#### POST /koi-net/bundles/fetch

Retrieves full bundles for specific RIDs.

**Request Body:**
```json
{
  "rids": ["orn:github.event:owner/repo:event123"]
}
```

**Response:**
```json
{
  "bundles": [
    {
      "manifest": {
        "rid": "orn:github.event:owner/repo:event123",
        "timestamp": "2023-01-01T12:00:00Z",
        "sha256_hash": "hash123"
      },
      "contents": {
        "event_source_type": "push",
        "repository": {
          "name": "repo",
          "owner": {
            "login": "owner"
          }
        }
      }
    }
  ],
  "not_found": [],
  "deferred": []
}
```

### GitHub Processor API Endpoints

#### GET /api/processor/github/status

Get the current status of the GitHub processor.

**Response:**
```json
{
  "status": "active",
  "message": "GitHub processor node is running",
  "details": {
    "node_name": "processor_github",
    "node_type": "FULL",
    "db_path": ".koi/processor-github/index.db"
  }
}
```

#### GET /api/processor/github/repositories

List all tracked repositories.

**Response:**
```json
[
  {
    "repo_rid": "orn:github.repo:owner/repo",
    "repo_url": "https://github.com/owner/repo.git",
    "first_indexed": "2023-01-01T12:00:00Z",
    "last_updated": "2023-01-02T12:00:00Z"
  }
]
```

#### GET /api/processor/github/repositories/{repo_rid}/events

Get events for a specific repository.

**Query Parameters:**
- `limit` (optional): Maximum number of events to return (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "event_rid": "orn:github.event:owner/repo:event123",
    "event_type": "push",
    "timestamp": "2023-01-01T12:00:00Z",
    "commit_sha": "abcdef123456",
    "summary": "Push to owner/repo: abcdef1",
    "bundle_rid": "orn:github.event:owner/repo:event123"
  }
]
```

## Architecture

The GitHub Processor consists of several key components that work together to process GitHub events and provide access to the stored data:

```
┌─────────────────┐     ┌────────────────┐     ┌────────────────┐
│  GitHub Sensor  │────>│  KOI-net Node  │────>│ Other KOI-net  │
│     (events)    │     │   Interface    │     │     Nodes      │
└─────────────────┘     └────────┬───────┘     └────────────────┘
                                 │
                                 ▼
               ┌─────────────────────────────────┐
               │       Processor Interface       │
               │                                 │
               │  ┌─────────────┐ ┌───────────┐  │
               │  │    Event    │ │  Network  │  │
               │  │  Handlers   │ │  Handlers │  │
               │  └─────────────┘ └───────────┘  │
               └──────────────┬──────────────────┘
                              │
                              ▼
      ┌───────────────────────────────────────────────┐
      │              Repository Service               │
      └─────────────────────┬─────────────────────────┘
                            │
                            ▼
      ┌───────────────────────────────────────────────┐
      │               Index Database                  │
      │  ┌────────────┐  ┌─────────┐  ┌───────────┐   │
      │  │Repositories│  │ Events  │  │  Metadata │   │
      │  └────────────┘  └─────────┘  └───────────┘   │
      └───────────────────────────────────────────────┘
                            │
                            ▼
      ┌───────────────────────────────────────────────┐
      │                REST API / CLI                 │
      └───────────────────────────────────────────────┘
```

### Component Responsibilities

- **KOI-net Node Interface**: Handles communication with other nodes in the KOI-net network.
- **Processor Interface**: Processes incoming GitHub events through a pipeline of handlers.
- **Event Handlers**: Extract and normalize data from GitHub events.
- **Network Handlers**: Manage communication with other nodes, including edge negotiation.
- **Repository Service**: Core service managing GitHub repository data and events.
- **Index Database**: SQLite database storing metadata about repositories and GitHub events.
- **REST API**: FastAPI-based API for querying repositories and events.
- **CLI**: Command-line interface for interacting with the stored data.

## Examples

### Adding a Repository and Monitoring Events

```python
import requests
import time

# 1. Add a repository to track
repo = "blockscience/koi-net"
requests.post(
    "http://localhost:8004/api/processor/github/repositories",
    json={"repo_url": f"https://github.com/{repo}.git"}
)

# 2. Monitor events for the repository
repo_rid = f"orn:github.repo:{repo}"
while True:
    response = requests.get(
        f"http://localhost:8004/api/processor/github/repositories/{repo_rid}/events"
    )
    events = response.json()
    print(f"Found {len(events)} events for {repo}")
    for event in events:
        print(f"  {event['event_type']} - {event['timestamp']} - {event['summary']}")

    time.sleep(30)  # Check every 30 seconds
```

### Using the CLI to Explore Events

```bash
#!/bin/bash
# This script demonstrates using the CLI to explore GitHub events

# List all repositories
echo "Listing all tracked repositories:"
python cli.py list-repos

# Select the first repository and show its events
REPO_RID=$(python cli.py list-repos | grep 'orn:github.repo' | head -1 | awk '{print $1}')
echo "Showing events for repository: $REPO_RID"
python cli.py show-events $REPO_RID

# Show details for the first event
EVENT_RID=$(python cli.py show-events $REPO_RID | grep 'orn:github.event' | head -1 | awk '{print $NF}')
echo "Showing details for event: $EVENT_RID"
python cli.py event-details $EVENT_RID

# Show overall summary
echo "Showing event summary:"
python cli.py summarize-events
```

## Contributing

Contributions to the GitHub Processor are welcome! Please follow these steps:

1. **Fork the Repository**
   - Create a fork of the repository on GitHub.

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR-USERNAME/koi-net-github-processor.git
   cd koi-net-github-processor
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Changes**
   - Implement your changes
   - Add tests for new functionality

5. **Run Tests**
   ```bash
   pytest
   ```

6. **Commit Changes**
   ```bash
   git commit -am "Add your detailed commit message"
   ```

7. **Push to GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**
   - Go to your fork on GitHub and create a pull request to the main repository.

Please adhere to the project's code style and include appropriate tests with your contributions.

## Testing

Run the test suite with:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=processor_github_node

# Generate HTML coverage report
pytest --cov=processor_github_node --cov-report=html
```

## CI/CD & Deployment

The project uses GitHub Actions for continuous integration:

```yaml
name: GitHub Processor CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10"]

    steps:
    - uses: actions/checkout@v2
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Lint with flake8
      run: flake8 processor_github_node

    - name: Test with pytest
      run: pytest

    - name: Build package
      run: python -m build

    - name: Upload artifacts
      uses: actions/upload-artifact@v2
      with:
        name: dist
        path: dist/
```

## Versioning & Changelog

This project follows [Semantic Versioning](https://semver.org/). For a complete list of changes, see the [CHANGELOG.md](CHANGELOG.md) file.

- **Major version**: Incompatible API changes
- **Minor version**: New functionality in a backward-compatible manner
- **Patch version**: Backward-compatible bug fixes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact & Support

### Maintainers
- BlockScience Team - [info@block.science](mailto:info@block.science)

### Get Help
- Issue Tracker: [GitHub Issues](https://github.com/BlockScience/koi-net-github-processor/issues)
- Discussion: [GitHub Discussions](https://github.com/BlockScience/koi-net-github-processor/discussions)

### Community
- KOI-net Community Forum: [community.koi-net.org](https://community.koi-net.org)
