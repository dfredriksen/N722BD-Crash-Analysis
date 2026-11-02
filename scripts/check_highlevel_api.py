"""Compare full Py-ART API ray metadata and sampled moments to native records."""
import io
import json
import platform
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
import pyart
from run_investigation import NEXRADLevel2File, timestamp, sample
from evidence_source import EvidenceSource


REQUIRED_METADATA = ['azimuth_deg', 'elevation_deg', 'radar_alt_m',
                     'radar_lat', 'radar_lon', 'range_gate_m', 'ray_index']
METADATA_TOLERANCES = dict(azimuth_difference_deg=1e-5,
    elevation_difference_deg=1e-5, radar_height_difference_m=1e-5,
    radar_latitude_difference_deg=1e-6, radar_longitude_difference_deg=1e-6,
    ray_index_difference=0.)


def validate_api_table(api):
    """Fail closed for required metadata; NaN is permitted only for masked moments."""
    if api.empty or api['file'].isna().any() or api['time'].isna().any():
        raise ValueError('Empty API data or missing file/timestamp')
    if api.duplicated(['file', 'time']).any():
        raise ValueError('Nonunique high-level radial timestamps')
    if not np.isfinite(api[REQUIRED_METADATA].to_numpy(dtype=float)).all():
        raise ValueError('Nonfinite required API metadata')
    if np.isinf(api[['REF_dBZ', 'VEL_mps', 'SW_mps']].to_numpy(dtype=float)).any():
        raise ValueError('Infinite API moment value')


def compare_metadata(a, record, location, ray_index):
    h = record['msg_header']
    native = np.array([h['azimuth_angle'], h['elevation_angle'], *location], dtype=float)
    if not np.isfinite(native).all():
        raise ValueError('Nonfinite native radar metadata')
    lat, lon, height = location
    return dict(azimuth_difference_deg=float(a.azimuth_deg-h['azimuth_angle']),
        elevation_difference_deg=float(a.elevation_deg-h['elevation_angle']),
        radar_height_difference_m=float(a.radar_alt_m-height),
        radar_latitude_difference_deg=float(a.radar_lat-lat),
        radar_longitude_difference_deg=float(a.radar_lon-lon),
        ray_index_difference=float(a.ray_index-ray_index),
        sample_range_m=float(a.range_gate_m))


def validation_summary(result, api_rays):
    """Require complete comparisons before computing maxima; all-masked is null."""
    if result.empty or not result.api_ray_found.all() or len(result) != api_rays:
        raise ValueError('API/native ray coverage mismatch')
    summary = dict(python=platform.python_version(), pyart=pyart.__version__, numpy=np.__version__,
        native_rays=len(result), api_rays=api_rays, matched_rays=int(result.api_ray_found.sum()),
        validation_passed=True, fields={})
    for column, tolerance in METADATA_TOLERANCES.items():
        values = result[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (np.abs(values) > tolerance).any():
            raise ValueError('API/native metadata disagreement: '+column)
        summary[column.replace('_difference', '_max_difference')] = float(np.abs(values).max())
    for field in ['REF', 'VEL', 'SW']:
        masks = result[field+'_mask_agrees']
        values = result[field+'_value_difference']
        maximum = float(values.abs().max()) if values.notna().any() else None
        if masks.isna().any() or not masks.all() or np.isinf(values).any() or (maximum is not None and maximum > 1e-5):
            raise ValueError('API/native sampled-moment disagreement: '+field)
        summary['fields'][field] = dict(mask_mismatches=0, compared_mask_rays=len(masks),
            max_value_difference=maximum, comparable_valid_rays=int(values.notna().sum()))
    return summary


def main():
    root = Path(__file__).resolve().parents[1]
    out = root/'results/independent'
    api = pd.read_csv(out/'pyart_highlevel_samples.csv')
    api['time'] = pd.to_datetime(api.utc,utc=True,format='ISO8601')
    validate_api_table(api)
    api=api.set_index(['file','time'])
    rows=[]
    with EvidenceSource(root,root/'data/evidence_packages/N722BD_remaining_GitHub_upload.zip') as z:
        for name in sorted(n for n in z.namelist() if n.startswith('data/radar/KAMX/')):
            r=NEXRADLevel2File(io.BytesIO(z.read(name)))
            for i, record in enumerate(r.radial_records):
                h=record['msg_header'];time=timestamp(record)
                key=(Path(name).name,pd.Timestamp(time))
                row=dict(volume=key[0],utc=time.isoformat(),api_ray_found=key in api.index)
                if key in api.index:
                    a=api.loc[key]
                    row.update(compare_metadata(a, record, r.location(), i))
                    for field,label in [('REF','REF_dBZ'),('VEL','VEL_mps'),('SW','SW_mps')]:
                        expected=sample(record.get(field),a.range_gate_m)
                        native=expected['value'];actual=a[label]
                        row[field+'_native_status']=expected['status']
                        row[field+'_mask_agrees']=bool(pd.isna(native)==pd.isna(actual))
                        row[field+'_value_difference']=float(actual-native) if pd.notna(native) and pd.notna(actual) else np.nan
                rows.append(row)
            r.close()
    result=pd.DataFrame(rows)
    result.to_csv(out/'pyart_api_comparison.csv',index=False)
    summary=validation_summary(result, len(api))
    (out/'pyart_api_validation.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(json.dumps(summary,indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
