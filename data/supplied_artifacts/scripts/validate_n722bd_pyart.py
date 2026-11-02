"""Independent KAMX Level II validation using ARM Py-ART.
Run in an environment with `conda install -c conda-forge arm_pyart`.
Usage: python validate_n722bd_pyart.py /path/to/KAMX20261101_174548_V06\(1\)
Outputs one CSV with per-ray metadata and moments at ~117.47 km.
"""
import argparse, csv, datetime, pathlib
import numpy as np
import pyart

p=argparse.ArgumentParser();p.add_argument('files',nargs='+');p.add_argument('--output',default='N722BD_pyart_independent_samples.csv')
a=p.parse_args()
fields={'reflectivity':'REF_dBZ','velocity':'VEL_mps','spectrum_width':'SW_mps'}
rows=[]
for path in a.files:
 radar=pyart.io.read_nexrad_archive(path)
 units=radar.time['units']
 try:
  from netCDF4 import num2date
  ts=num2date(radar.time['data'],units,only_use_cftime_datetimes=False,only_use_python_datetimes=True)
 except ImportError:
  raise SystemExit('Install netCDF4 for exact radial timestamps')
 for i in range(radar.nrays):
  dt=ts[i]
  if dt.tzinfo is None:dt=dt.replace(tzinfo=datetime.timezone.utc)
  if not datetime.datetime(2026,11,1,17,35,tzinfo=datetime.timezone.utc)<=dt<=datetime.datetime(2026,11,1,17,57,tzinfo=datetime.timezone.utc):continue
  az=float(radar.azimuth['data'][i]); el=float(radar.elevation['data'][i]);
  # Include all rays near last aircraft position bearing, allowing independent comparison.
  if abs((az-14.769+180)%360-180)>2.0:continue
  row={'file':pathlib.Path(path).name,'utc':dt.isoformat(),'ray_index':i,'azimuth_deg':az,'elevation_deg':el,'range_gate_m':None,'radar_lat':float(radar.latitude['data'][0]),'radar_lon':float(radar.longitude['data'][0]),'radar_alt_m':float(radar.altitude['data'][0])}
  for field,label in fields.items():
   row[label]=''
   if field in radar.fields:
    data=radar.fields[field]['data']; gate=int(np.argmin(abs(radar.range['data']-117467)))
    row['range_gate_m']=float(radar.range['data'][gate]); value=data[i,gate]
    if not np.ma.is_masked(value):row[label]=float(value)
  rows.append(row)
keys=['file','utc','ray_index','azimuth_deg','elevation_deg','range_gate_m','radar_lat','radar_lon','radar_alt_m',*fields.values()]
with open(a.output,'w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
print(f'Wrote {len(rows)} rays to {a.output}; compare timestamps, gate geometry and REF/VEL/SW with custom decoder before making claims.')
