"""Summarize generated comparison products without changing source evidence."""
import json
from pathlib import Path
import pandas as pd


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
        candidate_rays=len(m),nominal_joint_overlap_rays=int((m.nominal_vertical_overlap&m.nominal_horizontal_overlap).sum()),
        fields={})
    for field in ['REF','VEL','SW']:
        selected=c[field+'_raw_mismatches'].notna()
        result['fields'][field]=dict(compared_native_gates=int(c.loc[selected,field+'_native_gates'].sum()),
            raw_gate_mismatches=int(c[field+'_raw_mismatches'].sum()),
            max_value_difference=float(c[field+'_max_value_difference'].max()),
            geometry_disagreements=int((c.loc[selected,field+'_geometry_equal']==False).sum()),
            mask_disagreements=int(c[field+'_mask_mismatches'].sum()),
            moment_presence_disagreements_on_shared_rays=int(((c[field+'_pyart_present']!=c[field+'_custom_present'])&c.custom_ray_found).sum()))
    (p/'validation_summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
