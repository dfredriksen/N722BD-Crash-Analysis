from pathlib import Path
import pandas as pd
p=Path(__file__).parent
r=pd.read_csv(p/'N722BD_neighbor_beam_candidates.csv')
rows=[]
for width in (0.8,1.0,1.2,1.5):
 for extra in (0,500,1000):
  gap=(r.aircraft_alt_ft-r.beam_center_ft).abs()-r.beam_halfwidth_ft*width-extra
  rows.append(dict(full_beam_width_deg=width,extra_vertical_uncertainty_ft=extra,overlapping_candidates=int((gap<=0).sum()),total_candidates=len(r),minimum_signed_gap_ft=round(gap.min())))
pd.DataFrame(rows).to_csv(p/'N722BD_beam_sensitivity.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
