"""Evidence audit, native-gate cross-check and aircraft-centered reconstruction.

Uses the unmodified, BSD-licensed Py-ART 2.3.0 low-level Archive II reader for
native-gate comparison and reconstruction. The separate full Py-ART API run is
performed by validate_n722bd_pyart.py and checked by check_highlevel_api.py.
The delivered investigation ran both paths under Python 3.11 with the full
Py-ART environment installed. Originals are read only.
"""
import argparse
import ast
import csv
import datetime as dt
import hashlib
import io
import json
import math
import platform
from pathlib import Path
import struct
import bz2
import zipfile

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pyproj import Geod
from vendor.pyart_nexrad_level2 import NEXRADLevel2File
from evidence_source import EvidenceSource
from radar_geometry import (slant_from_ground, beam_height, height_at_ground,
                            point_geometry, altitude_interval_overlap)

ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc
EPOCH = dt.datetime(1970, 1, 1, tzinfo=UTC)
FIELDS = {'DREF': 'REF', 'DVEL': 'VEL', 'DSW': 'SW'}
GEOD = Geod(ellps='WGS84')


def digest(stream):
    h = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        h.update(block)
    return h.hexdigest()


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(path, index=False)
    return frame


def flight_features(positions):
    """Do not draw continuous flight paths across unsupported observation gaps."""
    groups=(positions.time.diff().dt.total_seconds().fillna(0)>20).cumsum()
    features=[]
    for _,part in positions.groupby(groups):
        coords=part[['longitude','latitude']].values.tolist()
        geometry=dict(type='LineString',coordinates=coords) if len(coords)>1 else dict(type='Point',coordinates=coords[0])
        features.append(dict(type='Feature',properties=dict(source='FR24',
            altitude_datum='unverified',first_utc=part.time.iloc[0].isoformat(),
            last_utc=part.time.iloc[-1].isoformat(),observations=len(part),
            segment_break_gap_s=20,timing='see flight_observations.csv'),geometry=geometry))
    return features


def custom_functions(source):
    # Load ONLY the supplied parser's function definitions; its top-level analysis
    # assumes /mnt/data and would overwrite supplied results.
    tree = ast.parse(source)
    tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    scope = dict(np=np, struct=struct, bz2=bz2, datetime=dt, math=math)
    exec(compile(tree, 'supplied_analyze_3d_n722bd.py', 'exec'), scope)
    return scope


class MemoryArchive:
    def __init__(self, data):
        self.data = data

    def read_bytes(self):
        return self.data


def timestamp(record):
    h = record['msg_header']
    return EPOCH + dt.timedelta(days=h['collect_date'] - 1,
                                milliseconds=h['collect_ms'])


def ray_key(time, az, el, sweep):
    return (time, float(az), float(el), int(sweep))


def interpolate(frame, time, cols, max_gap=10):
    # Cached arrays avoid constructing mixed-type pandas rows for every ray.
    # Frames are immutable after construction throughout this analysis.
    cache = frame.attrs.setdefault('_interpolation_arrays', {})
    if 'times' not in cache:
        cache['times'] = frame.time.to_numpy(dtype='datetime64[ns]').astype(np.int64)
    for col in cols:
        if col not in cache:
            cache[col] = frame[col].to_numpy(dtype=float)
    target = pd.Timestamp(time).value
    index = int(np.searchsorted(cache['times'], target))
    if index < len(frame) and cache['times'][index] == target:
        return [float(cache[c][index]) for c in cols], 0., 0.
    if index == 0 or index == len(frame):
        return None
    left = (target-int(cache['times'][index-1]))/1e9
    right = (int(cache['times'][index])-target)/1e9
    if left > max_gap or right > max_gap:
        return None
    w = left / (left + right)
    return [float(cache[c][index-1]) * (1-w) + float(cache[c][index]) * w for c in cols], left, right


def distance_bearing(lat1, lon1, lat2, lon2):
    bearing, _, distance = GEOD.inv(lon1, lat1, lon2, lat2)
    return distance, bearing % 360


