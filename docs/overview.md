---
title: GCS Upload
sidebar_label: Overview
sidebar_position: 1
---

import Admonition from '@theme/Admonition';

# GCS Upload

The GCS Upload filter is a specialized component that uploads video segments and images to Google Cloud Storage buckets. It supports segmented video outputs, image uploads from upstream filters (like frame deduplication), optional manifest generation, and customizable upload behavior through environment variables and configuration.

## Features

- **Google Cloud Storage Output**  
  Uploads video segments to `gs://` destinations, supporting wildcards and segment intervals (e.g., `video_%Y-%m-%d_%H-%M-%S.mp4!segtime=1`).

- **Image Upload Support**  
  Monitors specified directories for images from upstream filters (like frame deduplication) and uploads them to GCS with file locking to prevent concurrent access.

- **Manifest Generation**  
  Creates a manifest JSON file listing all uploaded files (both videos and images) and places it into GCS alongside the content.

- **Nested Manifest Paths**  
  The manifest field can be a deep path (e.g., `my.happy.files`) to embed the file list inside a nested structure.

- **Flexible Template Sources**  
  Templates for manifests can be pulled from:
  - `file://` (local disk)
  - `gs://` (GCS buckets)
  - Cached remote files

- **Concurrent Uploading**  
  Background threads upload videos and images as they are written and clean up local copies.

- **Segmented Video Output**  
  Video outputs can be chunked using `!segtime` options:
  - `segtime` specifies segment duration in minutes. Means 0.1 minutes = 6 seconds
  - Upload interval is calculated as `min(10, 60 * segtime)` seconds
  - Ensures timely uploads while preventing excessive system load

- **File Locking for Images**  
  Uses `.lock` files to prevent concurrent access when:
  - Uploading files that are still being written
  - Multiple uploaders try to process the same file
  - Ensures clean lock file cleanup even on failures

- **Configuration Validation**  
  Validates user-provided configuration keys to prevent typos and provides helpful error messages with suggestions for correct key names.

- **Environment Configuration**  
  Uses `GOOGLE_APPLICATION_CREDENTIALS` for GCP service account authentication.

## Example Configuration

```python
# Basic configuration with single output
{
    "id": "connector_gcs",
    "sources": "tcp://127.0.0.1:6002",
    "outputs": "gs://my-bucket/videos/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.4",
    "image_directory": "./output",
    "mq_log": "pretty"
}

# Image upload from frame dedup filter
--image_directory /path/to/images

# Manifest configuration
--manifest file://manifest_template.json
--manifest_field videos.segmented

# Multiple outputs with different configurations
{
    "id": "connector_gcs",
    "sources": "tcp://127.0.0.1:6002",
    "outputs": [
        "gs://bucket1/videos/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5",
        "gs://bucket2/backup/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=1.0"
    ],
    "image_directory": "./results/images",
    "manifest": "file://manifest_template.json",
    "manifest_field": "uploaded_files",
    "timeout": 120.0,
    "workdir": "./temp"
}
```

## Sample Pipelines

### 1. Basic Video Recording Pipeline

**Use Case**: Simple video recording with automatic GCS upload

```python
# Pipeline: VideoIn → FilterConnectorGCS → Webvis
from openfilter import Filter

# Video source configuration
video_config = {
    "id": "video_input",
    "sources": "file://sample_video.mp4",
    "outputs": "tcp://127.0.0.1:5550"
}

# GCS connector configuration
gcs_config = {
    "id": "gcs_uploader",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": "gs://my-bucket/recordings/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5",
    "workdir": "./temp_videos",
    "timeout": 60.0
}

# Webvis for monitoring
webvis_config = {
    "id": "webvis",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": "tcp://127.0.0.1:8080"
}

# Run the pipeline
filters = [
    Filter("VideoIn", video_config),
    Filter("FilterConnectorGCS", gcs_config),
    Filter("Webvis", webvis_config)
]

Filter.run_multi(filters, exit_time=30.0)
```

