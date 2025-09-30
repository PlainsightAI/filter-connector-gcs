# ---------------------------------
# Repo-specific variables
# ---------------------------------
# Define these for consistency in the repo
REPO_NAME ?= filter-connector-gcs
REPO_NAME_SNAKECASE ?= filter_connector_gcs
REPO_NAME_PASCALCASE ?= FilterConnectorGCS

IMAGE ?= us-west1-docker.pkg.dev/plainsightai-prod/oci/${REPO_NAME}

# ---------------------------------
# Repo-specific targets
# ---------------------------------
.PHONY: install
install:  ## Install package with dev dependencies from GAR
	@if [ -n "$$GOOGLE_APPLICATION_CREDENTIALS" ]; then \
		echo "Using GOOGLE_APPLICATION_CREDENTIALS to authenticate"; \
		pip install --upgrade keyrings.google-artifactregistry-auth; \
		PIP_INDEX_URL="https://us-west1-python.pkg.dev/plainsightai-prod/python/simple/" \
		PIP_EXTRA_INDEX_URL="https://pypi.org/simple" \
		pip install -e .[dev]; \
	else \
		echo "Using gcloud access token"; \
		ACCESS_TOKEN=$$(gcloud auth print-access-token) && \
		PIP_INDEX_URL="https://oauth2accesstoken:$${ACCESS_TOKEN}@us-west1-python.pkg.dev/plainsightai-prod/python/simple/" \
		PIP_EXTRA_INDEX_URL="https://pypi.org/simple" \
		pip install -e .[dev]; \
	fi

.PHONY: run-video
run-video:  ## Run image in docker container
	${CONTAINER_EXEC} compose -f docker-compose.video.yaml up

.PHONY: run-video-dedup
run-video-dedup:  ## Run image in docker container
	${CONTAINER_EXEC} compose -f docker-compose.video-dedup.yaml up

.PHONY: run-rtsp
run-rtsp:  ## Run image in docker container
	${CONTAINER_EXEC} compose -f docker-compose.rtsp.yaml up

.PHONY: run-rtsp-dedup
run-rtsp-dedup:  ## Run image in docker container
	${CONTAINER_EXEC} compose -f docker-compose.rtsp-dedup.yaml up


# ---------------------------------
# Shared makefile include
# ---------------------------------
# Ensure the path matches where `filter.mk` is stored in each repo
include build-include/filter.mk
