"""Summarize generated comparison products without changing source evidence."""
import json
from pathlib import Path
import pandas as pd


def field_summary(c, field):
    """Geometry availability is independent of whether raw arrays can be compared."""
    shared = c.custom_ray_found
    both = shared & c[field+'_pyart_present'] & c[field+'_custom_present']
    geometry = c[field+'_geometry_equal']
    selected = shared & c[field+'_raw_mismatches'].notna()
    values = c.loc[selected, field+'_max_value_difference']
    return dict(compared_native_gates=int(c.loc[selected,field+'_native_gates'].sum()),
        raw_comparable_rays=int(selected.sum()),
        raw_comparison_unavailable_on_shared_moments=int((both & ~selected).sum()),
        raw_gate_mismatches=int(c.loc[selected,field+'_raw_mismatches'].sum()) if selected.any() else None,
        max_value_difference=float(values.max()) if values.notna().any() else None,
        geometry_compared_rays=int((shared & geometry.notna()).sum()),
        geometry_comparison_unavailable_on_shared_moments=int((both & geometry.isna()).sum()),
        geometry_disagreements=int((shared & (geometry==False)).sum()),
        mask_disagreements=int(c.loc[selected,field+'_mask_mismatches'].sum()) if selected.any() else None,
        moment_presence_disagreements_on_shared_rays=int(((c[field+'_pyart_present']!=c[field+'_custom_present']) & shared).sum()))


def main():
    p=Path(__file__).resolve().parents[1]/'results/independent'
    c=pd.read_csv(p/'radar_comparison.csv')
    m=pd.read_csv(p/'aircraft_radar_matches.csv')
    sweeps=c.groupby(['volume','elevation_number']).agg(
        pyart_rays=('utc','size'),custom_rays=('custom_ray_found','sum')).reset_index()
    sweeps['omitted_by_custom']=sweeps.pyart_rays-sweeps.custom_rays
    sweeps.to_csv(p/'sweep_coverage.csv',index=False)
    result=dict(pyart_rays=len(c),custom_rays=int(c.custom_ray_found.sum()),
        omitted_custom_rays=int((~c.custom_ray_found).sum()),
        omitted_custom_percent=float(100*(~c.custom_ray_found).mean()),
        candidate_rays=len(m),nominal_joint_overlap_rays=int(m.nominal_joint_overlap.sum()),
        nominal_joint_valid_REF_rays=int((m.nominal_joint_overlap & (m.REF_status=='valid')).sum()),
        fields={})
    for field in ['REF','VEL','SW']:
        result['fields'][field]=field_summary(c, field)
    (p/'validation_summary.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