### 2. Frame Deduplication with Image Upload

**Use Case**: Extract unique frames and upload both video segments and images

```python
# Pipeline: VideoIn → FrameDedup → FilterConnectorGCS → Webvis
from openfilter import Filter

# Video input
video_config = {
    "id": "video_input",
    "sources": "rtsp://camera.local:554/stream",
    "outputs": "tcp://127.0.0.1:5550"
}

# Frame deduplication (extracts unique frames)
dedup_config = {
    "id": "frame_dedup",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": "tcp://127.0.0.1:5551",
    "image_directory": "./unique_frames",  # Outputs unique frames here
    "threshold": 0.8
}

# GCS connector with both video and image upload
gcs_config = {
    "id": "gcs_uploader",
    "sources": "tcp://127.0.0.1:5551",
    "outputs": "gs://my-bucket/videos/stream_%Y-%m-%d_%H-%M-%S.mp4!segtime=1.0",
    "image_directory": "./unique_frames",  # Uploads images from dedup
    "manifest": "file://manifest_template.json",
    "manifest_field": "stream_data.files",
    "workdir": "./temp_processing",
    "timeout": 120.0
}

# Webvis for monitoring
webvis_config = {
    "id": "webvis",
    "sources": "tcp://127.0.0.1:5551",
    "outputs": "tcp://127.0.0.1:8080"
}

filters = [
    Filter("VideoIn", video_config),
    Filter("FilterFrameDedup", dedup_config),
    Filter("FilterConnectorGCS", gcs_config),
    Filter("Webvis", webvis_config)
]

Filter.run_multi(filters, exit_time=300.0)  # 5 minutes
```

### 3. Multi-Output Backup Pipeline

**Use Case**: Record to multiple GCS buckets with different segment durations

```python
# Pipeline: VideoIn → FilterConnectorGCS (multiple outputs)
from openfilter import Filter

# Video input
video_config = {
    "id": "video_input",
    "sources": "file://security_camera.mp4",
    "outputs": "tcp://127.0.0.1:5550"
}

# GCS connector with multiple outputs
gcs_config = {
    "id": "multi_gcs_uploader",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": [
        "gs://primary-bucket/security/feed_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.2",  # 12-second segments
        "gs://backup-bucket/archive/feed_%Y-%m-%d_%H-%M-%S.mp4!segtime=2.0",    # 2-minute segments
        "gs://analytics-bucket/processed/feed_%Y-%m-%d_%H-%M-%S.mp4!segtime=5.0" # 5-minute segments
    ],
    "manifest": "gs://primary-bucket/templates/security_manifest.json",
    "manifest_field": "security_feed.recordings",
    "workdir": "./security_temp",
    "timeout": 180.0
}

filters = [
    Filter("VideoIn", video_config),
    Filter("FilterConnectorGCS", gcs_config)
]

Filter.run_multi(filters, exit_time=600.0)  # 10 minutes
```

### 4. Real-time Processing with Image Analysis

**Use Case**: Process video stream, extract frames for analysis, upload both

```python
# Pipeline: VideoIn → ObjectDetection → FilterConnectorGCS → Webvis
from openfilter import Filter

# Video input
video_config = {
    "id": "video_input",
    "sources": "rtsp://192.168.1.100:554/stream",
    "outputs": "tcp://127.0.0.1:5550"
}

# Object detection (outputs annotated frames)
detection_config = {
    "id": "object_detection",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": "tcp://127.0.0.1:5551",
    "image_directory": "./detected_frames",  # Saves annotated frames
    "model": "yolov8n.pt",
    "confidence": 0.5
}

# GCS connector
gcs_config = {
    "id": "gcs_uploader",
    "sources": "tcp://127.0.0.1:5551",
    "outputs": "gs://ai-bucket/videos/processed_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5",
    "image_directory": "./detected_frames",  # Uploads annotated frames
    "manifest": "file://ai_manifest_template.json",
    "manifest_field": "ai_processing.results",
    "workdir": "./ai_temp",
    "timeout": 90.0
}

# Webvis for monitoring
webvis_config = {
    "id": "webvis",
    "sources": "tcp://127.0.0.1:5551",
    "outputs": "tcp://127.0.0.1:8080"
}

filters = [
    Filter("VideoIn", video_config),
    Filter("FilterObjectDetection", detection_config),
    Filter("FilterConnectorGCS", gcs_config),
    Filter("Webvis", webvis_config)
]

Filter.run_multi(filters, exit_time=1800.0)  # 30 minutes
```

