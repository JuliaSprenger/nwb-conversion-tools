import json
from dateutil.parser import parse as dateparse
from typing import Optional

try:
    from PIL import Image, ExifTags

    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

from ..tiff.tiffdatainterface import TiffImagingInterface
from ....utils import dict_deep_update, FilePathType, OptionalArrayType


class ScanImageImagingInterface(TiffImagingInterface):
    def __init__(
        self,
        file_path: FilePathType,
        fallback_sampling_frequency: Optional[float] = None,
        channel_names: OptionalArrayType = None,
    ):
        """
        DataInterface for reading Tiff files that are generated by ScanImage. This interface extracts the metadata
        from the exif of the tiff file.

        Parameters
        ----------
        file_path: str
            Path to tiff file.
        fallback_sampling_frequency: float, optional
            The sampling frequency can usually be extracted from the scanimage metadata in
            exif:ImageDescription:state.acq.frameRate. If not, use this.
        channel_names: list
            list of channel names.
        """

        assert HAVE_PIL, "To use the ScanImageTiffExtractor install Pillow: \n\n pip install pillow\n\n"
        image = Image.open(file_path)
        image_exif = image.getexif()
        exif = {ExifTags.TAGS[k]: v for k, v in image_exif.items() if k in ExifTags.TAGS and type(v) is not bytes}
        self.image_metadata = {
            x.split("=")[0]: x.split("=")[1] for x in exif["ImageDescription"].split("\r") if "=" in x
        }
        if "state.acq.frameRate" in self.image_metadata:
            sampling_frequency = float(self.image_metadata["state.acq.frameRate"])
        else:
            sampling_frequency = fallback_sampling_frequency

        super().__init__(file_path=file_path, sampling_frequency=sampling_frequency, channel_names=channel_names)

    def get_metadata(self):

        new_metadata = dict(Ophys=dict(TwoPhotonSeries=dict(description=json.dumps(self.image_metadata))))

        if "state.internal.triggerTimeString" in self.image_metadata:
            new_metadata["NWBFile"] = dict(
                session_start_time=dateparse(self.image_metadata["state.internal.triggerTimeString"])
            )

        return dict_deep_update(super().get_metadata(), new_metadata)