def sample(moment, slant):
    if moment is None:
        return dict(value=np.nan, status='moment_absent', gate=-1, range_m=np.nan,
                    raw=np.nan, gate_spacing_m=np.nan)
    index = int(np.floor((slant-moment['first_gate'])/moment['gate_spacing']+.5))
    if index < 0 or index >= len(moment['data']):
        return dict(value=np.nan, status='outside_range', gate=index, range_m=np.nan,
                    raw=np.nan, gate_spacing_m=moment['gate_spacing'])
    raw = int(moment['data'][index])
    return dict(value=(raw-moment['offset'])/moment['scale'] if raw > 1 else np.nan,
        status=('below_threshold_or_missing' if raw == 0 else 'range_folded' if raw == 1 else 'valid'),
        raw=raw, gate=index, range_m=moment['first_gate']+index*moment['gate_spacing'],
        gate_spacing_m=moment['gate_spacing'])


def clock_case(frames, time, shift, lat, lon, height, az, el):
    """Evaluate each radial before nominal filtering; positive shift queries later FR24 time."""
    shifted = pd.Timestamp(time)+pd.Timedelta(seconds=shift)
    position = interpolate(frames['pos'], shifted, ['latitude', 'longitude'])
    altitude = interpolate(frames['alt'], shifted, ['altitude'])
    row = dict(aircraft_clock_shift_s=shift, aircraft_query_utc=shifted.isoformat(),
        brackets_available=position is not None and altitude is not None,
        within_2deg=False, nominal_joint_overlap=False,
        interpretation='all_rays_reselected_scenario_not_measured_clock_error')
    if position is None or altitude is None:
        return row
    ground, bearing = distance_bearing(lat, lon, *position[0])
    delta = (az-bearing+180)%360-180
    geometry = point_geometry(ground, altitude[0][0]*.3048, height, el, delta)
    row.update(geometry, reported_altitude_ft=altitude[0][0], ground_range_m=ground,
        azimuth_difference_deg=delta, within_2deg=abs(delta)<=2)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=ROOT/'data/evidence_packages/N722BD_remaining_GitHub_upload.zip')
    parser.add_argument('--extracted',action='store_true',help='Use committed original members even when the ZIP is present')
    args = parser.parse_args()
    out = ROOT/'results/independent'
    out.mkdir(parents=True, exist_ok=True)
    summary, comparisons, matches, uncertainty, azimuth_samples, clock_scenarios = [], [], [], [], [], []
    audit = []
    with EvidenceSource(ROOT,None if args.extracted else args.zip) as z:
        manifest = list(csv.DictReader((ROOT/'docs/evidence_manifest.csv').open()))
        for row in manifest:
            with z.open(row['repository_target']) as stream:
                actual = digest(stream)
            audit.append(dict(**row, actual_sha256=actual,
                actual_size_bytes=z.getinfo(row['repository_target']).file_size,
                verified=actual == row['sha256'] and z.getinfo(row['repository_target']).file_size == int(row['size_bytes'])))
        write_csv(out/'evidence_audit.csv', audit)
        if not all(r['verified'] for r in audit):
            raise ValueError('Evidence checksum mismatch: analysis stopped')
        custom = custom_functions(z.read('scripts/analyze_3d_n722bd.py').decode())
        flight = pd.read_csv(z.open(manifest[0]['repository_target']))
        flight['time'] = pd.to_datetime(flight.Timestamp, utc=True)
        if flight.time.isna().any():
            raise ValueError('Invalid flight timestamp')
        frame_cols = dict(pos=['latitude', 'longitude'], alt=['altitude'])
        frames = {key: flight.dropna(subset=cols).sort_values('time').drop_duplicates('time')
                  for key, cols in frame_cols.items()}
        # Preserve asynchronous observations rather than forward filling a state vector.
        flight.to_csv(out/'flight_observations.csv', index=False)
        last = {}
        for col in ['latitude', 'longitude', 'altitude', 'ground_speed', 'track', 'vertical_rate']:
            record = flight.dropna(subset=[col]).iloc[-1]
            last[col] = dict(utc=record.time.isoformat(), value=float(record[col]))
        (out/'flight_summary.json').write_text(json.dumps(dict(rows=len(flight),
            position_rows=len(frames['pos']), first_utc=flight.time.min().isoformat(),
            last_utc=flight.time.max().isoformat(), last_observations=last), indent=2))
        for entry in manifest[1:]:
            name = entry['filename']
            print('Decoding', name, flush=True)
            data = z.read(entry['repository_target'])
            radar = NEXRADLevel2File(io.BytesIO(data))
            lat, lon, height = radar.location()
            originals = {}
            custom_count = 0
            for body in custom['messages'](MemoryArchive(data)):
                parsed = custom['parse'](body)
                if parsed:
                    time, az, el, sweep, moments = parsed
                    key = ray_key(time, az, el, sweep)
                    if key in originals:
                        raise ValueError('Duplicate custom ray key')
                    originals[key] = moments
                    custom_count += 1
            times = []
            pykeys = set()
            for i, record in enumerate(radar.radial_records):
                h = record['msg_header']; time = timestamp(record); times.append(time)
                az, el, sweep = h['azimuth_angle'], h['elevation_angle'], h['elevation_number']
                key = ray_key(time, az, el, sweep); pykeys.add(key)
                old = originals.get(key)
                base = dict(volume=name, ray_index=i, utc=time.isoformat(),
                    azimuth_deg=az, elevation_deg=el, elevation_number=sweep)
                row = dict(**base, custom_ray_found=old is not None)
                for tag, field in FIELDS.items():
                    moment = record.get(field); prior = old.get(tag) if old is not None else None
                    row[field+'_pyart_present'] = moment is not None
                    row[field+'_custom_present'] = prior is not None
                    row[field+'_native_gates'] = len(moment['data']) if moment else 0
                    row[field+'_raw_mismatches'] = np.nan
                    row[field+'_geometry_equal'] = None
                    row[field+'_max_value_difference'] = np.nan
                    if moment is not None and prior is not None:
                        first, step, raw, scale, offset = prior
                        same = len(raw) == len(moment['data'])
                        row[field+'_geometry_equal'] = (same and
                            abs(first*1000-moment['first_gate']) < 1e-6 and
                            abs(step*1000-moment['gate_spacing']) < 1e-6)
                        if same:
                            row[field+'_raw_mismatches'] = int(np.count_nonzero(raw != moment['data']))
                            row[field+'_mask_mismatches'] = int(np.count_nonzero((raw < 2) != (moment['data'] < 2)))
                            good = (raw >= 2) & (moment['data'] >= 2)
                            row[field+'_max_value_difference'] = float(np.max(np.abs(
                                (raw[good].astype(float)-offset)/scale -
                                (moment['data'][good].astype(float)-moment['offset'])/moment['scale']))) if good.any() else 0.
                comparisons.append(row)
                # Fixed final-position bearing screen retained as a comparison product,
                # explicitly NOT an aircraft position at this radial's time.
                fixed_distance, fixed_bearing = distance_bearing(lat, lon,
                    last['latitude']['value'], last['longitude']['value'])
                if abs((az-fixed_bearing+180)%360-180) <= 2:
                    fixed = dict(**base, ground_range_m=fixed_distance,
                                 reference='last_position_not_contemporaneous')
                    sr = slant_from_ground(fixed_distance, el)
                    for field in FIELDS.values():
                        fixed.update({field+'_'+k:v for k,v in sample(record.get(field), sr).items()})
                    azimuth_samples.append(fixed)
                # No nominal bracketing, bearing or height preselection here.
                # Store every ray for every shift, including unsupported states.
                for shift in (-2., -1., 0., 1., 2.):
                    scenario = dict(**base, **clock_case(frames, time, shift, lat, lon, height, az, el))
                    for field in FIELDS.values():
                        values = sample(record.get(field), scenario['aircraft_slant_range_m']) if scenario['brackets_available'] else dict(status='aircraft_state_unavailable', value=np.nan)
                        scenario.update({field+'_'+key: value for key, value in values.items() if key in ('status', 'value')})
                    clock_scenarios.append(scenario)
                position = interpolate(frames['pos'], pd.Timestamp(time), frame_cols['pos'])
                altitude = interpolate(frames['alt'], pd.Timestamp(time), frame_cols['alt'])
                if position is None or altitude is None:
                    continue
                (airlat, airlon), pleft, pright = position
                (altft,), aleft, aright = altitude
                ground, bearing = distance_bearing(lat, lon, airlat, airlon)
                delta = (az-bearing+180)%360-180
                if abs(delta) > 2:
                    continue
                slant = slant_from_ground(ground, el)
                center = beam_height(slant, el, height)
                low = height_at_ground(ground, el-.5, height)
                high = height_at_ground(ground, el+.5, height)
                geometry = point_geometry(ground, altft*.3048, height, el, delta)
                match = dict(**base, aircraft_latitude=airlat, aircraft_longitude=airlon,
                    reported_altitude_ft=altft, altitude_datum='unverified_assumed_MSL_for_screen',
                    position_before_s=pleft, position_after_s=pright,
                    altitude_before_s=aleft, altitude_after_s=aright,
                    radar_latitude=lat, radar_longitude=lon, radar_height_m_msl=height,
                    ground_range_m=ground, axis_ground_slant_range_m=slant, aircraft_bearing_deg=bearing,
                    azimuth_difference_deg=delta, beam_center_m_msl=center,
                    beam_lower_m_msl=low, beam_upper_m_msl=high,
                    aircraft_minus_beam_m=altft*.3048-center,
                    nominal_vertical_overlap=low <= altft*.3048 <= high,
                    nominal_horizontal_overlap=abs(delta) <= .5,
                    vertical_gap_m=max(0., low-altft*.3048, altft*.3048-high))
                match.update(geometry)
                for field in FIELDS.values():
                    aircraft_sample = sample(record.get(field), geometry['aircraft_slant_range_m'])
                    match.update({field+'_'+k:v for k,v in aircraft_sample.items()})
                    match.update({'axis_'+field+'_'+k:v for k,v in sample(record.get(field), slant).items()})
                    in_gate = (np.isfinite(aircraft_sample['range_m']) and
                        abs(aircraft_sample['range_m']-geometry['aircraft_slant_range_m']) <= aircraft_sample['gate_spacing_m']/2)
                    match[field+'_range_cell_contains_aircraft'] = bool(in_gate)
                    match[field+'_geometric_overlap'] = bool(in_gate and geometry['nominal_joint_overlap'])
                if np.isfinite(match['REF_range_m']):
                    gate_range = match['REF_range_m']
                    half_spacing = match['REF_gate_spacing_m']/2
                    match['REF_range_error_m'] = gate_range-geometry['aircraft_slant_range_m']
                    match['REF_gate_beam_min_m_msl'] = min(beam_height(gate_range+d,el+a,height)
                        for d in (-half_spacing,half_spacing) for a in (-.5,.5))
                    match['REF_gate_beam_max_m_msl'] = max(beam_height(gate_range+d,el+a,height)
                        for d in (-half_spacing,half_spacing) for a in (-.5,.5))
                matches.append(match)
                # All nominal-bearing candidates, without the old 2-km height filter.
                for k in (1., 4/3, 1.5):
                    for width in (.8, 1., 1.2, 1.5):
                        g = point_geometry(ground, altft*.3048, height, el, delta, k, width)
                        for tolerance in (0., 152.4, 304.8):
                            uncertainty.append(dict(**base, effective_earth_radius_factor=k,
                                full_beam_width_deg=width, altitude_tolerance_m=tolerance,
                                cone_lower_m_msl=g['cone_lower_m_msl'], cone_upper_m_msl=g['cone_upper_m_msl'],
                                axis_to_aircraft_angle_deg=g['axis_to_aircraft_angle_deg'],
                                possible_angular_overlap=altitude_interval_overlap(g, altft*.3048, tolerance),
                                interpretation='circular_cone_altitude_interval_scenario_not_measured_uncertainty'))
            summary.append(dict(volume=name, pyart_rays=len(radar.radial_records),
                custom_rays=custom_count, matched_ray_keys=len(pykeys & originals.keys()),
                custom_only_ray_keys=len(originals.keys()-pykeys),
                pyart_only_ray_keys=len(pykeys-originals.keys()), scans=radar.nscans,
                first_utc=min(times).isoformat(), last_utc=max(times).isoformat(),
                radar_latitude=lat, radar_longitude=lon, radar_height_m_msl=height))
            radar.close()
        comp = write_csv(out/'radar_comparison.csv', comparisons)
        sums = write_csv(out/'volume_summary.csv', summary)
        matchframe = write_csv(out/'aircraft_radar_matches.csv', matches)
        write_csv(out/'beam_uncertainty.csv', uncertainty)
        clockframe = pd.DataFrame(clock_scenarios)
        coverage_columns = ['volume', 'ray_index', 'utc', 'aircraft_clock_shift_s',
                            'brackets_available', 'within_2deg', 'nominal_joint_overlap']
        clockframe[coverage_columns].to_csv(out/'clock_ray_coverage.csv', index=False)
        clockframe[clockframe.within_2deg].to_csv(out/'clock_sensitivity.csv', index=False)
        write_csv(out/'clock_sensitivity_summary.csv', [dict(aircraft_clock_shift_s=shift,
            evaluated_rays=len(group), bracket_supported_rays=int(group.brackets_available.sum()),
            within_2deg=int(group.within_2deg.sum()), nominal_joint_overlap=int(group.nominal_joint_overlap.sum()),
            joint_valid_REF=int((group.nominal_joint_overlap & (group.REF_status=='valid')).sum()))
            for shift, group in clockframe.groupby('aircraft_clock_shift_s')])
        write_csv(out/'fixed_final_position_samples.csv', azimuth_samples)
        # WGS84 GeoJSON flight positions: altitude omitted because datum unverified.
        (out/'flight_path.geojson').write_text(json.dumps(dict(type='FeatureCollection',
            features=flight_features(frames['pos']))))
        fig, axes = plt.subplots(3, 1, figsize=(12,9), sharex=True)
        final = flight[flight.time >= pd.Timestamp('2026-11-01T17:30:00Z')]
        for ax, col, unit in zip(axes, ['altitude','ground_speed','vertical_rate'],
                                ['Reported altitude (ft)','Ground speed (kt)','Reported vertical rate (ft/min)']):
            valid = final.dropna(subset=[col]); ax.scatter(valid.time, valid[col], s=2)
            ax.set_ylabel(unit); ax.grid(alpha=.3)
        axes[-1].set_xlabel('UTC, 2026-11-01'); fig.autofmt_xdate(); fig.tight_layout()
        fig.savefig(out/'flight_timeline.png', dpi=130); plt.close(fig)
        (out/'execution.json').write_text(json.dumps(dict(python=platform.python_version(),
            numpy=np.__version__, pandas=pd.__version__, matplotlib=matplotlib.__version__,
            decoder='unmodified Py-ART 2.3.0 low-level NEXRADLevel2File; not full read_nexrad_archive',
            reader_sha256=digest((ROOT/'scripts/vendor/pyart_nexrad_level2.py').open('rb')),
            zip_sha256=digest(args.zip.open('rb')) if not args.extracted and args.zip.exists() else None,
            evidence_source='retained_zip' if not args.extracted and args.zip.exists() else 'committed_original_members',
            interpolation_max_each_side_s=10,
            azimuth_screen_deg=2, nominal_full_width_deg=1,
            altitude_units='ft per supplied analyses; source datum unverified',
            geodesy='WGS84 inverse geodesic; spherical 6371km effective-radius vertical model',
            beam_model='circular angular cone; ground-consistent vertical projections; aircraft-point native gates',
            clock_scenarios='all 48600 rays evaluated independently for each shift; positive queries later FR24 time',
            run_utc=dt.datetime.now(UTC).isoformat()), indent=2))
        print(sums.to_string(index=False))
        print('Matches',len(matchframe),'nominal circular-cone overlap', int(matchframe.nominal_joint_overlap.sum()))


if __name__ == '__main__':
    main()
