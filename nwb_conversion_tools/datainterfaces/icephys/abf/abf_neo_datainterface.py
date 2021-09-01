from ..base_interface_icephys_neo import BaseIcephysNeoInterface
from ....utils.json_schema import get_schema_from_method_signature
from neo import AxonIO


class AbfNeoDataInterface(BaseIcephysNeoInterface):
    """ABF DataInterface based on Neo AxonIO"""

    neo_class = AxonIO

    @classmethod
    def get_source_schema(cls):
        """Compile input schema for the Neo class"""
        source_schema = get_schema_from_method_signature(
            class_method=cls.__init__, 
            exclude=[]
        )
        source_schema["properties"]["file_path"]["format"] = "file"
        source_schema["properties"]["file_path"]["description"] = "Path to ABF file."
        return source_schema

    def __init__(self, file_path: str):
        super().__init__(filename=file_path)