from datetime import datetime, timedelta
from pathlib import Path
import json
from neo import AxonIO

from ..base_interface_icephys_neo import BaseIcephysNeoInterface
from ....utils.neo import get_number_of_electrodes, get_number_of_segments


class AbfNeoDataInterface(BaseIcephysNeoInterface):
    """ABF DataInterface based on Neo AxonIO"""

    neo_class = AxonIO

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the Neo class"""
        source_schema = super().get_source_schema()
        source_schema["properties"]["files_paths"] = dict(
            type="array",
            minItems=1,
            items={"type": "string", "format": "file"},
            description="Array of paths to ABF files.",
        )
        source_schema["properties"]["metadata_file_path"] = dict(
            type="string", format="file", description="Path to JSON file containing metadata for this experiment."
        )
        return source_schema

    def __init__(self, files_paths: list, metadata_file_path: str = None):
        super().__init__(files_paths=files_paths)
        self.source_data["metadata_file_path"] = metadata_file_path

    def get_metadata(self):
        """Auto-fill as much of the metadata as possible. Must comply with metadata schema."""
        metadata = super().get_metadata()

        # Load metafile, if present in data_source. This is Optional
        # This metafile can carry extra information such as: Subject, LabMetadata and stimulus_type for recording sessions
        metafile_data = dict()
        metafile = self.source_data["metadata_file_path"]
        if Path(metafile).is_file():
            with open(metafile) as json_file:
                metafile_data = json.load(json_file)

        # Extract start_time info
        first_reader = self.readers_list[0]
        startDate = str(first_reader._axon_info["uFileStartDate"])
        startTime = round(first_reader._axon_info["uFileStartTimeMS"] / 1000)
        startDate = datetime.strptime(startDate, "%Y%m%d")
        startTime = timedelta(seconds=startTime)
        first_session_time = startDate + startTime
        session_start_time = first_session_time.strftime("%Y-%m-%dT%H:%M:%S%z")

        # NWBFile metadata
        if "NWBFile" not in metadata:
            metadata["NWBFile"] = dict()
        metadata["NWBFile"].update(
            session_start_time=session_start_time, experimenter=[metafile_data.get("experimenter", "")]
        )

        # Subject metadata
        metadata["Subject"] = dict(
            subject_id=metafile_data.get("subject_id", ""),
            species=metafile_data.get("species", ""),
            sex=metafile_data.get("sex", "U"),
            date_of_birth=metafile_data.get("dob", ""),
        )

        # LabMetadata
        metadata["LabMetadata"] = dict(
            # Required fields for DANDI
            cell_id=metafile_data.get("cell_id", ""),
            slice_id=metafile_data.get("slice_id", ""),
            # Lab specific metadata
            targeted_layer=metafile_data.get("targeted_layer", ""),
            inferred_layer=metafile_data.get("estimate_laminate", ""),
        )

        # Recordings metadata
        metafile_sessions = metafile_data.get("recording_sessions", dict())
        metadata["Icephys"]["Recordings"] = list()

        # Extract useful metadata from each reader in the sequence
        i = 0
        ii = 0
        iii = 0
        for ir, reader in enumerate(self.readers_list):
            # Get extra info from metafile, if present
            abf_file_name = reader.filename.split("/")[-1]
            item = [s for s in metafile_sessions if s.get("abf_file_name", "") == abf_file_name]
            extra_info = item[0] if len(item) > 0 else dict()

            startDate = str(reader._axon_info["uFileStartDate"])
            startTime = round(reader._axon_info["uFileStartTimeMS"] / 1000)
            startDate = datetime.strptime(startDate, "%Y%m%d")
            startTime = timedelta(seconds=startTime)
            abfDateTime = startDate + startTime

            # Calculate session start time relative to first abf file (first session), in seconds
            relative_session_start_time = abfDateTime - first_session_time
            relative_session_start_time = float(relative_session_start_time.seconds)

            n_segments = get_number_of_segments(reader, block=0)
            n_electrodes = get_number_of_electrodes(reader)

            # Loop through segments (sequential recordings table)
            for sg in range(n_segments):
                # Loop through channels (simultaneous recordings table)
                for el in range(n_electrodes):
                    metadata["Icephys"]["Recordings"].append(
                        dict(
                            relative_session_start_time=relative_session_start_time,
                            stimulus_type=extra_info.get("stimulus_type", "not described"),
                            icephys_experiment_type=extra_info.get("icephys_experiment_type", None),
                            intracellular_recordings_table_id=i,
                            simultaneous_recordings_table_id=ii,
                            sequential_recordings_table_id=iii,
                            # repetitions_table_id=0,
                            # experimental_conditions_table_id=0
                        )
                    )
                    i += 1
                ii += 1
            iii += 1

        return metadata
