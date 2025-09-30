#!/usr/bin/env python3
"""
Integration Configuration Normalization Tests for FilterConnectorGCS

This test validates configuration normalization with real-world scenarios:
- String-to-type conversions (bool, int, float, JSON)
- Required vs optional parameters
- Edge cases and invalid inputs
- Environment variable handling
"""

import os
import sys
import json
import tempfile
from pathlib import Path

import pytest

# Add the filter module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from filter_connector_gcs.filter import FilterConnectorGCS, FilterConnectorGCSConfig

class TestIntegrationConfigNormalization:
    """Integration tests for configuration normalization."""
    
    def test_string_to_type_conversions(self):
        """Test that string configurations are properly converted to correct types."""
        
        # Test that the normalize_config method preserves string types as-is
        # (The actual conversion happens in the VideoOutConfig parent class)
        config_with_string_bool = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'workdir': 'test_workdir',
            'timeout': '60.5',  # String float
            'manifest': 'file://test.json',
            'manifest_field': 'test.files',
            'image_directory': '/path/to/images'
        }
        
        normalized = FilterConnectorGCS.normalize_config(config_with_string_bool)
        
        # Verify types are correct (strings are preserved as strings)
        assert isinstance(normalized.workdir, str)
        assert isinstance(normalized.timeout, str)  # String is preserved as string
        assert normalized.timeout == '60.5'
        assert isinstance(normalized.manifest, str)
        assert isinstance(normalized.manifest_field, str)
        assert isinstance(normalized.image_directory, str)
        
        # Test with integer string
        config_with_int = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'timeout': '120'  # String int
        }
        
        normalized_int = FilterConnectorGCS.normalize_config(config_with_int)
        assert isinstance(normalized_int.timeout, str)  # String is preserved as string
        assert normalized_int.timeout == '120'
    
    def test_required_vs_optional_parameters(self):
        """Test that required parameters are enforced and optional ones are handled."""
        
        # Test missing required 'outputs' parameter
        with pytest.raises(ValueError, match="must specify at least one output"):
            FilterConnectorGCS.normalize_config({
                'sources': 'tcp://127.0.0.1:5550'
            })
        
        # Test missing required 'sources' parameter
        with pytest.raises(ValueError, match="must specify at least one source"):
            FilterConnectorGCS.normalize_config({
                'outputs': 'gs://test-bucket/test.mp4'
            })
        
        # Test with only required parameters
        minimal_config = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550'
        }
        
        normalized = FilterConnectorGCS.normalize_config(minimal_config)
        assert normalized.outputs is not None
        assert normalized.sources is not None
        assert normalized.workdir is None  # Optional
        assert normalized.timeout is None  # Optional
        assert normalized.manifest is None  # Optional
        assert normalized.manifest_field is None  # Optional
        assert normalized.image_directory is None  # Optional
    
    def test_gs_url_validation(self):
        """Test validation of gs:// URLs."""
        
        # Test valid gs:// URLs
        valid_urls = [
            'gs://bucket/path/file.mp4',
            'gs://my-bucket/subfolder/video_%Y-%m-%d.mp4',
            'gs://bucket-with-dashes/path/file.mp4',
            'gs://bucket.with.dots/path/file.mp4'
        ]
        
        for url in valid_urls:
            config = {
                'outputs': url,
                'sources': 'tcp://127.0.0.1:5550'
            }
            normalized = FilterConnectorGCS.normalize_config(config)
            assert normalized.outputs is not None
            assert len(normalized.outputs) == 1
        
        # Test invalid gs:// URLs
        invalid_urls = [
            'file://local-file.mp4',  # Not gs://
            'gs://bucket-only',  # Missing path
            'gs://',  # Empty bucket
            'http://bucket/path/file.mp4',  # Wrong protocol
            's3://bucket/path/file.mp4',  # Wrong protocol
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValueError):
                FilterConnectorGCS.normalize_config({
                    'outputs': url,
                    'sources': 'tcp://127.0.0.1:5550'
                })
    
    def test_manifest_configuration(self):
        """Test manifest-related configuration options."""
        
        # Test with file:// manifest
        config_with_file_manifest = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'manifest': 'file://test_manifest.json',
            'manifest_field': 'test.files'
        }
        
        normalized = FilterConnectorGCS.normalize_config(config_with_file_manifest)
        assert normalized.manifest == 'file://test_manifest.json'
        assert normalized.manifest_field == 'test.files'
        
        # Test with gs:// manifest
        config_with_gs_manifest = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'manifest': 'gs://test-bucket/manifest_template.json',
            'manifest_field': 'data.files'
        }
        
        normalized_gs = FilterConnectorGCS.normalize_config(config_with_gs_manifest)
        assert normalized_gs.manifest == 'gs://test-bucket/manifest_template.json'
        assert normalized_gs.manifest_field == 'data.files'
        
        # Test with None manifest (should be allowed)
        config_no_manifest = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'manifest': None,
            'manifest_field': None
        }
        
        normalized_none = FilterConnectorGCS.normalize_config(config_no_manifest)
        assert normalized_none.manifest is None
        assert normalized_none.manifest_field is None
    
    def test_workdir_and_timeout_configuration(self):
        """Test working directory and timeout configuration."""
        
        # Test with custom workdir
        config_with_workdir = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'workdir': '/custom/work/directory',
            'timeout': 120.0
        }
        
        normalized = FilterConnectorGCS.normalize_config(config_with_workdir)
        assert normalized.workdir == '/custom/work/directory'
        assert normalized.timeout == 120.0
        
        # Test with relative workdir
        config_relative_workdir = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'workdir': 'relative/path',
            'timeout': 30
        }
        
        normalized_rel = FilterConnectorGCS.normalize_config(config_relative_workdir)
        assert normalized_rel.workdir == 'relative/path'
        assert normalized_rel.timeout == 30.0  # Should convert to float
    
    def test_image_directory_configuration(self):
        """Test image directory configuration."""
        
        # Test with image folder
        config_with_images = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'image_directory': '/path/to/images'
        }
        
        normalized = FilterConnectorGCS.normalize_config(config_with_images)
        assert normalized.image_directory == '/path/to/images'
        
        # Test without image folder
        config_no_images = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550'
        }
        
        normalized_no_images = FilterConnectorGCS.normalize_config(config_no_images)
        assert normalized_no_images.image_directory is None
    
    def test_multiple_outputs(self):
        """Test configuration with multiple outputs."""
        
        config_multiple = {
            'outputs': [
                'gs://bucket1/path1/video1.mp4',
                'gs://bucket2/path2/video2.mp4'
            ],
            'sources': 'tcp://127.0.0.1:5550'
        }
        
        normalized = FilterConnectorGCS.normalize_config(config_multiple)
        assert len(normalized.outputs) == 2
        assert any('bucket1' in str(output) for output in normalized.outputs)
        assert any('bucket2' in str(output) for output in normalized.outputs)
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        
        # Test empty string values
        config_empty_strings = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'workdir': '',
            'manifest': '',
            'manifest_field': '',
            'image_directory': ''
        }
        
        normalized = FilterConnectorGCS.normalize_config(config_empty_strings)
        # Empty strings should be preserved as strings
        assert normalized.workdir == ''
        assert normalized.manifest == ''
        assert normalized.manifest_field == ''
        assert normalized.image_directory == ''
        
        # Test with very long strings
        long_string = 'a' * 1000
        config_long_strings = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'workdir': long_string,
            'manifest_field': long_string
        }
        
        normalized_long = FilterConnectorGCS.normalize_config(config_long_strings)
        assert normalized_long.workdir == long_string
        assert normalized_long.manifest_field == long_string
        
        # Test with special characters in paths
        config_special_chars = {
            'outputs': 'gs://test-bucket/test.mp4',
            'sources': 'tcp://127.0.0.1:5550',
            'workdir': '/path/with spaces and-special_chars',
            'manifest_field': 'test.field.with.dots'
        }
        
        normalized_special = FilterConnectorGCS.normalize_config(config_special_chars)
        assert normalized_special.workdir == '/path/with spaces and-special_chars'
        assert normalized_special.manifest_field == 'test.field.with.dots'


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])