## Use Cases

### 1. Security Camera Monitoring

**Scenario**: 24/7 security camera recording with automatic cloud backup

```bash
# Environment variables
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/security-service-account.json"
export GCS_BUCKET="company-security-cameras"
export CAMERA_RTSP="rtsp://camera.company.com:554/stream"

# Configuration
{
    "id": "security_recorder",
    "sources": "rtsp://camera.company.com:554/stream",
    "outputs": "gs://company-security-cameras/camera-01/recording_%Y-%m-%d_%H-%M-%S.mp4!segtime=1.0",
    "workdir": "/tmp/security_temp",
    "timeout": 120.0,
    "manifest": "file://security_manifest.json",
    "manifest_field": "camera_recordings.files"
}
```

**Key Variables Used**:
- `sources`: RTSP camera stream
- `outputs`: GCS path with timestamp wildcards and 1-minute segments
- `workdir`: Temporary storage for video segments
- `timeout`: 2-minute timeout for large file uploads
- `manifest`: JSON file listing all recordings for audit trail

### 2. Content Creation Pipeline

**Scenario**: Process video content, extract thumbnails, upload to multiple destinations

```bash
# Environment variables
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/content-service-account.json"
export PRIMARY_BUCKET="content-primary"
export CDN_BUCKET="content-cdn"
export THUMBNAIL_DIR="/tmp/thumbnails"

# Configuration
{
    "id": "content_processor",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": [
        "gs://content-primary/videos/content_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5",
        "gs://content-cdn/videos/content_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5"
    ],
    "image_directory": "/tmp/thumbnails",
    "workdir": "/tmp/content_temp",
    "timeout": 300.0,
    "manifest": "gs://content-primary/templates/content_manifest.json",
    "manifest_field": "content_assets.videos"
}
```

**Key Variables Used**:
- `outputs`: Multiple GCS destinations for redundancy
- `image_directory`: Thumbnail extraction from upstream filter
- `timeout`: 5-minute timeout for large content files
- `manifest`: Template from GCS bucket
- `manifest_field`: Nested path for organized metadata

### 3. IoT Data Collection

**Scenario**: Collect video data from IoT devices, process, and store with metadata

```bash
# Environment variables
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/iot-service-account.json"
export IOT_BUCKET="iot-data-collection"
export DEVICE_ID="sensor-001"
export PROCESSING_DIR="/data/processing"

# Configuration
{
    "id": "iot_collector",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": "gs://iot-data-collection/devices/sensor-001/data_%Y-%m-%d_%H-%M-%S.mp4!segtime=2.0",
    "image_directory": "/data/processing/frames",
    "workdir": "/data/temp",
    "timeout": 180.0,
    "manifest": "file://iot_manifest_template.json",
    "manifest_field": "device_data.sensor_001.recordings",
    "mq_log": "json"
}
```

**Key Variables Used**:
- `outputs`: Device-specific GCS path with 2-minute segments
- `image_directory`: Frame processing from upstream analysis
- `workdir`: Dedicated temp directory for IoT data
- `manifest_field`: Deep nested path for device-specific metadata
- `mq_log`: JSON logging for structured data collection

### 4. Live Streaming Archive

**Scenario**: Archive live streams with real-time processing and backup

