import os
import pytest
from unittest.mock import patch, MagicMock, call
from filter_connector_gcs.filter import is_gs, FilterConnectorGCSConfig, FilterConnectorGCS


@pytest.fixture
def mock_storage_client():
    """
    Pytest fixture that mocks out `google.cloud.storage.Client`.
    Returns a mock for the `Client`, the `Bucket`, and the `Blob`.
    """
    with patch('filter_connector_gcs.filter.storage.Client', autospec=True) as mock_client_cls:
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.get_blob.return_value = mock_blob
        mock_bucket.blob.return_value = mock_blob
        mock_client_cls.return_value = mock_client

        yield mock_client, mock_bucket, mock_blob


def test_is_gs():
    """
    Simple sanity check for the is_gs lambda.
    """
    assert is_gs('gs://my-bucket'), "Should return True for gs://"
    assert not is_gs('file://my-file'), "Should return False for file://"


def test_vid2gs_config_defaults():
    """
    Test constructing a Vid2GSConfig with default values.
    """
    config = FilterConnectorGCSConfig()
    assert config.workdir is None
    assert config.timeout is None
    assert config.manifest is None
    assert config.manifest_field is None
    assert config.image_directory is None


def test_vid2gs_config_explicit():
    """
    Test constructing a Vid2GSConfig with explicit values.
    """
    config = FilterConnectorGCSConfig(
        workdir='my_workdir',
        timeout=120,
        manifest='file://my_manifest.json',
        manifest_field='my.custom.files',
        image_directory='/path/to/images'
    )
    assert config.workdir == 'my_workdir'
    assert config.timeout == 120
    assert config.manifest == 'file://my_manifest.json'
    assert config.manifest_field == 'my.custom.files'
    assert config.image_directory == '/path/to/images'


def test_vid2gs_normalize_config_no_outputs():
    """
    Ensure Vid2GS.normalize_config raises ValueError if 'outputs' is missing or empty.
    """
    with pytest.raises(ValueError, match='must specify at least one output'):
        FilterConnectorGCS.normalize_config({})  # no 'outputs' key


def test_vid2gs_normalize_config_not_gs():
    """
    Ensure Vid2GS.normalize_config raises ValueError if any output is not gs://
    """
    with pytest.raises(ValueError, match='can only specify gs:// outputs'):
        FilterConnectorGCS.normalize_config({'outputs': ['file://localfile']})

    with pytest.raises(ValueError, match='output must have both bucket and a path/file name'):
        FilterConnectorGCS.normalize_config({'outputs': ['gs://my-bucket']})  # no slash after bucket


def test_vid2gs_normalize_config_good():
    """
    Test a happy path where the config has valid gs:// outputs.
    """
    config_in = {
        'outputs': [
            'gs://my-bucket/path/video_%Y-%m-%d.mp4'
        ],
        'sources': [
            'some-dummy-source'
        ],
        'workdir': 'some_work',
        'timeout': 60,
        'manifest': 'file://my_manifest.json',
        'manifest_field': 'my.files',
        'image_directory': '/path/to/images'
    }

    config_out = FilterConnectorGCS.normalize_config(config_in)
    assert config_out.outputs, "Outputs should not be empty after normalization"
    assert any(o.output.startswith('gs://') for o in config_out.outputs), \
        "Should still store the original gs:// prefix for each output"
    assert config_out.image_directory == '/path/to/images'


def test_vid2gs_setup(mock_storage_client, tmp_path):
    """
    Test Vid2GS.setup with valid configuration for video uploads only.
    """
    mock_client, mock_bucket, mock_blob = mock_storage_client

    # Minimal valid config that includes one gs:// output
    config_data = {
        'id': 'vid2gs_test',
        'outputs': [
            'gs://my-bucket/path/video_123.mp4'
        ],
        'sources': [
            'some-dummy-source'
        ],
        'workdir': 'workdir_test',
        'timeout': 60,
        'manifest': None,
        'manifest_field': None
    }

    config = FilterConnectorGCS.normalize_config(config_data)
    vid2gs_instance = FilterConnectorGCS(config)
    vid2gs_instance.setup(config)

    # Should have one video uploader
    assert len(vid2gs_instance.uploaders) == 1
    uploader = vid2gs_instance.uploaders[0]
    assert isinstance(uploader, FilterConnectorGCS.VideoUploader)
    assert uploader.bucket == mock_bucket
    assert uploader.manifest is None
    assert uploader.prefix == 'video_123'


def test_vid2gs_setup_with_images(mock_storage_client, tmp_path):
    """
    Test Vid2GS.setup with image folder configuration.
    """
    mock_client, mock_bucket, mock_blob = mock_storage_client

    config_data = {
        'id': 'vid2gs_test',
        'outputs': [
            'gs://my-bucket/path/video_123.mp4'
        ],
        'sources': [
            'some-dummy-source'
        ],
        'workdir': 'workdir_test',
        'timeout': 60,
        'manifest': None,
        'manifest_field': None,
        'image_directory': str(tmp_path / 'images')
    }

    config = FilterConnectorGCS.normalize_config(config_data)
    vid2gs_instance = FilterConnectorGCS(config)
    vid2gs_instance.setup(config)

    # Should have two uploaders (video and image)
    assert len(vid2gs_instance.uploaders) == 2
    video_uploader = vid2gs_instance.uploaders[0]
    image_uploader = vid2gs_instance.uploaders[1]

    assert isinstance(video_uploader, FilterConnectorGCS.VideoUploader)
    assert isinstance(image_uploader, FilterConnectorGCS.ImageUploader)
    assert image_uploader.image_directory == str(tmp_path / 'images')


