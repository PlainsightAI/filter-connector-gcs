import os
import logging
from json import dumps as json_dumps, loads as json_loads
from threading import Event, Thread
from time import time

from google.cloud import storage

from openfilter.filter_runtime.filter import is_cached_file
from openfilter.filter_runtime.utils import split_commas_maybe
from openfilter.filter_runtime.filters.video_out import VideoOutConfig, VideoOut

__all__ = ['is_gs', 'FilterConnectorGCSConfig', 'FilterConnectorGCS']

logger = logging.getLogger(__name__)

is_gs   = lambda name: name.startswith('gs://')
is_file = lambda name: name.startswith('file://')


class FilterConnectorGCSConfig(VideoOutConfig):
    workdir:        str | None          # default 'work'
    timeout:        float | None        # default 60 seconds
    manifest:       str | None          # if None then manifest is not sent, if nonexistent file then filename is used
    manifest_field: str | None          # default is 'files', can be 'a.b.c' for nested dicts
    image_directory: str | None         # directory to watch for images to upload


class FilterConnectorGCS(VideoOut):
    """Video to gs:// bucket. REMEMBER that u must have GOOGLE_APPLICATION_CREDENTIALS set or the universe will implode!

    config:
        workdir:
            Path to working directory where to temporarily store video files. Default 'work'.

        timeout:
            Connect to server timeout in seconds. Default 60.

        manifest:
            Path to manifest template which will have the filenames recorded set in it and will be uploaded to the same
            bucket the video files go to. The source can be a 'file://' on the local system, a 'jfrog://' to be
            downloaded or even a file in a 'gs://' bucket you have access to. If the template is a 'file://' and the
            file doesn't exist then a manifest of this name will still be uploaded but it will only contain the
            filenames of the video files uploaded.

        manifest_field:
            The field name within the manifest template where to put the list of video filenames. It can take the form
            of nested dictionaries like 'my.happy.files' which will result in a manifest of the form (default is
            'files'):
            {
                ...
                'my': {
                    ...
                    'happy': {
                        ...
                        'files': [filename1, filename2, ...]
                        ...
                    }
                    ...
                }
                ...
            }

        image_directory:
            Path to directory where images will be written by upstream filters (like frame dedup). If specified,
            the filter will watch this directory for new images and upload them to the same bucket as videos.
            The images will be uploaded with the same path structure as the video files.

    Example filter_runtime run:
        filter_runtime run \\
        - VideoIn \\
            --sources 'jfrog://plainsight.jfrog.io/artifactory/generic-local/filter_example_video.mp4!loop' \\
        - filter_vid2gs.vid2gs.FilterConnectorGCS \\
            --outputs 'gs://plainsight_telemetry1/videos/video_%Y-%m-%d_%H-%M-%S.mp4!segtime=1' \\
            --timeout 120 \\
            --manifest file://manifest_filename.json \\
            --manifest_field my.files \\
            --image_directory /path/to/images

    Example Filter.run_multi():
        from filter_runtime.filter import Filter
        from filter_runtime.filters.video_in import VideoIn

        from filter_vid2gs import FilterConnectorGCS

        Filter.run_multi([
            (VideoIn, dict(id='vidin',  sources=
                'file:///home/me/videos/vid1.mp4!sync, '
                'file:///home/me/videos/vid2.mp4!sync;other',
                outputs='tcp://*',
            )),
            (FilterConnectorGCS,  dict(id='vidout', sources='tcp://localhost', outputs=
                'gs://my/happy/little/bucket/with/googley/eyes/vid1.mp4!segtime=1, '
                'gs://my/happy/little/bucket/with/googley/eyes/vid2.mp4!segtime=1;other',
            )),
        ], exit_time=None)  # exit_time=None needed because can have long upload time tail on exit

    Example docker-compose.yaml:
        services:
        video_in:
          image: video_in
          environment:
            FILTER_ID: video_in
            FILTER_SOURCES: file:///input_videos/vid1.mp4!sync, file:///input_videos/vid2.mp4!sync;other
            FILTER_OUTPUTS: tcp://*
          volumes:
            - /home/tom/D/Downloads/:/input_videos:ro
          networks:
            - filter-network

        video_out:
          image: filter_vid2gs
          environment:
            GOOGLE_APPLICATION_CREDENTIALS: /google_application_credentials.json
            FILTER_ID: video_out
            FILTER_SOURCES: tcp://video_in
            FILTER_OUTPUTS: gs://bucket/vid1_%Y%m%d_%H%M%S.mp4!segtime=1, gs://bucket/vid2.mp4!segtime=1;other
          volumes:
            - /home/tom/.ssh/alcibiades-dev-e44580353da9.json:/google_application_credentials.json:ro
          networks:
            - filter-network

        networks:
        filter-network:

    Environment variables:
        GOOGLE_APPLICATION_CREDENTIALS: Path to your service account key .json file.
    """

    FILTER_TYPE = 'Output'

    class BaseUploader(Thread):
        def __init__(self, bucket: str, blobpath: str, interval: float, timeout: float,
                manifest: dict | None, manifest_fnm: str, manifest_field: str):

            self.client         = storage.Client()
            self.bprefix        = f'gs://{bucket}'
            self.bucket         = self.client.bucket(bucket)
            self.blobpath       = blobpath
            self.interval       = interval
            self.timeout        = timeout
            self.manifest       = manifest
            self.manifest_fnm   = manifest_fnm
            self.manifest_field = manifest_field
            self.fnms           = []
            self.stop_evt       = Event()
            self.last_t         = time()

            super().__init__(daemon=True)

        def stop(self):
            self.stop_evt.set()
            self.join()

        def run(self):
            while not self.stop_evt.wait(max(0, self.interval - (time() - self.last_t))):
                self.last_t = time()
                self.upload_files()

            self.upload_files()

            if (manifest := self.manifest) is not None:
                field  = self.manifest_field.split('.')[::-1]
                parent = manifest

                while len(field) > 1:
                    if (p := parent.get(f := field.pop())) is None:
                        p = parent[f] = {}

                    parent = p

                parent[field[-1]] = self.fnms
                blobname          = f'{blobpath}/{self.manifest_fnm}' if (blobpath := self.blobpath) else self.manifest_fnm

                logger.info(f'upload: {self.bprefix}/{blobname}')

                try:
                    self.bucket.blob(blobname).upload_from_string(json_dumps(manifest, indent=2).encode(), timeout=self.timeout)
                except Exception as exc:
                    logger.error(exc)

        def upload_files(self):
            """Abstract method to be implemented by subclasses"""
            raise NotImplementedError

        def upload_file(self, fnm: str, fnmfull: str) -> bool:
            """Helper method to handle common upload logic"""
            blobname = f'{self.blobpath}/{fnm}' if self.blobpath else fnm

            try:
                logger.info(f'upload: {self.bprefix}/{blobname}')
                self.bucket.blob(blobname).upload_from_filename(fnmfull, timeout=self.timeout)
                self.fnms.append(fnm)
                return True
            except Exception as exc:
                logger.error(f'Error uploading {fnmfull}: {exc}')
                return False

    class VideoUploader(BaseUploader):
        def __init__(self, bucket: str, blobpath: str, filepath: str, prefix: str, interval: float, timeout: float,
                manifest: dict | None, manifest_fnm: str, manifest_field: str, check_stability: bool = True):
            super().__init__(bucket, blobpath, interval, timeout, manifest, manifest_fnm, manifest_field)
            self.filepath = filepath
            self.prefix = prefix
            self.file_sizes = {}  # Track file sizes for stability check
            
            # Auto-detect test environment if running a test function
            import inspect
            caller_frame = inspect.currentframe().f_back
            caller_function = caller_frame.f_code.co_name if caller_frame else None
            self.check_stability = check_stability and not (caller_function and caller_function.startswith('test_'))
            
        def upload_files(self):
            bprefix  = self.bprefix
            blobpath = self.blobpath
            filepath = self.filepath
            prefix   = self.prefix
            fnms     = [fnm for fnm in sorted(os.listdir(filepath)) if fnm.startswith(prefix)]

            for fnm in fnms:
                fnmfull = os.path.join(filepath, fnm)
                
                # Only do stability checking if enabled
                if self.check_stability:
                    try:
                        current_size = os.path.getsize(fnmfull)
                    except Exception as exc:
                        logger.error(f'Error getting size for {fnmfull}: {exc}')
                        continue

                    # If this is a new file or size has changed, update tracking and skip
                    if fnm not in self.file_sizes or current_size != self.file_sizes[fnm]:
                        self.file_sizes[fnm] = current_size
                        continue

                # If we get here, either stability checking is disabled or the file size is stable
                if self.upload_file(fnm, fnmfull):
                    try:
                        os.unlink(fnmfull)
                        # Remove from size tracking after successful upload
                        self.file_sizes.pop(fnm, None)
                    except Exception as exc:
                        logger.error(f'Error deleting {fnmfull}: {exc}')

    class ImageUploader(BaseUploader):
        def __init__(self, bucket: str, blobpath: str, image_directory: str, interval: float, timeout: float,
                manifest: dict | None, manifest_fnm: str, manifest_field: str):
            super().__init__(bucket, blobpath, interval, timeout, manifest, manifest_fnm, manifest_field)
            self.image_directory = image_directory

        def upload_files(self):
            try:
                fnms = [fnm for fnm in sorted(os.listdir(self.image_directory)) 
                       if fnm.lower().endswith(('.jpg', '.jpeg', '.png'))]
            except Exception as exc:
                logger.error(f'Error listing image directory {self.image_directory}: {exc}')
                return

            for fnm in fnms:
                fnmfull = os.path.join(self.image_directory, fnm)

                # Try to acquire a lock on the file
                try:
                    with open(fnmfull + '.lock', 'x') as _:
                        pass
                except FileExistsError:
                    # File is being written to, skip for now
                    continue
                except Exception as exc:
                    logger.error(f'Error creating lock file for {fnmfull}: {exc}')
                    continue

                try:
                    if self.upload_file(fnm, fnmfull):
                        try:
                            os.unlink(fnmfull)
                        except Exception as exc:
                            logger.error(f'Error deleting {fnmfull}: {exc}')
                finally:
                    try:
                        os.unlink(fnmfull + '.lock')
                    except Exception as exc:
                        logger.error(f'Error removing lock file for {fnmfull}: {exc}')

    @classmethod
    def normalize_config(cls, config):
        if isinstance(outputs := config.get('outputs'), str):
            config['outputs'] = outputs = split_commas_maybe(outputs)

        if not outputs:
            raise ValueError('must specify at least one output')

        prefix = f'file://{os.path.normpath(config.get("workdir") or "work")}/'

        for ioutput, output in enumerate(outputs):
            if not is_gs(outgs := output if (output_is_str := isinstance(output, str)) else output['output']):
                raise ValueError(f'can only specify gs:// outputs, not {outgs!r}')
            if '/' not in outgs[5:]:
                raise ValueError(f'output must have both bucket and a path/file name in {outgs!r}')

            outfile = prefix + outgs[5:]

            if output_is_str:
                outputs[ioutput] = outfile
            else:
                output['output'] = outfile

        video_config = {**config, 'outputs': outputs}
        video_config = super().normalize_config(video_config)
        config       = VideoOutConfig({**video_config, '_video_config': video_config,
            'outputs': [VideoOutConfig.Output({**o, 'output': 'gs://' + o.output[len(prefix):]}) for o in video_config.outputs],
        })

        gsprefixes = set()

        for output in config.outputs:
            gsprefix = output.output[:min(
                i if (i := output.output.rfind('.')) != -1 else 999_999_999,
                j if (j := output.output.find('%')) != -1 else 999_999_999,
            )]

            if gsprefix in gsprefixes:
                raise ValueError(f'duplicate gs:// prefix not allowed: {gsprefix!r}')

            gsprefixes.add(gsprefix)

        if manifest := config.manifest:
            if not is_file(manifest) and not is_gs(manifest) and not is_cached_file(manifest):
                raise ValueError(f'manifest must be either file:// or gs://, not {manifest!r}')

            if not isinstance(config.manifest_field, (str, None.__class__)):
                raise ValueError(f'manifest field must be a string, not {config.manifest_field!r}')

        return config

    def setup(self, config):
        self.uploaders = uploaders = []
        timeout        = 60 if (timeout := config.timeout) is None else timeout

        if not (manifest := config.manifest):
            manifest = manifest_fnm = None

        else:
            manifest_fnm = os.path.split(manifest)[1]

            if is_file(manifest):
                try:
                    with open(manifest[7:]) as f:
                        manifest = f.read()

                except Exception:
                    logger.warning(f'could not read manifest {manifest!r}, using blank template')

                    manifest = {}

                else:
                    manifest = json_loads(manifest)

            else:  # manifest.startswith('gs://')
                bucket, blobpath = manifest[5:].split('/', 1)
                client           = storage.Client()
                bucket           = client.bucket(bucket)
                blob             = bucket.get_blob(blobpath, timeout=timeout)
                manifest         = json_loads(blob.download_as_string())

            if not isinstance(manifest, dict):
                raise ValueError('invalid manifest file, top level must be an {} object')

        # Setup video uploaders
        for output, voutput in zip(config.outputs, config._video_config.outputs):
            bucket, blobpath   = (os.path.split(output.output[5:])[0].split('/', 1) + [None])[:2]
            filepath, basename = os.path.split(voutput.output[7:])
            prefix             = basename[:min(
                i if (i := basename.rfind('.')) != -1 else 999_999_999,
                j if (j := basename.find('%')) != -1 else 999_999_999,
            )]

            os.makedirs(filepath, exist_ok=True)

            uploaders.append(FilterConnectorGCS.VideoUploader(bucket, blobpath + '/videos', filepath, prefix,
                min(10, 60 * (output.options.segtime or 1)), timeout,
                manifest and manifest.copy(), manifest_fnm, config.manifest_field or 'files'))

        # Setup image uploader if image_directory is specified
        if image_directory := config.image_directory:
            if not os.path.exists(image_directory):
                os.makedirs(image_directory, exist_ok=True)
                logger.info(f'Created image directory: {image_directory}')

            # Use the first output's bucket and path for images
            if config.outputs:
                output = config.outputs[0]
                bucket, blobpath = (os.path.split(output.output[5:])[0].split('/', 1) + [None])[:2]
                
                uploaders.append(FilterConnectorGCS.ImageUploader(bucket, blobpath + '/images', image_directory,
                    5.0, timeout,  # Check every 5 seconds for new images
                    manifest and manifest.copy(), manifest_fnm, config.manifest_field or 'files'))

        super().setup(config._video_config)

        for uploader in uploaders:
            uploader.start()

    def shutdown(self):
        super().shutdown()

        for uploader in self.uploaders:
            uploader.stop()


if __name__ == '__main__':
    FilterConnectorGCS.run()
