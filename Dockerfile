FROM us-west1-docker.pkg.dev/plainsightai-prod/oci/filter_base:python-3.11

# Install ffmpeg
RUN apt-get update && \
  apt-get install -y ffmpeg && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*


CMD ["python", "-m", "filter_connector_gcs.filter"]