@pytest.mark.parametrize("files,expected_uploads", [
    (["video_123_0001.mp4", "video_123_0002.mp4"], 2),
    ([], 0),
])
def test_video_uploader_upload_files(files, expected_uploads, mock_storage_client, tmp_path):
    """
    Test the VideoUploader.upload_files() method.
    """
    mock_client, mock_bucket, mock_blob = mock_storage_client

    # Create files in a temporary directory
    for fname in files:
        (tmp_path / fname).write_text("dummy video data")

    uploader = FilterConnectorGCS.VideoUploader(
        bucket="my-bucket",
        blobpath="path",
        filepath=str(tmp_path),
        prefix="video_123",
        interval=5.0,
        timeout=60.0,
        manifest=None,
        manifest_fnm="some_manifest.json",
        manifest_field="files"
    )

    uploader.upload_files()

    assert mock_blob.upload_from_filename.call_count == expected_uploads

    for fname in files:
        was_deleted = not (tmp_path / fname).exists()
        if "video_123" in fname:
            assert was_deleted, f"Expected {fname} to be unlinked"
        else:
            assert not was_deleted, f"Didn't expect {fname} to be unlinked"


@pytest.mark.parametrize("files,expected_uploads", [
    (["image1.jpg", "image2.png"], 2),
    ([], 0),
])
def test_image_uploader_upload_files(files, expected_uploads, mock_storage_client, tmp_path):
    """
    Test the ImageUploader.upload_files() method with file locking.
    """
    mock_client, mock_bucket, mock_blob = mock_storage_client

    # Create image files in a temporary directory
    for fname in files:
        (tmp_path / fname).write_text("dummy image data")

    uploader = FilterConnectorGCS.ImageUploader(
        bucket="my-bucket",
        blobpath="path",
        image_directory=str(tmp_path),
        interval=5.0,
        timeout=60.0,
        manifest=None,
        manifest_fnm="some_manifest.json",
        manifest_field="files"
    )

    uploader.upload_files()

    assert mock_blob.upload_from_filename.call_count == expected_uploads

    for fname in files:
        was_deleted = not (tmp_path / fname).exists()
        assert was_deleted, f"Expected {fname} to be unlinked"
        # Ensure lock files were cleaned up
        assert not (tmp_path / f"{fname}.lock").exists()


def test_image_uploader_locked_files(mock_storage_client, tmp_path):
    """
    Test that ImageUploader skips files that are locked.
    """
    mock_client, mock_bucket, mock_blob = mock_storage_client

    # Create an image file and its lock file
    image_file = tmp_path / "test.jpg"
    lock_file = tmp_path / "test.jpg.lock"
    image_file.write_text("dummy image data")
    lock_file.write_text("")

    uploader = FilterConnectorGCS.ImageUploader(
        bucket="my-bucket",
        blobpath="path",
        image_directory=str(tmp_path),
        interval=5.0,
        timeout=60.0,
        manifest=None,
        manifest_fnm="some_manifest.json",
        manifest_field="files"
    )

    uploader.upload_files()

    # Should not have attempted to upload the locked file
    assert mock_blob.upload_from_filename.call_count == 0
    assert image_file.exists(), "Locked file should not be deleted"


def test_uploader_manifest_upload(mock_storage_client, tmp_path):
    """
    Test manifest upload functionality for both uploader types.
    """
    mock_client, mock_bucket, mock_blob = mock_storage_client

    manifest_data = {"some": {"nested": {"structure": 123}}}
    
    # Test with VideoUploader
    video_uploader = FilterConnectorGCS.VideoUploader(
        bucket="my-bucket",
        blobpath="my/path",
        filepath=str(tmp_path),
        prefix="video_",
        interval=1.0,
        timeout=30.0,
        manifest=manifest_data.copy(),
        manifest_fnm="manifest.json",
        manifest_field="some.nested.files"
    )
    video_uploader.fnms = ["video_1.mp4", "video_2.mp4"]
    video_uploader.stop_evt.set()
    video_uploader.run()

    # Test with ImageUploader
    image_uploader = FilterConnectorGCS.ImageUploader(
        bucket="my-bucket",
        blobpath="my/path",
        image_directory=str(tmp_path),
        interval=1.0,
        timeout=30.0,
        manifest=manifest_data.copy(),
        manifest_fnm="manifest.json",
        manifest_field="some.nested.files"
    )
    image_uploader.fnms = ["image1.jpg", "image2.png"]
    image_uploader.stop_evt.set()
    image_uploader.run()

    # Check that manifest was uploaded twice (once for each uploader)
    assert mock_blob.upload_from_string.call_count == 2

    # Verify the manifest content for video uploader
    args, _ = mock_blob.upload_from_string.call_args_list[0]
    uploaded_bytes = args[0]
    expected_manifest = {
        "some": {
            "nested": {
                "structure": 123,
                "files": ["video_1.mp4", "video_2.mp4"]
            }
        }
    }
    assert expected_manifest == eval(uploaded_bytes.decode('utf-8'))

    # Verify the manifest content for image uploader
    args, _ = mock_blob.upload_from_string.call_args_list[1]
    uploaded_bytes = args[0]
    expected_manifest = {
        "some": {
            "nested": {
                "structure": 123,
                "files": ["image1.jpg", "image2.png"]
            }
        }
    }
    assert expected_manifest == eval(uploaded_bytes.decode('utf-8'))
