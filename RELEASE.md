# Changelog
GCS Upload release notes

## [Unreleased]

## v2.0.9 - 2026-08-20

### Changed

- Build the filter image on `openfilter-base:py3.14` (was `py3.11`). The published wheel supports Python 3.14, so the image now ships 3.14. Running on 3.10–3.13 is unaffected.

## v2.0.8 - 2026-08-18

### Changed

- Update the openfilter dependency to 1.3.0
- Add Python 3.14 support: raise the `requires-python` ceiling to `<3.15`; the CI test matrix now runs 3.10–3.14.

## v2.0.7 - 2026-08-10

### Changed

- Build the image on `openfilter-base` (weekly apt-upgraded python-slim) instead of a stale `python:X.Y.Z-slim` pin, clearing the OS-package CVEs the pin carried.
- Update the openfilter dependency to 1.2.2

## v2.0.6 - 2026-08-04

### Changed
- Update `openfilter[all]` to `>=1.2.1`.
- Grant `id-token: write` in `create-release.yaml` so the public release workflow can produce a keyless (cosign) SBOM attestation for the published image (once the shared SBOM steps land).
- Fix the `RELEASE.md` header (`# Changelog` first line; a stray `# v2.0.5` H1 plus a duplicated `# Changelog`/`[Unreleased]` block broke the changelog-parser).
- Pin the Docker base to `python:3.11.12-slim` (was `python:3.11-slim`).
- Fix the `docker-compose.yaml` utility images (were the malformed `openfilter-video-in`/`webvis` + `-connector-gcs` concatenation) and point them at `containers.openfilter.io/plainsightai/openfilter-{video-in,webvis}:1.2.1`; pin the filter's own image to `openfilter-connector-gcs:2.0.6`.
- Update dev-tooling floors (`setuptools>=83.0.0`) and switch dev pins to range pins.

## v2.0.5 - 2026-04-23

### Changed
- Update the openfilter dependency to `>=0.1.30`, and align the CI workflow with the shared release gate (source-paths).
- Fix release workflow secret names: `PYPI_API_TOKEN` → `PLAINSIGHT_PYPI_TOKEN`, `DOCKERHUB_TOKEN` → `DOCKERHUB_ACCESS_TOKEN` (org-level secret names). Without this the PyPI / Docker Hub tokens resolved to empty and no package has been published since the migration.

## v2.0.4 - 2026-04-20

### Changed
- Remove redundant ci.yaml (shared workflow handles PR testing)
- Add push + pull_request triggers to create-release.yaml

## v2.0.3 - 2026-04-15

### Changed
- Add CI/CD workflows: create-release.yaml (Docker Hub publishing), ci.yaml (PR testing), security-scan.yaml
- Update openfilter dependency to >=0.1.27

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
