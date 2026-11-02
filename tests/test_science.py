"""Boundary and recorded-result regressions; these do not authenticate evidence.

Recorded-result checks recompute counts from committed per-ray/per-match CSVs.
They detect changes from the reviewed results without rerunning radar decoding;
they do not independently reproduce the raw-archive processing or certify truth.
"""
import io
import math
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_investigation import interpolate, sample, beam_height, slant_from_ground, digest, flight_features
from make_overlays import ground_from_slant, destination, plot_observed_track


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


    def test_png_track_breaks_gaps_and_keeps_isolated_observations(self):
        # Exactly 20 seconds stays connected; 21 seconds splits the path.
        frame=pd.DataFrame(dict(time=pd.to_datetime([
            '2026-11-01T00:00:00Z','2026-11-01T00:00:20Z',
            '2026-11-01T00:00:41Z','2026-11-01T00:00:42Z',
            '2026-11-01T00:01:10Z']),
            latitude=[26.,26.1,26.2,26.3,26.4],longitude=[-80.,-80.1,-80.2,-80.3,-80.4]))
        fig,ax=plt.subplots()
        try:
            artists=plot_observed_track(ax,frame)
            self.assertEqual(len(artists),3)
            self.assertEqual(list(artists[0].get_xdata()),[-80.,-80.1])
            self.assertEqual(list(artists[1].get_xdata()),[-80.2,-80.3])
            self.assertEqual(list(artists[2].get_xdata()),[-80.4])
            self.assertEqual(artists[2].get_linestyle(),'None')
            self.assertEqual(artists[2].get_marker(),'.')
            # Assert that the actual rendered artists use the GeoJSON segments.
            features=flight_features(frame)
            for artist,feature in zip(artists,features):
                coords=feature['geometry']['coordinates']
                if feature['geometry']['type']=='Point':coords=[coords]
                self.assertEqual(list(zip(artist.get_xdata(),artist.get_ydata())),
                                 [tuple(c) for c in coords])
        finally:
            plt.close(fig)


class RecordedFindingsTests(unittest.TestCase):
    """Freeze the reviewed CSV-derived findings, not the accuracy of the source."""

    @classmethod
    def setUpClass(cls):
        output=Path(__file__).resolve().parents[1]/'results/independent'
        cls.rays=pd.read_csv(output/'radar_comparison.csv',usecols=[
            'volume','custom_ray_found','SW_pyart_present','SW_custom_present'])
        cls.matches=pd.read_csv(output/'aircraft_radar_matches.csv')

    def test_reviewed_decoder_coverage(self):
        self.assertEqual(len(self.rays),48600)
        self.assertEqual(int(self.rays.custom_ray_found.sum()),29556)
        self.assertEqual(int((~self.rays.custom_ray_found).sum()),19044)
        by_volume=self.rays.groupby('volume').agg(
            pyart=('custom_ray_found','size'),custom=('custom_ray_found','sum'))
        self.assertEqual(by_volume.pyart.tolist(),[9720]*5)
        self.assertEqual(by_volume.custom.tolist(),[6245,5674,5789,5933,5915])

    def test_reviewed_spectrum_width_omissions(self):
        shared=self.rays[self.rays.custom_ray_found]
        missing=shared.SW_pyart_present & ~shared.SW_custom_present
        unexpected=~shared.SW_pyart_present & shared.SW_custom_present
        self.assertEqual(int(missing.sum()),3929)
        self.assertEqual(int(unexpected.sum()),0)

    def test_geometric_overlap_is_not_a_valid_radar_detection(self):
        overlap=self.matches[self.matches.nominal_joint_overlap]
        self.assertEqual(len(overlap),1)
        self.assertEqual(overlap.utc.iloc[0],'2026-11-01T17:39:11.040000+00:00')
        for field in ['REF','VEL','SW']:
            self.assertEqual(overlap[field+'_status'].iloc[0],'below_threshold_or_missing')
            self.assertEqual(overlap[field+'_raw'].iloc[0],0)
            self.assertTrue(pd.isna(overlap[field+'_value'].iloc[0]))

    def test_valid_moments_do_not_establish_geometric_overlap(self):
        near=self.matches[self.matches.utc=='2026-11-01T17:44:26.796000+00:00']
        self.assertEqual(len(near),1)
        row=near.iloc[0]
        self.assertFalse(row.nominal_vertical_overlap)
        self.assertTrue(row.nominal_horizontal_overlap)
        self.assertFalse(row.nominal_joint_overlap)
        for field,value in [('REF',13.5),('VEL',-6.),('SW',1.5)]:
            self.assertEqual(row[field+'_status'],'valid')
            self.assertEqual(row[field+'_value'],value)
        # Different modeled points select adjacent native gates; preserve both.
        self.assertEqual(row.REF_range_m, 99875.)
        self.assertEqual(row.axis_REF_range_m, 100125.)
        self.assertEqual(row.axis_REF_value, 12.5)
        self.assertEqual(row.axis_SW_value, .5)


if __name__ == '__main__':
    unittest.main()