```bash
# Environment variables
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/streaming-service-account.json"
export LIVE_BUCKET="live-streams"
export ARCHIVE_BUCKET="stream-archive"
export STREAM_KEY="live-event-001"

# Configuration
{
    "id": "live_archiver",
    "sources": "tcp://127.0.0.1:5550",
    "outputs": [
        "gs://live-streams/events/live-event-001/stream_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.1",
        "gs://stream-archive/events/live-event-001/stream_%Y-%m-%d_%H-%M-%S.mp4!segtime=5.0"
    ],
    "workdir": "/tmp/live_temp",
    "timeout": 60.0,
    "manifest": "file://live_manifest.json",
    "manifest_field": "live_events.event_001.segments"
}
```

**Key Variables Used**:
- `outputs`: Dual output for live streaming (6-second segments) and archive (5-minute segments)
- `workdir`: Fast temp storage for live processing
- `timeout`: 1-minute timeout for quick live uploads
- `manifest_field`: Event-specific metadata organization

## When to Use

Use this filter when:

- You want to store video output directly in GCS
- You need to upload images from upstream filters (like frame dedup)
- You need a JSON manifest describing stored segments and images
- You're working in cloud-native environments where local storage is temporary

## Configuration Reference

### Required Configuration

| Key              | Type       | Description |
|-------------------|------------|-------------|
| `outputs`         | `string[]` | List of GCS output paths with optional `segtime` (e.g., `gs://bucket/path/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=0.5`) |

### Optional Configuration

| Key              | Type       | Default     | Description |
|-------------------|------------|-------------|-------------|
| `id`              | `string`   | _auto_      | Filter instance identifier |
| `sources`         | `string[]` | _required_  | Input sources (e.g., `tcp://127.0.0.1:5550`) |
| `workdir`         | `string`   | `"work"`    | Temporary working directory for segment files |
| `timeout`         | `float`    | `60.0`      | Timeout (in seconds) for GCS uploads |
| `manifest`        | `string`   | `null`      | Manifest template path (`file://`, `gs://`, or cached) |
| `manifest_field`  | `string`   | `"files"`   | Field in the manifest to write list of uploaded files (supports nested paths like `videos.segmented`) |
| `image_directory` | `string`   | `null`      | Directory to watch for images from upstream filters |
| `mq_log`          | `string`   | `null`      | Message queue logging level (`"pretty"`, `"json"`, etc.) |

### Environment Variables

| Variable                        | Required | Description |
|--------------------------------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes      | Path to GCP service account key JSON file |

### Output Path Format

Output paths support the following format:
```
gs://bucket-name/path/to/file_%Y-%m-%d_%H-%M-%S.mp4!segtime=DURATION
```

Where:
- `%Y-%m-%d_%H-%M-%S` - Timestamp wildcards (strftime format)
- `!segtime=DURATION` - Segment duration in minutes (e.g., `0.5` = 30 seconds)
- Multiple outputs can be specified as an array

### Manifest Configuration

The manifest feature allows you to generate a JSON file listing all uploaded files:

```json
{
  "metadata": {
    "upload_time": "2025-01-15T10:30:00Z",
    "total_files": 5
  },
  "files": [
    "video_2025-01-15_10-30-00_000000.mp4",
    "video_2025-01-15_10-30-30_000000.mp4"
  ]
}
```

**Manifest Sources:**
- `file://path/to/template.json` - Local file
- `gs://bucket/path/template.json` - GCS bucket file
- Cached remote files (via `is_cached_file`)

**Nested Manifest Fields:**
- `"files"` → `{"files": [...]}`
- `"videos.segmented"` → `{"videos": {"segmented": [...]}}`
- `"data.uploads.video_files"` → `{"data": {"uploads": {"video_files": [...]}}}`

### Image Upload Configuration

When `image_directory` is specified:
- **Supported formats**: `.jpg`, `.jpeg`, `.png`
- **Upload location**: `gs://bucket/path/images/`
- **File locking**: Uses `.lock` files to prevent concurrent access
- **Cleanup**: Successfully uploaded images are deleted locally
- **Check interval**: Every 5 seconds for new images

