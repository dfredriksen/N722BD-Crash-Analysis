"""Checks on scientific boundary cases; source evidence is not modified."""
import io
import math
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_investigation import interpolate, sample, beam_height, slant_from_ground, digest, flight_features
from make_overlays import ground_from_slant, destination


class ScienceTests(unittest.TestCase):
    def test_no_extrapolation_or_long_gap(self):
        f=pd.DataFrame(dict(time=pd.to_datetime(['2026-11-01T00:00:00Z','2026-11-01T00:00:30Z']),alt=[0.,30.]))
        self.assertIsNone(interpolate(f,pd.Timestamp('2026-11-01T00:00:15Z'),['alt']))
        self.assertIsNone(interpolate(f,pd.Timestamp('2026-10-31T23:59:59Z'),['alt']))

    def test_exact_endpoint_is_valid(self):
        f=pd.DataFrame(dict(time=pd.to_datetime(['2026-11-01T00:00:00Z']),alt=[100.]))
        self.assertEqual(interpolate(f,f.time.iloc[0],['alt']),([100.],0.,0.))

    def test_brackets_and_linear_interpolation(self):
        f=pd.DataFrame(dict(time=pd.to_datetime(['2026-11-01T00:00:00Z','2026-11-01T00:00:10Z']),alt=[0.,100.]))
        self.assertEqual(interpolate(f,pd.Timestamp('2026-11-01T00:00:02Z'),['alt']),([20.],2.,8.))

    def test_slant_ground_roundtrip(self):
        for elevation in (.5,6.372,19.5):
            for k in (1.,4/3,1.5):
                slant=slant_from_ground(100000,elevation,k)
                self.assertGreater(slant,100000)
                self.assertAlmostEqual(ground_from_slant(slant,elevation,k),100000,places=7)

    def test_height_reference_and_refraction(self):
        self.assertEqual(beam_height(0,10,33),33)
        self.assertGreater(beam_height(100000,.5,33,1),beam_height(100000,.5,33,4/3))

    def test_gate_flags_not_wind_or_missing_as_zero(self):
        m=dict(first_gate=1000,gate_spacing=250,data=np.array([0,1,130]),offset=129.,scale=2.)
        self.assertTrue(math.isnan(sample(m,1000)['value']))
        self.assertEqual(sample(m,1250)['status'],'range_folded')
        self.assertEqual(sample(m,1500)['value'],.5)
        self.assertEqual(sample(m,2000)['status'],'outside_range')
        self.assertEqual(sample(None,1000)['status'],'moment_absent')

    def test_sha256(self):
        self.assertEqual(digest(io.BytesIO(b'abc')),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')

    def test_geographic_axis_order(self):
        lon,lat=destination(26,-80,0,1000)
        self.assertAlmostEqual(lon,-80)
        self.assertGreater(lat,26)

    def test_path_breaks_across_missing_positions(self):
        frame=pd.DataFrame(dict(time=pd.to_datetime(['2026-11-01T00:00:00Z','2026-11-01T00:00:01Z','2026-11-01T00:05:00Z']),
            latitude=[26.,26.1,27.],longitude=[-80.,-80.1,-80.2]))
        features=flight_features(frame)
        self.assertEqual(len(features),2)
        self.assertEqual(features[0]['geometry']['type'],'LineString')
        self.assertEqual(features[1]['geometry']['type'],'Point')


if __name__ == '__main__':
    unittest.main()
