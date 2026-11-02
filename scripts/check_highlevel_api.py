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


def main():
    root = Path(__file__).resolve().parents[1]
    out = root/'results/independent'
    api = pd.read_csv(out/'pyart_highlevel_samples.csv')
    api['time'] = pd.to_datetime(api.utc,utc=True,format='ISO8601')
    if api.duplicated(['file','time']).any():
        raise ValueError('Nonunique high-level radial timestamps')
    api=api.set_index(['file','time'])
    rows=[]
    with EvidenceSource(root,root/'data/evidence_packages/N722BD_remaining_GitHub_upload.zip') as z:
        for name in sorted(n for n in z.namelist() if n.startswith('data/radar/KAMX/')):
            r=NEXRADLevel2File(io.BytesIO(z.read(name)))
            for record in r.radial_records:
                h=record['msg_header'];time=timestamp(record)
                key=(Path(name).name,pd.Timestamp(time))
                row=dict(volume=key[0],utc=time.isoformat(),api_ray_found=key in api.index)
                if key in api.index:
                    a=api.loc[key]
                    row['azimuth_difference_deg']=float(a.azimuth_deg-h['azimuth_angle'])
                    row['elevation_difference_deg']=float(a.elevation_deg-h['elevation_angle'])
                    row['radar_height_difference_m']=float(a.radar_alt_m-r.location()[2])
                    row['sample_range_m']=float(a.range_gate_m)
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
    summary=dict(python=platform.python_version(),pyart=pyart.__version__,numpy=np.__version__,
        native_rays=len(result),api_rays=len(api),matched_rays=int(result.api_ray_found.sum()),
        azimuth_max_difference_deg=float(result.azimuth_difference_deg.abs().max()),
        elevation_max_difference_deg=float(result.elevation_difference_deg.abs().max()),
        radar_height_max_difference_m=float(result.radar_height_difference_m.abs().max()),
        fields={field:dict(mask_mismatches=int((~result[field+'_mask_agrees']).sum()),
                 max_value_difference=float(result[field+'_value_difference'].abs().max()),
                 comparable_valid_rays=int(result[field+'_value_difference'].notna().sum())) for field in ['REF','VEL','SW']})
    (out/'pyart_api_validation.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    if summary['matched_rays'] != len(api) or summary['matched_rays'] != len(result):
        raise ValueError('API/native ray coverage mismatch')
    if any(summary[k] > 1e-5 for k in ['azimuth_max_difference_deg','elevation_max_difference_deg','radar_height_max_difference_m']):
        raise ValueError('API/native metadata disagreement')
    if any(v['mask_mismatches'] or v['max_value_difference'] > 1e-5 for v in summary['fields'].values()):
        raise ValueError('API/native sampled-moment disagreement')


if __name__ == '__main__':
    main()
