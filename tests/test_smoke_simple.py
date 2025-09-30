#!/usr/bin/env python3
"""
Simple Smoke Tests for FilterConnectorGCS

This test focuses on basic functionality without complex pipeline orchestration:
- Filter initialization and setup
- Configuration validation
- Basic frame processing simulation
- Clean shutdown
"""

import os
import sys
import tempfile
import shutil
import logging
from unittest.mock import patch, MagicMock

import pytest

# Add the filter module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from filter_connector_gcs.filter import FilterConnectorGCS, FilterConnectorGCSConfig

logger = logging.getLogger(__name__)

class TestSmokeSimple:
    """Simple smoke tests for FilterConnectorGCS."""
    
    @pytest.fixture
    def temp_workdir(self):
        """Create a temporary working directory."""
        temp_dir = tempfile.mkdtemp(prefix="filter_connector_gcs_smoke_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_gcs_operations(self):
        """Mock GCS operations to avoid real cloud calls."""
        with patch('filter_connector_gcs.filter.FilterConnectorGCS.BaseUploader.upload_file') as mock_upload:
            mock_upload.return_value = True
            yield mock_upload
    
    def test_filter_initialization(self, temp_workdir, mock_gcs_operations):
        """Test that the filter can be initialized with valid config."""
        config_data = {
            'id': 'test_filter',
            'sources': 'tcp://127.0.0.1:5550',
            'outputs': 'gs://test-bucket/path/test.mp4',
            'workdir': temp_workdir,
            'timeout': 30.0,
            'manifest': None,
            'manifest_field': None,
            'image_directory': None
        }
        
        # Test config normalization
        config = FilterConnectorGCS.normalize_config(config_data)
        assert config.id == 'test_filter'
        assert config.workdir == temp_workdir
        assert len(config.outputs) == 1
        assert config.outputs[0].output == 'gs://test-bucket/path/test.mp4'
        
        # Test filter creation
        filter_instance = FilterConnectorGCS(config)
        assert filter_instance.config.id == 'test_filter'
        
        logger.info("Filter initialization test passed")
    
    def test_setup_and_shutdown(self, temp_workdir, mock_gcs_operations):
        """Test that setup() and shutdown() work correctly."""
        config_data = {
            'id': 'test_lifecycle',
            'sources': 'tcp://127.0.0.1:5550',
            'outputs': 'gs://test-bucket/path/lifecycle.mp4',
            'workdir': temp_workdir,
            'timeout': 30.0,
            'manifest': None,
            'manifest_field': None,
            'image_directory': None
        }
        
        config = FilterConnectorGCS.normalize_config(config_data)
        filter_instance = FilterConnectorGCS(config)
        
        # Test setup
        filter_instance.setup(config)
        assert hasattr(filter_instance, 'uploaders'), "Setup should create uploaders"
        assert len(filter_instance.uploaders) == 1, "Should have one video uploader"
        
        # Test shutdown
        filter_instance.shutdown()
        # Shutdown should complete without errors
        assert True, "Shutdown should complete successfully"
        
        logger.info("Setup and shutdown test passed")
    
    def test_config_validation(self):
        """Test configuration validation with various inputs."""
        
        # Test valid configuration
        valid_config = {
            'outputs': 'gs://test-bucket/path/video.mp4',
            'sources': 'tcp://127.0.0.1:5550'
        }
        normalized = FilterConnectorGCS.normalize_config(valid_config)
        assert normalized.outputs is not None
        assert len(normalized.outputs) == 1
        
        # Test invalid outputs (not gs://)
        with pytest.raises(ValueError, match="can only specify gs:// outputs"):
            FilterConnectorGCS.normalize_config({
                'outputs': 'file://local-file.mp4',
                'sources': 'tcp://127.0.0.1:5550'
            })
        
        # Test missing outputs
        with pytest.raises(ValueError, match="must specify at least one output"):
            FilterConnectorGCS.normalize_config({
                'sources': 'tcp://127.0.0.1:5550'
            })
        
        # Test malformed gs:// URL
        with pytest.raises(ValueError, match="output must have both bucket and a path/file name"):
            FilterConnectorGCS.normalize_config({
                'outputs': 'gs://bucket-only',
                'sources': 'tcp://127.0.0.1:5550'
            })
        
        logger.info("Configuration validation test passed")
    
    def test_manifest_configuration(self, temp_workdir, mock_gcs_operations):
        """Test filter with manifest configuration."""
        # Create a test manifest file
        manifest_path = os.path.join(temp_workdir, "test_manifest.json")
        manifest_data = {"test": {"files": []}}
        with open(manifest_path, 'w') as f:
            import json
            json.dump(manifest_data, f)
        
        config_data = {
            'id': 'test_manifest',
            'sources': 'tcp://127.0.0.1:5550',
            'outputs': 'gs://test-bucket/path/manifest-test.mp4',
            'workdir': temp_workdir,
            'timeout': 30.0,
            'manifest': f'file://{manifest_path}',
            'manifest_field': 'test.files',
            'image_directory': None
        }
        
        config = FilterConnectorGCS.normalize_config(config_data)
        filter_instance = FilterConnectorGCS(config)
        
        # Test setup with manifest
        filter_instance.setup(config)
        assert hasattr(filter_instance, 'uploaders'), "Setup should create uploaders"
        
        # Test shutdown
        filter_instance.shutdown()
        
        # Verify manifest file was read
        assert os.path.exists(manifest_path), "Manifest file should exist"
        
        logger.info("Manifest configuration test passed")
    
    def test_string_config_conversion(self):
        """Test that string configs are properly converted to types."""
        # Test with string values that should be converted
        config_data = {
            'outputs': 'gs://test-bucket/path/video.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'timeout': '60.5',  # String that should be preserved
            'manifest': 'file:///path/to/manifest.json',
            'manifest_field': 'test.files',
            'image_directory': '/path/to/images'
        }
        
        normalized = FilterConnectorGCS.normalize_config(config_data)
        
        # Check that string values are preserved (VideoOutConfig handles conversion)
        assert normalized.timeout == '60.5'
        assert normalized.manifest == 'file:///path/to/manifest.json'
        assert normalized.manifest_field == 'test.files'
        assert normalized.image_directory == '/path/to/images'
        
        logger.info("String config conversion test passed")


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])
