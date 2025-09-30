# Changelog
GCS Upload release notes

## [Unreleased]

## v2.0.2 - 2025-09-27
### Updated
- **Documentation**: Updated documentation

## v2.0.0 - 2025-09-15
### Updated
- **Configuration Parameter Naming**: Renamed `image_folder` to `image_directory` for consistency with Linux naming conventions
- **Configuration Validation**: Enhanced `normalize_config()` method with comprehensive validation to prevent typos and provide helpful error messages
- **Documentation**: Completely updated `overview.md` with comprehensive sample pipelines, use cases, and configuration examples
- **Test Suite**: Improved test coverage with better error handling and validation testing

### Added
- **Configuration Validation System**: 
  - Validates user-provided configuration keys to prevent typos
  - Special handling for common typos (e.g., `image_folder` → `image_directory`)
- **Comprehensive Documentation**:
  - 4 complete sample pipeline examples showing real-world usage
  - 4 detailed use case scenarios (Security, Content Creation, IoT, Live Streaming)
  - Environment variable configuration examples
- **Enhanced Test Coverage**:
  - Integration tests for configuration normalization
  - Smoke tests for filter lifecycle management
  - Comprehensive validation testing for all configuration parameters
- **Error Handling Improvements**:
  - Better error messages for configuration validation
  - Runtime key management to prevent false validation errors


## v1.5.3 - 2025-07-15
### Updated
- Migrated from filter_runtime to openfilter

### Added
- Makefile installs in editable mode by default
- Updated docs

## v1.5.2 - 2025-04-15

### Changed
- Internal improvements

## v1.5.1 - 2025-04-15
### Added
- Support for RTSP streaming input via `rtsp-streamer` service
- Docker Compose configuration for RTSP-based video ingestion pipeline

### Changed
- Enhanced GCS video connector with file size stability verification to prevent uploading incomplete files
- Fixed issue with corrupted video file uploads by implementing file completion detection
- Improved upload reliability by ensuring files have reached a stable size before transfer


## v1.5.0 - 2025-04-09

### Added
- Support for image file uploads to GCS buckets via `image_folder` configuration
- Improved error handling and logging for upload failures
- File locking mechanism to prevent concurrent uploads of the same file

### Changed
- Enhanced base uploader class with common upload functionality
- Separated video and image upload logic into distinct uploader classes

## v1.4.13 - 2024-03-26

### Added
- Internal improvements

## v1.4.0

### Added
- Initial Release: new GCS Upload filter for uploading video segments to Google Cloud Storage (GCS).

- **GCS Output Support**
  - Streams output video files to `gs://` buckets
  - Supports multiple outputs with validation for unique prefixes

- **Manifest Generation**
  - Optional JSON manifest file can be created and uploaded alongside video files
  - Manifest structure is configurable via `manifest_field` path (supports nested keys like `a.b.c`)

- **Flexible Template Sources**
  - Manifest templates can be read from `file://`, `gs://`, or downloaded dynamically
  - If template is not found, a default manifest is generated automatically

- **Video Output Segmentation**
  - Supports time-based segmentation using `!segtime=N` syntax in output paths

- **Uploader Threads**
  - Parallel uploaders handle background streaming to GCS with retry and cleanup

- **Environment Auth**
  - Uses `GOOGLE_APPLICATION_CREDENTIALS` for authentication to GCP