<Admonition type="note" title="Note">
All `outputs` must be unique in their `gs://` path prefix to prevent collisions. Each output path must include both a bucket name and a file path.
</Admonition>

<Admonition type="tip" title="Tip">
For optimal performance:
- Use `segtime` values between 0.1 (6 seconds) and 1 (60 seconds)
- Set `image_directory` to a dedicated directory for image uploads
- Ensure sufficient disk space in the working directory
- Use descriptive manifest field names for better organization
</Admonition>

<Admonition type="warning" title="Configuration Validation">
The filter validates user-provided configuration keys to prevent typos. Common mistakes:
- `image_folder` → should be `image_directory`
- Unknown keys will show helpful error messages with suggestions
- Runtime keys (`pipeline_id`, `device_name`, etc.) are automatically added and ignored
</Admonition>


## Error Handling and Troubleshooting

### Common Configuration Errors

**Typo in configuration key:**
```
ValueError: Unknown config key "image_folder". Did you mean "image_directory"?
```

**Missing required output:**
```
ValueError: must specify at least one output
```

**Invalid GCS path:**
```
ValueError: can only specify gs:// outputs, not file:///path/video.mp4
ValueError: output must have both bucket and a path/file name in gs://bucket
```

**Duplicate output prefixes:**
```
ValueError: duplicate gs:// prefix not allowed: 'gs://bucket/videos/'
```

### GCS Authentication Issues

**Missing credentials:**
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**Solution:** Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Upload Failures

**Timeout errors:**
```
google.cloud.exceptions.DeadlineExceeded: 504 Deadline Exceeded
```

**Solution:** Increase timeout value:
```python
{"timeout": 120.0}  # 2 minutes instead of default 60 seconds
```

**Permission errors:**
```
google.cloud.exceptions.Forbidden: 403 Forbidden
```

**Solution:** Ensure service account has proper GCS permissions:
- `storage.objectCreator`
- `storage.objectViewer`
- `storage.bucketReader`

## How It Works

```shell

        ┌────────────────────┐
        │   FilterRuntime    │
        │  (manages pipeline)│
        └─────────┬──────────┘
                  │
             [new frame arrives]
                  │
                  ▼
        ┌────────────────────┐
        │    Vid2GS.process  │  (inherits .process from VideoOut)
        │   calls VideoOut   │
        │     .process(...)  │
        └─────────┬──────────┘
                  │
                  ▼
        ┌────────────────────┐
        │   VideoWriter      │
        │ .write(image):     │
        │  • If chunk full → │
        │    finalize file   │
        │  • Else append     │
        │    frames          │
        └─────────┬──────────┘
                  │ (local .mp4)
                  ▼
        ┌────────────────────┐
        │   Uploader Thread  │
        │  (runs in a loop)  │
        │   • Wait ~10s      │
        │   • List .mp4      │
        │   • Upload to GCS  │
        │   • Delete local   │
        └────────────────────┘

```

### Image Upload Process

```shell
        ┌────────────────────┐
        │  Image Directory   │
        │  (watched folder)  │
        └─────────┬──────────┘
                  │
             [new image file]
                  │
                  ▼
        ┌────────────────────┐
        │   Image Uploader   │
        │  (runs every 5s)   │
        │   • Check for .jpg │
        │   • Create .lock   │
        │   • Upload to GCS  │
        │   • Delete local   │
        │   • Remove .lock   │
        └────────────────────┘
```

## Performance Considerations

- **Segment Duration**: Shorter segments (0.1-0.5 min) = more frequent uploads but smaller files
- **Upload Interval**: Automatically calculated as `min(10, 60 * segtime)` seconds
- **File Stability**: Video files are checked for size stability before upload
- **Concurrent Access**: Image uploads use file locking to prevent conflicts
- **Memory Usage**: Local files are deleted after successful upload to save disk space