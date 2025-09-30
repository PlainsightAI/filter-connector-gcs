#!/usr/bin/env python3
"""
Filter Connector GCS Usage Example

This script demonstrates how to use FilterConnectorGCS in a pipeline:
VideoIn → VideoOut → FilterConnectorGCS → Webvis

Prerequisites:
- Valid GCS credentials (user credentials or service account)
- Sample video file in data/sample_video.mp4
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add the filter module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import OpenFilter components
from openfilter.filter_runtime.filter import Filter
from openfilter.filter_runtime.filters.video_in import VideoIn
from openfilter.filter_runtime.filters.video_out import VideoOut
from openfilter.filter_runtime.filters.webvis import Webvis
from filter_connector_gcs.filter import FilterConnectorGCS

def create_test_image(image_path: str, text: str = "Test Image"):
    """Create a simple test image for demonstration purposes."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import datetime
        
        # Create a simple test image
        img = Image.new('RGB', (400, 200), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Add timestamp and text
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text((10, 10), f"{text} - {timestamp}", fill='black')
        draw.text((10, 40), "This image will be uploaded to GCS", fill='darkblue')
        
        img.save(image_path)
        print(f"Created test image: {image_path}")
        return True
    except ImportError:
        print("PIL not available, skipping test image creation")
        return False
    except Exception as e:
        print(f"Error creating test image: {e}")
        return False

def main():
    """Run the FilterConnectorGCS pipeline with both video and image uploads."""
    
    # Configuration from environment variables
    GCS_BUCKET = os.getenv("GCS_BUCKET", "protege-artifacts-development")
    GCS_PATH = os.getenv("GCS_PATH", "filter-connector-gcs")
    VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "file://./data/sample_video.mp4!loop")
    SEGMENT_DURATION = float(os.getenv("SEGMENT_DURATION", "0.1"))
    IMAGE_DIRECTORY = os.getenv("IMAGE_DIRECTORY", "./results/images")
    
    # Build the pipeline
    pipeline = [
        # VideoIn: Read local video file
        (
            VideoIn,
            {
                "id": "video_in",
                "sources": VIDEO_SOURCE,
                "outputs": "tcp://*:5550",
            },
        ),
        
        # VideoOut: Save local output for debugging
        (
            VideoOut,
            {
                "id": "video_out",
                "sources": "tcp://127.0.0.1:5550",
                "outputs": f"file://./results/output_%Y-%m-%d_%H-%M-%S.mp4!segtime={SEGMENT_DURATION}",
            },
        ),
        
        # FilterConnectorGCS: Upload segments and images to GCS
        (
            FilterConnectorGCS,
            {
                "id": "connector_gcs",
                "sources": "tcp://127.0.0.1:5550",
                "outputs": f"gs://{GCS_BUCKET}/{GCS_PATH}/test_video_%Y-%m-%d_%H-%M-%S.mp4!segtime={SEGMENT_DURATION}",
                "image_directory": IMAGE_DIRECTORY,  # Watch this directory for images to upload
                "mq_log": "pretty",
            },
        ),
        
        # Webvis: Display video stream in browser
        (
            Webvis,
            {
                "id": "webvis",
                "sources": "tcp://localhost:5550",
                "port": 8000
            }
        )
    ]

    # Create image directory if it doesn't exist
    os.makedirs(IMAGE_DIRECTORY, exist_ok=True)
    
    # Create a test image for demonstration
    test_image_path = os.path.join(IMAGE_DIRECTORY, "test_image.jpg")
    create_test_image(test_image_path, "Filter Connector GCS Test")
    
    # Run the pipeline
    print(f"Starting pipeline with GCS bucket: {GCS_BUCKET}")
    print(f"Video source: {VIDEO_SOURCE}")
    print(f"Image directory: {IMAGE_DIRECTORY}")
    print(f"Webvis will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop the pipeline")
    print(f"\nTo test image uploads, copy .jpg/.jpeg/.png files to: {IMAGE_DIRECTORY}")
    print("Images will be uploaded to GCS in the /images subfolder")
    
    Filter.run_multi(pipeline, exit_time=None)

if __name__ == "__main__":
    main()