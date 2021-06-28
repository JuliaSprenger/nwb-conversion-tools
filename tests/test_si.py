import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from datetime import datetime

import spikeextractors as se
from spikeextractors.testing import (
    check_sortings_equal,
    check_recordings_equal,
    check_dumping,
    check_recording_return_types,
    get_default_nwbfile_metadata
)
from pynwb import NWBHDF5IO, NWBFile

from nwb_conversion_tools.utils.spike_interface import get_nwb_metadata, write_recording, write_sorting


def _create_example(seed):
    channel_ids = [0, 1, 2, 3]
    num_channels = 4
    num_frames = 10000
    num_ttls = 30
    sampling_frequency = 30000
    X = np.random.RandomState(seed=seed).normal(0, 1, (num_channels, num_frames))
    geom = np.random.RandomState(seed=seed).normal(0, 1, (num_channels, 2))
    X = (X*100).astype(int)
    ttls = np.sort(np.random.permutation(num_frames)[:num_ttls])

    RX = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)
    RX.set_ttls(ttls)
    RX.set_channel_locations([0, 0], channel_ids=0)
    RX.add_epoch("epoch1", 0, 10)
    RX.add_epoch("epoch2", 10, 20)
    for i, channel_id in enumerate(RX.get_channel_ids()):
        RX.set_channel_property(channel_id=channel_id, property_name='shared_channel_prop', value=i)

    RX2 = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)
    RX2.copy_epochs(RX)
    times = np.arange(RX.get_num_frames())/RX.get_sampling_frequency() + 5
    RX2.set_times(times)

    RX3 = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)

    SX = se.NumpySortingExtractor()
    SX.set_sampling_frequency(sampling_frequency)
    spike_times = [200, 300, 400]
    train1 = np.sort(np.rint(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[0])).astype(int))
    SX.add_unit(unit_id=1, times=train1)
    SX.add_unit(unit_id=2, times=np.sort(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[1])))
    SX.add_unit(unit_id=3, times=np.sort(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[2])))
    SX.set_unit_property(unit_id=1, property_name='stability', value=80)
    SX.add_epoch("epoch1", 0, 10)
    SX.add_epoch("epoch2", 10, 20)

    SX2 = se.NumpySortingExtractor()
    SX2.set_sampling_frequency(sampling_frequency)
    spike_times2 = [100, 150, 450]
    train2 = np.rint(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[0])).astype(int)
    SX2.add_unit(unit_id=3, times=train2)
    SX2.add_unit(unit_id=4, times=np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[1]))
    SX2.add_unit(unit_id=5, times=np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[2]))
    SX2.set_unit_property(unit_id=4, property_name='stability', value=80)
    SX2.set_unit_spike_features(unit_id=3, feature_name='widths', value=np.asarray([3]*spike_times2[0]))
    SX2.copy_epochs(SX)
    SX2.copy_times(RX2)
    for i, unit_id in enumerate(SX2.get_unit_ids()):
        SX2.set_unit_property(unit_id=unit_id, property_name='shared_unit_prop', value=i)
        SX2.set_unit_spike_features(
            unit_id=unit_id,
            feature_name='shared_unit_feature',
            value=np.asarray([i]*spike_times2[i])
        )

    SX3 = se.NumpySortingExtractor()
    train3 = np.asarray([1, 20, 21, 35, 38, 45, 46, 47])
    SX3.add_unit(unit_id=0, times=train3)
    features3 = np.asarray([0, 5, 10, 15, 20, 25, 30, 35])
    features4 = np.asarray([0, 10, 20, 30])
    feature4_idx = np.asarray([0, 2, 4, 6])
    SX3.set_unit_spike_features(unit_id=0, feature_name='dummy', value=features3)
    SX3.set_unit_spike_features(unit_id=0, feature_name='dummy2', value=features4, indexes=feature4_idx)

    example_info = dict(
        channel_ids=channel_ids,
        num_channels=num_channels,
        num_frames=num_frames,
        sampling_frequency=sampling_frequency,
        unit_ids=[1, 2, 3],
        train1=train1,
        train2=train2,
        train3=train3,
        features3=features3,
        unit_prop=80,
        channel_prop=(0, 0),
        ttls=ttls,
        epochs_info=((0, 10), (10, 20)),
        geom=geom,
        times=times
    )

    return (RX, RX2, RX3, SX, SX2, SX3, example_info)


