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


def slant_from_ground(ground, elevation, k=4/3):
    radius = 6371000*k
    angle = ground/radius
    return radius*math.sin(angle)/math.cos(math.radians(elevation)+angle)


def beam_height(slant, elevation, site_height, k=4/3):
    radius = 6371000*k
    return math.sqrt(radius**2+slant**2+2*radius*slant*
                     math.sin(math.radians(elevation)))-radius+site_height


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
                low = beam_height(slant, el-.5, height)
                high = beam_height(slant, el+.5, height)
                match = dict(**base, aircraft_latitude=airlat, aircraft_longitude=airlon,
                    reported_altitude_ft=altft, altitude_datum='unverified_assumed_MSL_for_screen',
                    position_before_s=pleft, position_after_s=pright,
                    altitude_before_s=aleft, altitude_after_s=aright,
                    radar_latitude=lat, radar_longitude=lon, radar_height_m_msl=height,
                    ground_range_m=ground, slant_range_m=slant, aircraft_bearing_deg=bearing,
                    azimuth_difference_deg=delta, beam_center_m_msl=center,
                    beam_lower_m_msl=low, beam_upper_m_msl=high,
                    aircraft_minus_beam_m=altft*.3048-center,
                    nominal_vertical_overlap=low <= altft*.3048 <= high,
                    nominal_horizontal_overlap=abs(delta) <= .5,
                    vertical_gap_m=max(0., low-altft*.3048, altft*.3048-high))
                for field in FIELDS.values():
                    match.update({field+'_'+k:v for k,v in sample(record.get(field), slant).items()})
                if np.isfinite(match['REF_range_m']):
                    gate_range = match['REF_range_m']
                    half_spacing = match['REF_gate_spacing_m']/2
                    match['REF_range_error_m'] = gate_range-slant
                    match['REF_gate_beam_min_m_msl'] = min(beam_height(gate_range+d,el+a,height)
                        for d in (-half_spacing,half_spacing) for a in (-.5,.5))
                    match['REF_gate_beam_max_m_msl'] = max(beam_height(gate_range+d,el+a,height)
                        for d in (-half_spacing,half_spacing) for a in (-.5,.5))
                matches.append(match)
                # Retain all near-height candidates; no confidence probabilities implied.
                if match['vertical_gap_m'] < 2000:
                    for shift in (-2.,-1.,0.,1.,2.):
                        shifted = pd.Timestamp(time)+pd.Timedelta(seconds=shift)
                        pp = interpolate(frames['pos'],shifted,frame_cols['pos'])
                        hh = interpolate(frames['alt'],shifted,frame_cols['alt'])
                        scenario = dict(**base,aircraft_clock_shift_s=shift,
                            brackets_available=pp is not None and hh is not None,
                            interpretation='scenario_not_measured_clock_error')
                        if pp is not None and hh is not None:
                            gg,bb=distance_bearing(lat,lon,*pp[0]);ss=slant_from_ground(gg,el)
                            ll=beam_height(ss,el-.5,height);uu=beam_height(ss,el+.5,height)
                            dd=(az-bb+180)%360-180
                            scenario.update(reported_altitude_ft=hh[0][0],ground_range_m=gg,
                                azimuth_difference_deg=dd,vertical_gap_m=max(0.,ll-hh[0][0]*.3048,hh[0][0]*.3048-uu),
                                nominal_joint_overlap=ll<=hh[0][0]*.3048<=uu and abs(dd)<=.5)
                        clock_scenarios.append(scenario)
                    for k in (1., 4/3, 1.5):
                        sr = slant_from_ground(ground, el, k)
                        for width in (.8, 1., 1.2, 1.5):
                            bottom = beam_height(sr, el-width/2, height, k)
                            top = beam_height(sr, el+width/2, height, k)
                            for altitude_tolerance in (0., 152.4, 304.8):
                                uncertainty.append(dict(**base, effective_earth_radius_factor=k,
                                    full_beam_width_deg=width, altitude_tolerance_m=altitude_tolerance,
                                    lower_m_msl=bottom, upper_m_msl=top,
                                    vertical_overlap=bottom-altitude_tolerance <= altft*.3048 <= top+altitude_tolerance,
                                    horizontal_overlap=abs(delta) <= width/2,
                                    interpretation='scenario_not_measured_uncertainty'))
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
        write_csv(out/'clock_sensitivity.csv', clock_scenarios)
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
            run_utc=dt.datetime.now(UTC).isoformat()), indent=2))
        print(sums.to_string(index=False))
        print('Matches',len(matchframe),'nominal vertical and horizontal',
              int((matchframe.nominal_vertical_overlap & matchframe.nominal_horizontal_overlap).sum()))


if __name__ == '__main__':
    main()
