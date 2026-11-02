from pathlib import Path
import pandas as pd,numpy as np,math,datetime
P=Path('/mnt/data')
src=(P/'analyze_3d_n722bd.py').read_text().split('track=pd.read_csv')[0]
exec(src)
df=pd.read_csv(next(P.glob('Flightradar24*.csv')));df['time']=pd.to_datetime(df.Timestamp,utc=True)
# Interpolation only if both bracketing observations are within 10 seconds of sample
track=df.dropna(subset=['latitude','longitude']).sort_values('time').drop_duplicates('time');alts=df.dropna(subset=['altitude']).sort_values('time').drop_duplicates('time')
def interp(t,frame,cols):
 a=frame.time.searchsorted(t)
 if a==0 or a==len(frame):return None
 before,after=frame.iloc[a-1],frame.iloc[a];gap1=(t-before.time).total_seconds();gap2=(after.time-t).total_seconds()
 if gap1>10 or gap2>10:return None
 w=gap1/(gap1+gap2)
 return [float(before[c])*(1-w)+float(after[c])*w for c in cols],max(gap1,gap2)
radlat,radlon=25.611084,-80.412666
rows=[]; counts={'all_radials':0,'with_position':0,'with_altitude':0,'azimuth_matched':0,'beam_intersection':0}
for f in files:
 for body in messages(f):
  v=parse(body)
  if not v:continue
  t,a,e,num,m=v;counts['all_radials']+=1;t=pd.Timestamp(t)
  p=interp(t,track,['latitude','longitude'])
  if p is None:continue
  counts['with_position']+=1
  alt=interp(t,alts,['altitude'])
  if alt is None:continue
  counts['with_altitude']+=1
  (lat,lon),posgap=p;(altft,),altgap=alt
  km,az=distaz(radlat,radlon,lat,lon);delta=((a-az+180)%360)-180
  if abs(delta)>0.6:continue
  counts['azimuth_matched']+=1
  beam_km=math.sqrt(km**2+8495**2+2*km*8495*math.sin(math.radians(e)))-8495
  beam_ft=(beam_km*1000+4)*3.28084
  # altitude reported datum assumed MSL; beam width ~1 degree full width
  halfbeam_ft=km*1000*math.tan(math.radians(.5))*3.28084
  diff=altft-beam_ft
  intersect=abs(diff)<=halfbeam_ft
  if intersect:counts['beam_intersection']+=1
  row={'volume':f.name,'radial_utc':t.isoformat(),'aircraft_lat':lat,'aircraft_lon':lon,'aircraft_alt_ft':altft,'track_max_bracket_s':posgap,'alt_max_bracket_s':altgap,'radar_range_km':km,'radar_azimuth_deg':az,'radial_azimuth_deg':a,'azimuth_difference_deg':delta,'elevation_deg':e,'beam_center_ft_msl_approx':beam_ft,'beam_halfwidth_ft_approx':halfbeam_ft,'aircraft_minus_beam_center_ft':diff,'within_nominal_beam_vertical_extent':intersect}
  for tag,(first,step,vals,scale,offset) in m.items():
   ix=round((km-first)/step)
   if 0<=ix<len(vals):
    raw=int(vals[ix]);row[tag]=round((raw-offset)/scale,2) if raw>=2 else np.nan
  rows.append(row)
out=pd.DataFrame(rows);out.to_csv(P/'N722BD_moving_aircraft_radar_matches.csv',index=False)
print('COUNTS',counts,'rows',len(out))
if len(out):
 print('INTERSECTIONS',out[out.within_nominal_beam_vertical_extent].to_string(index=False,max_rows=20))
 print('CLOSEST',out.assign(absdiff=out.aircraft_minus_beam_center_ft.abs()).sort_values('absdiff').head(15).to_string(index=False))
