"""Adversarial fixtures for validation failures and model boundary behavior."""
import json
import math
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_highlevel_api import (REQUIRED_METADATA, METADATA_TOLERANCES,
    compare_metadata, validate_api_table, validation_summary)
from summarize_validation import field_summary
from radar_geometry import point_geometry, height_at_ground, altitude_interval_overlap, slant_from_ground
from run_investigation import clock_case, distance_bearing


class ValidationGuardTests(unittest.TestCase):
    def setUp(self):
        self.api = pd.DataFrame([dict(file='fixture', time=pd.Timestamp('2026-11-01T17:44:26Z'),
            azimuth_deg=345., elevation_deg=6., radar_alt_m=33., radar_lat=25.6,
            radar_lon=-80.4, range_gate_m=117375., ray_index=0.,
            REF_dBZ=np.nan, VEL_mps=np.nan, SW_mps=np.nan)])
        row = dict(api_ray_found=True, **{k: 0. for k in METADATA_TOLERANCES})
        for field in ('REF', 'VEL', 'SW'):
            row[field+'_mask_agrees'] = True
            row[field+'_value_difference'] = np.nan
        self.comparison = pd.DataFrame([row])

    def test_nonfinite_required_metadata_rejected(self):
        validate_api_table(self.api)
        for column in REQUIRED_METADATA:
            for value in (np.nan, np.inf, -np.inf):
                with self.subTest(column=column, value=value):
                    bad = self.api.copy(); bad.loc[0, column] = value
                    with self.assertRaises(ValueError): validate_api_table(bad)

    def test_site_coordinate_disagreements_rejected(self):
        record = {'msg_header': dict(azimuth_angle=345., elevation_angle=6.)}
        for column in ('radar_lat', 'radar_lon'):
            bad = self.api.iloc[0].copy(); bad[column] += 1.
            diff = compare_metadata(bad, record, (25.6, -80.4, 33.), 0)
            c = self.comparison.copy()
            for key in METADATA_TOLERANCES: c.loc[0, key] = diff[key]
            with self.assertRaises(ValueError): validation_summary(c, 1)

    def test_nan_comparisons_and_incomplete_coverage_rejected(self):
        for column in METADATA_TOLERANCES:
            c = self.comparison.copy(); c.loc[0, column] = np.nan
            with self.assertRaises(ValueError): validation_summary(c, 1)
        with self.assertRaises(ValueError): validation_summary(self.comparison, 2)
        c = self.comparison.copy(); c.loc[0, 'api_ray_found'] = False
        with self.assertRaises(ValueError): validation_summary(c, 1)
        with self.assertRaises(ValueError): validate_api_table(pd.concat([self.api]*2))

    def test_all_masked_is_null_not_agreement_on_valid_values(self):
        summary = validation_summary(self.comparison, 1)
        self.assertIsNone(summary['fields']['REF']['max_value_difference'])
        self.assertEqual(summary['fields']['REF']['comparable_valid_rays'], 0)
        self.assertEqual(summary['fields']['REF']['compared_mask_rays'], 1)
        json.dumps(summary, allow_nan=False)

    def test_geometry_failure_survives_unavailable_raw_comparison(self):
        # Array-length mismatch: geometry is known false, element comparisons unavailable.
        frame = pd.DataFrame([dict(custom_ray_found=True, REF_pyart_present=True,
            REF_custom_present=True, REF_native_gates=3, REF_geometry_equal=False,
            REF_raw_mismatches=np.nan, REF_mask_mismatches=np.nan,
            REF_max_value_difference=np.nan)])
        result = field_summary(frame, 'REF')
        self.assertEqual(result['geometry_disagreements'], 1)
        self.assertEqual(result['geometry_compared_rays'], 1)
        self.assertEqual(result['raw_comparison_unavailable_on_shared_moments'], 1)
        self.assertIsNone(result['raw_gate_mismatches'])
        self.assertIsNone(result['max_value_difference'])
        frame['REF_geometry_equal'] = pd.Series([None], dtype=object)
        result = field_summary(frame, 'REF')
        self.assertEqual(result['geometry_comparison_unavailable_on_shared_moments'], 1)
        self.assertEqual(result['geometry_compared_rays'], 0)


class ThreeDimensionalGeometryTests(unittest.TestCase):
    def test_point_on_axis_roundtrip(self):
        for k in (1., 4/3, 1.5):
            height = height_at_ground(100000., 6., 33., k)
            g = point_geometry(100000., height, 33., 6., 0., k)
            self.assertAlmostEqual(g['aircraft_slant_range_m'], slant_from_ground(100000., 6., k), places=6)
            self.assertAlmostEqual(g['aircraft_apparent_elevation_deg'], 6., places=9)
            self.assertLess(g['axis_to_aircraft_angle_deg'], 1e-5)
            self.assertTrue(g['nominal_joint_overlap'])

    def test_separate_projections_do_not_define_circular_cone(self):
        # Both offsets are <0.5 deg, but their combined angular separation is >0.5.
        height = height_at_ground(100000., 5.6, 33.)
        g = point_geometry(100000., height, 33., 6., .4)
        self.assertGreater(height, height_at_ground(100000., 5.5, 33.))
        self.assertLess(height, height_at_ground(100000., 6.5, 33.))
        self.assertFalse(g['nominal_joint_overlap'])
        self.assertGreater(g['axis_to_aircraft_angle_deg'], .5)

    def test_target_altitude_and_width_scenarios(self):
        ground, el, offset = 99307.556752, 6.3720703125, -.354224
        self.assertAlmostEqual(height_at_ground(ground, el-.5, 33.), 10840.488847, places=4)
        g = point_geometry(ground, 10668., 33., el, offset)
        self.assertAlmostEqual(g['aircraft_slant_range_m'], 99936.622072, places=4)
        self.assertFalse(altitude_interval_overlap(g, 10668., 304.8))
        self.assertFalse(point_geometry(ground, 10668.+304.8, 33., el, offset)['nominal_joint_overlap'])
        self.assertTrue(point_geometry(ground, 10668., 33., el, offset, width=1.5)['nominal_joint_overlap'])

    def test_no_bearing_slice_is_not_altitude_overlap(self):
        g = point_geometry(100000., 10000., 33., 6., 2.)
        self.assertFalse(g['cone_slice_intersects_bearing'])
        self.assertTrue(math.isnan(g['cone_lower_m_msl']))
        self.assertFalse(altitude_interval_overlap(g, 10000., 100000.))

    def test_shift_can_recover_state_excluded_at_nominal_time(self):
        t = pd.Timestamp('2026-11-01T17:44:26Z')
        frames = dict(pos=pd.DataFrame(dict(time=[t+pd.Timedelta(seconds=1)], latitude=[26.5], longitude=[-80.4])),
            alt=pd.DataFrame(dict(time=[t+pd.Timedelta(seconds=1)], altitude=[35000.])))
        _, az = distance_bearing(25.6, -80.4, 26.5, -80.4)
        self.assertFalse(clock_case(frames, t, 0., 25.6, -80.4, 33., az, 6.)['brackets_available'])
        shifted = clock_case(frames, t, 1., 25.6, -80.4, 33., az, 6.)
        self.assertTrue(shifted['brackets_available'])
        self.assertTrue(shifted['within_2deg'])


if __name__ == '__main__': unittest.main()
