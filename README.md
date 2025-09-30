# GCS Upload

[![PyPI version](https://img.shields.io/pypi/v/filter-connector-gcs.svg?style=flat-square)](https://pypi.org/project/filter-connector-gcs/)
[![Docker Version](https://img.shields.io/docker/v/plainsightai/openfilter-connector-gcs?sort=semver)](https://hub.docker.com/r/plainsightai/openfilter-connector-gcs)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/PlainsightAI/filter-connector-gcs/blob/main/LICENSE)

A specialized OpenFilter component that uploads video segments and images to Google Cloud Storage buckets. Supports segmented video outputs, image uploads from upstream filters, optional manifest generation, and comprehensive configuration validation.

## Features

- **Google Cloud Storage Output**: Uploads video segments to `gs://` destinations with wildcards and segment intervals
- **Image Upload Support**: Monitors directories for images from upstream filters and uploads them to GCS
- **Manifest Generation**: Creates JSON manifests listing all uploaded files with nested field support
- **Configuration Validation**: Prevents typos with helpful error messages and suggestions
- **Concurrent Uploading**: Background threads handle uploads with file locking for images
- **Flexible Templates**: Manifest templates from `file://`, `gs://`, or cached sources

## Quick Start

### Prerequisites

**IMPORTANT!** You need access to GCP and the `gcloud` CLI installed and authenticated:

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project (replace with your project ID)
gcloud config set project your-project-id
gcloud auth configure-docker us-west1-docker.pkg.dev
```

### Installation

```bash
# Create virtual environment
virtualenv venv
source venv/bin/activate

# Install the filter
make install
```

### Basic Usage

```python
from openfilter import Filter

# Simple video recording pipeline
filters = [
    Filter("VideoIn", {
        "sources": "file://sample_video.mp4",
        "outputs": "tcp://127.0.0.1:5550"
    }),
    Filter("FilterConnectorGCS", {
        "sources": "tcp://127.0.0.1:5550",
        "outputs": "gs://my-bucket/videos/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5",
        "workdir": "./temp_videos",
        "timeout": 60.0
    }),
    Filter("Webvis", {
        "sources": "tcp://127.0.0.1:5550",
        "outputs": "tcp://127.0.0.1:8080"
    })
]

Filter.run_multi(filters, exit_time=30.0)
```

## Documentation

For comprehensive documentation including:
- Complete configuration reference
- Sample pipelines and use cases
- Troubleshooting guides
- API documentation

**Refer to [docs/overview.md](https://github.com/PlainsightAI/filter-connector-gcs/blob/main/docs/overview.md)**

## Development

### Running Locally

```bash
# Run the filter locally
make run

# Navigate to http://localhost:8000 to see the video
```

### Running in Docker

```bash
# Build the filter docker image
make build-image

# Generate docker-compose.yaml (if needed)
make compose

# Run the containerized filter
make run-image
```

**Note**: If your filter uses GPU, ensure the `deploy:` section in `docker-compose.yaml` includes GPU configuration:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

### Testing

```bash
# Run unit tests
make test

# Run specific test files
pytest tests/test_vid2gs.py -v
pytest tests/test_smoke_simple.py -v
pytest tests/test_integration_config_normalization.py -v
```

## Configuration Examples

### Basic Video Upload
```json
{
    "id": "gcs_uploader",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": "gs://my-bucket/videos/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5",
    "workdir": "./temp_videos",
    "timeout": 60.0
}
```

### With Image Upload and Manifest
```json
{
    "id": "gcs_uploader",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": "gs://my-bucket/videos/stream_%Y-%m-%d_%H-%M-%S.mp4!segtime=1.0",
    "image_directory": "./unique_frames",
    "manifest": "file://manifest_template.json",
    "manifest_field": "stream_data.files",
    "workdir": "./temp_processing",
    "timeout": 120.0
}
```

### Multiple Outputs
```json
{
    "id": "multi_gcs_uploader",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": [
        "gs://primary-bucket/videos/feed_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.2",
        "gs://backup-bucket/archive/feed_%Y-%m-%d_%H-%M-%S.mp4!segtime=2.0"
    ],
    "manifest": "gs://primary-bucket/templates/manifest.json",
    "manifest_field": "recordings.files",
    "workdir": "./temp",
    "timeout": 180.0
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to GCP service account key JSON file |

## Use Cases

- **Security Camera Monitoring**: 24/7 recording with automatic cloud backup
- **Content Creation**: Multi-destination uploads with thumbnail extraction
- **IoT Data Collection**: Device-specific data collection with structured metadata
- **Live Streaming Archive**: Real-time streaming with dual outputs

See [docs/overview.md](https://github.com/PlainsightAI/filter-connector-gcs/blob/main/docs/overview.md) for detailed use case examples and sample pipelines.

## Publishing

To publish a new version:

1. **Update Version**: Ensure `VERSION` file has a production semver tag (e.g., `v2.0.0`)
2. **Update Release Notes**: Add new entry to `RELEASE.md` with changes
3. **Merge to Main**: CI will automatically:
   - Build and publish Docker image to GAR OCI registry
   - Build and publish Python wheel to GAR Python registry
   - Push docs to production and development documentation sites

**Important**: Releases are documentation-driven. Not updating `RELEASE.md` will not trigger a release.