class TestExtractors(unittest.TestCase):
    def setUp(self):
        self.RX, self.RX2, self.RX3, self.SX, self.SX2, self.SX3, self.example_info = _create_example(seed=0)
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        del self.RX, self.RX2, self.RX3, self.SX, self.SX2, self.SX3
        shutil.rmtree(self.test_dir)

    def _create_example(self, seed):
        channel_ids = [0, 1, 2, 3]
        num_channels = 4
        num_frames = 10000
        num_ttls = 30
        sampling_frequency = 30000
        X = np.random.RandomState(seed=seed).normal(0, 1, (num_channels, num_frames))
        geom = np.random.RandomState(seed=seed).normal(0, 1, (num_channels, 2))
        X = (X * 100).astype(int)
        ttls = np.sort(np.random.permutation(num_frames)[:num_ttls])

        RX = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)
        RX.set_ttls(ttls)
        RX.set_channel_locations([0, 0], channel_ids=0)
        RX.add_epoch("epoch1", 0, 10)
        RX.add_epoch("epoch2", 10, 20)
        for i, channel_id in enumerate(RX.get_channel_ids()):
            RX.set_channel_property(channel_id=channel_id, property_name='shared_channel_prop', value=i)

        RX2 = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)
        RX2.copy_epochs(RX)
        times = np.arange(RX.get_num_frames()) / RX.get_sampling_frequency() + 5
        RX2.set_times(times)

        RX3 = se.NumpyRecordingExtractor(timeseries=X, sampling_frequency=sampling_frequency, geom=geom)

        SX = se.NumpySortingExtractor()
        SX.set_sampling_frequency(sampling_frequency)
        spike_times = [200, 300, 400]
        train1 = np.sort(np.rint(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[0])).astype(int))
        SX.add_unit(unit_id=1, times=train1)
        SX.add_unit(unit_id=2, times=np.sort(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[1])))
        SX.add_unit(unit_id=3, times=np.sort(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times[2])))
        SX.set_unit_property(unit_id=1, property_name='stability', value=80)
        SX.add_epoch("epoch1", 0, 10)
        SX.add_epoch("epoch2", 10, 20)

        SX2 = se.NumpySortingExtractor()
        SX2.set_sampling_frequency(sampling_frequency)
        spike_times2 = [100, 150, 450]
        train2 = np.rint(np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[0])).astype(int)
        SX2.add_unit(unit_id=3, times=train2)
        SX2.add_unit(unit_id=4, times=np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[1]))
        SX2.add_unit(unit_id=5, times=np.random.RandomState(seed=seed).uniform(0, num_frames, spike_times2[2]))
        SX2.set_unit_property(unit_id=4, property_name='stability', value=80)
        SX2.set_unit_spike_features(unit_id=3, feature_name='widths', value=np.asarray([3] * spike_times2[0]))
        SX2.copy_epochs(SX)
        SX2.copy_times(RX2)
        for i, unit_id in enumerate(SX2.get_unit_ids()):
            SX2.set_unit_property(unit_id=unit_id, property_name='shared_unit_prop', value=i)
            SX2.set_unit_spike_features(
                unit_id=unit_id,
                feature_name='shared_unit_feature',
                value=np.asarray([i] * spike_times2[i])
            )

        SX3 = se.NumpySortingExtractor()
        train3 = np.asarray([1, 20, 21, 35, 38, 45, 46, 47])
        SX3.add_unit(unit_id=0, times=train3)
        features3 = np.asarray([0, 5, 10, 15, 20, 25, 30, 35])
        features4 = np.asarray([0, 10, 20, 30])
        feature4_idx = np.asarray([0, 2, 4, 6])
        SX3.set_unit_spike_features(unit_id=0, feature_name='dummy', value=features3)
        SX3.set_unit_spike_features(unit_id=0, feature_name='dummy2', value=features4, indexes=feature4_idx)

        example_info = dict(
            channel_ids=channel_ids,
            num_channels=num_channels,
            num_frames=num_frames,
            sampling_frequency=sampling_frequency,
            unit_ids=[1, 2, 3],
            train1=train1,
            train2=train2,
            train3=train3,
            features3=features3,
            unit_prop=80,
            channel_prop=(0, 0),
            ttls=ttls,
            epochs_info=((0, 10), (10, 20)),
            geom=geom,
            times=times
        )

        return (RX, RX2, RX3, SX, SX2, SX3, example_info)


    def test_write_recording(self):
        path = self.test_dir + '/test.nwb'

        write_recording(self.RX, path)
        RX_nwb = se.NwbRecordingExtractor(path)
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX, RX_nwb)
        check_dumping(RX_nwb)
        del RX_nwb

        write_recording(recording=self.RX, save_path=path, overwrite=True)
        RX_nwb = se.NwbRecordingExtractor(path)
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX, RX_nwb)
        check_dumping(RX_nwb)

        # Writting multiple recordings using metadata
        metadata = get_default_nwbfile_metadata()
        path_multi = self.test_dir + '/test_multiple.nwb'
        write_recording(
            recording=self.RX,
            save_path=path_multi,
            metadata=metadata,
            write_as='raw',
            es_key='ElectricalSeries_raw',
        )
        write_recording(
            recording=self.RX2,
            save_path=path_multi,
            metadata=metadata,
            write_as='processed',
            es_key='ElectricalSeries_processed',
        )
        write_recording(
            recording=self.RX3,
            save_path=path_multi,
            metadata=metadata,
            write_as='lfp',
            es_key='ElectricalSeries_lfp',
        )

        RX_nwb = se.NwbRecordingExtractor(file_path=path_multi, electrical_series_name='raw_traces')
        check_recording_return_types(RX_nwb)
        check_recordings_equal(self.RX, RX_nwb)
        check_dumping(RX_nwb)
        del RX_nwb

    def test_write_sorting(self):
        path = self.test_dir + '/test.nwb'
        sf = self.RX.get_sampling_frequency()

        # Append sorting to existing file
        write_recording(recording=self.RX, save_path=path, overwrite=True)
        write_sorting(sorting=self.SX, save_path=path, overwrite=False)
        SX_nwb = se.NwbSortingExtractor(path)
        check_sortings_equal(self.SX, SX_nwb)
        check_dumping(SX_nwb)

        # Test for handling unit property descriptions argument
        property_descriptions = dict(stability="This is a description of stability.")
        write_sorting(
            sorting=self.SX,
            save_path=path,
            property_descriptions=property_descriptions,
            overwrite=True
        )
        SX_nwb = se.NwbSortingExtractor(path, sampling_frequency=sf)
        check_sortings_equal(self.SX, SX_nwb)
        check_dumping(SX_nwb)

        # Test for handling skip_properties argument
        write_sorting(
            sorting=self.SX,
            save_path=path,
            skip_properties=['stability'],
            overwrite=True
        )
        SX_nwb = se.NwbSortingExtractor(path, sampling_frequency=sf)
        assert 'stability' not in SX_nwb.get_shared_unit_property_names()
        check_sortings_equal(self.SX, SX_nwb)
        check_dumping(SX_nwb)

        # Test for handling skip_features argument
        # SX2 has timestamps, so loading it back from Nwb will not recover the same spike frames. Set use_times=False
        write_sorting(
            sorting=self.SX2,
            save_path=path,
            skip_features=['widths'],
            use_times=False,
            overwrite=True
        )
        SX_nwb = se.NwbSortingExtractor(path, sampling_frequency=sf)
        assert 'widths' not in SX_nwb.get_shared_unit_spike_feature_names()
        check_sortings_equal(self.SX2, SX_nwb)
        check_dumping(SX_nwb)

    def check_metadata_write(self, metadata: dict, nwbfile_path: Path, recording: se.RecordingExtractor):
        standard_metadata = get_nwb_metadata(recording=recording)
        device_defaults = dict(  # from the individual add_devices function
            name="Device",
            description="no description"
        )
        electrode_group_defaults = dict(  # from the individual add_electrode_groups function
            name="Electrode Group",
            description="no description",
            location="unknown",
            device="Device"
        )

        with NWBHDF5IO(path=nwbfile_path, mode="r", load_namespaces=True) as io:
            nwbfile = io.read()

            device_source = metadata["Ecephys"].get("Device", standard_metadata["Ecephys"]["Device"])
            self.assertEqual(len(device_source), len(nwbfile.devices))
            for device in device_source:
                device_name = device.get("name", device_defaults["name"])
                self.assertIn(device_name, nwbfile.devices)
                self.assertEqual(
                    device.get("description", device_defaults["description"]), nwbfile.devices[device_name].description
                )
                self.assertEqual(device.get("manufacturer"), nwbfile.devices[device["name"]].manufacturer)

            electrode_group_source = metadata["Ecephys"].get(
                "ElectrodeGroup",
                standard_metadata["Ecephys"]["ElectrodeGroup"]
            )
            self.assertEqual(len(electrode_group_source), len(nwbfile.electrode_groups))
            for group in electrode_group_source:
                group_name = group.get("name", electrode_group_defaults["name"])
                self.assertIn(group_name, nwbfile.electrode_groups)
                self.assertEqual(
                    group.get("description", electrode_group_defaults["description"]),
                    nwbfile.electrode_groups[group_name].description
                )
                self.assertEqual(
                    group.get("location", electrode_group_defaults["location"]),
                    nwbfile.electrode_groups[group_name].location
                )
                device_name = group.get("device", electrode_group_defaults["device"])
                self.assertIn(device_name, nwbfile.devices)
                self.assertEqual(nwbfile.electrode_groups[group_name].device, nwbfile.devices[device_name])

            n_channels = len(recording.get_channel_ids())
            electrode_source = metadata["Ecephys"].get("Electrodes", [])
            self.assertEqual(n_channels, len(nwbfile.electrodes))
            for column in electrode_source:
                column_name = column["name"]
                self.assertIn(column_name, nwbfile.electrodes)
                self.assertEqual(column["description"], getattr(nwbfile.electrodes, column_name).description)
                if column_name in ["x", "y", "z", "rel_x", "rel_y", "rel_z"]:
                    for j in n_channels:
                        self.assertEqual(column["data"][j], getattr(nwbfile.electrodes[j], column_name).values[0])
                else:
                    for j in n_channels:
                        self.assertTrue(
                            column["data"][j] == getattr(nwbfile.electrodes[j], column_name).values[0]
                            or (
                                    np.isnan(column["data"][j])
                                    and np.isnan(getattr(nwbfile.electrodes[j], column_name).values[0])
                            )
                        )

    def test_nwb_metadata(self):
        path = self.test_dir + '/test_metadata.nwb'

        write_recording(recording=self.RX, save_path=path, overwrite=True)
        self.check_metadata_write(
            metadata=get_nwb_metadata(recording=self.RX),
            nwbfile_path=path,
            recording=self.RX
        )

        # Manually adjusted device name - must properly adjust electrode_group reference
        metadata2 = get_nwb_metadata(recording=self.RX)
        metadata2["Ecephys"]["Device"] = [dict(name="TestDevice", description="A test device.", manufacturer="unknown")]
        metadata2["Ecephys"]["ElectrodeGroup"][0]["device"] = "TestDevice"
        write_recording(recording=self.RX, metadata=metadata2, save_path=path, overwrite=True)
        self.check_metadata_write(
            metadata=metadata2,
            nwbfile_path=path,
            recording=self.RX
        )

        # Two devices in metadata
        metadata3 = get_nwb_metadata(recording=self.RX)
        metadata3["Ecephys"]["Device"].append(
            dict(name="Device2", description="A second device.", manufacturer="unknown")
        )
        write_recording(recording=self.RX, metadata=metadata3, save_path=path, overwrite=True)
        self.check_metadata_write(
            metadata=metadata3,
            nwbfile_path=path,
            recording=self.RX
        )

        # Forcing default auto-population from add_electrode_groups, and not get_nwb_metdata
        metadata4 = get_nwb_metadata(recording=self.RX)
        metadata4["Ecephys"]["Device"] = [dict(name="TestDevice", description="A test device.", manufacturer="unknown")]
        metadata4["Ecephys"].pop("ElectrodeGroup")
        write_recording(recording=self.RX, metadata=metadata4, save_path=path, overwrite=True)
        self.check_metadata_write(
            metadata=metadata4,
            nwbfile_path=path,
            recording=self.RX
        )


class TestWriteElectrodes(unittest.TestCase):
    def setUp(self):
        self.RX, self.RX2, _, _, _, _, _ = _create_example(seed=0)
        self.test_dir = tempfile.mkdtemp()
        self.path1 = self.test_dir + '/test_electrodes1.nwb'
        self.path2 = self.test_dir + '/test_electrodes2.nwb'
        self.path3 = self.test_dir + '/test_electrodes3.nwb'
        self.nwbfile1 = NWBFile('sess desc1', 'file id1', datetime.now())
        self.nwbfile2 = NWBFile('sess desc2', 'file id2', datetime.now())
        self.nwbfile3 = NWBFile('sess desc3', 'file id3', datetime.now())
        self.metadata_list = [dict(Ecephys={i: dict(name=i, description='desc')}) for i in ['es1', 'es2']]
        # change channel_ids
        id_offset = np.max(self.RX.get_channel_ids())
        self.RX2 = se.subrecordingextractor.SubRecordingExtractor(self.RX2,
                                            renamed_channel_ids=np.array(self.RX2.get_channel_ids())+id_offset+1)
        self.RX2.set_channel_groups([2*i for i in self.RX.get_channel_groups()])
        # add common properties:
        for no, (chan_id1, chan_id2) in enumerate(zip(self.RX.get_channel_ids(), self.RX2.get_channel_ids())):
            self.RX2.set_channel_property(chan_id2, 'prop1', '10Hz')
            self.RX.set_channel_property(chan_id1, 'prop1', '10Hz')
            self.RX2.set_channel_property(chan_id2, 'brain_area', 'M1')
            self.RX.set_channel_property(chan_id1, 'brain_area', 'PMd')
            self.RX2.set_channel_property(chan_id2, 'group_name', 'M1')
            self.RX.set_channel_property(chan_id1, 'group_name', 'PMd')
            if no%2 == 0:
                self.RX2.set_channel_property(chan_id2, 'prop2', chan_id2)
                self.RX.set_channel_property(chan_id1, 'prop2', chan_id1)
                self.RX2.set_channel_property(chan_id2, 'prop3', str(chan_id2))
                self.RX.set_channel_property(chan_id1, 'prop3', str(chan_id1))

    def test_append_same_properties(self):
        write_recording(recording=self.RX, nwbfile=self.nwbfile1, metadata=self.metadata_list[0], es_key='es1')
        write_recording(recording=self.RX2, nwbfile=self.nwbfile1, metadata=self.metadata_list[1], es_key='es2')
        with NWBHDF5IO(str(self.path1), 'w') as io:
            io.write(self.nwbfile1)
        with NWBHDF5IO(str(self.path1), 'r') as io:
            nwb = io.read()
            assert all(nwb.electrodes.id.data[()] == np.array(self.RX.get_channel_ids() + self.RX2.get_channel_ids()))
            assert all([i in nwb.electrodes.colnames for i in ['prop1', 'prop2', 'prop3']])
            for i, chan_id in enumerate(nwb.electrodes.id.data):
                assert nwb.electrodes['prop1'][i] == '10Hz'
                if chan_id in self.RX.get_channel_ids():
                    assert nwb.electrodes['location'][i] == 'PMd'
                    assert nwb.electrodes['group_name'][i] == 'PMd'
                    assert nwb.electrodes['group'][i].name == 'PMd'
                else:
                    assert nwb.electrodes['location'][i] == 'M1'
                    assert nwb.electrodes['group_name'][i] == 'M1'
                    assert nwb.electrodes['group'][i].name == 'M1'
                if i%2 == 0:
                    assert nwb.electrodes['prop2'][i] == chan_id
                    assert nwb.electrodes['prop3'][i] == str(chan_id)
                else:
                    assert np.isnan(nwb.electrodes['prop2'][i])
                    assert nwb.electrodes['prop3'][i] == ''

    def test_different_channel_properties(self):
        for chan_id in self.RX2.get_channel_ids():
            self.RX2.clear_channel_property(chan_id,'prop2')
            self.RX2.set_channel_property(chan_id,'prop_new',chan_id)
        write_recording(recording=self.RX, nwbfile=self.nwbfile1, metadata=self.metadata_list[0], es_key='es1')
        write_recording(recording=self.RX2, nwbfile=self.nwbfile1, metadata=self.metadata_list[1], es_key='es2')
        with NWBHDF5IO(str(self.path1), 'w') as io:
            io.write(self.nwbfile1)
        with NWBHDF5IO(str(self.path1), 'r') as io:
            nwb = io.read()
            for i, chan_id in enumerate(nwb.electrodes.id.data):
                if i<len(nwb.electrodes.id.data)/2:
                    assert np.isnan(nwb.electrodes['prop_new'][i])
                    if i%2 == 0:
                        assert nwb.electrodes['prop2'][i] == chan_id
                    else:
                        assert np.isnan(nwb.electrodes['prop2'][i])
                else:
                    assert np.isnan(nwb.electrodes['prop2'][i])
                    assert nwb.electrodes['prop_new'][i]==chan_id

    def test_group_set_custom_description(self):
        for i,grp_name in enumerate(['PMd','M1']):
            self.metadata_list[i]['Ecephys'].update(ElectrodeGroup=[dict(name=grp_name,
                                                                     description=grp_name+' description')])
        write_recording(recording=self.RX, nwbfile=self.nwbfile1, metadata=self.metadata_list[0], es_key='es1')
        write_recording(recording=self.RX2, nwbfile=self.nwbfile1, metadata=self.metadata_list[1], es_key='es2')
        with NWBHDF5IO(str(self.path1), 'w') as io:
            io.write(self.nwbfile1)
        with NWBHDF5IO(str(self.path1), 'r') as io:
            nwb = io.read()
            for i, chan_id in enumerate(nwb.electrodes.id.data):
                if i<len(nwb.electrodes.id.data)/2:
                    assert nwb.electrodes['group_name'][i]=='PMd'
                    assert nwb.electrodes['group'][i].description == 'PMd description'
                else:
                    assert nwb.electrodes['group_name'][i] == 'M1'
                    assert nwb.electrodes['group'][i].description == 'M1 description'

if __name__ == '__main__':
    unittest.main()
