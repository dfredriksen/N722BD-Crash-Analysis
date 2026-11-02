from pathlib import Path
import pandas as pd,numpy as np,math
P=Path('/mnt/data')
src=(P/'analyze_3d_n722bd.py').read_text().split('track=pd.read_csv')[0]
exec(src)
df=pd.read_csv(next(P.glob('Flightradar24*.csv')));df['time']=pd.to_datetime(df.Timestamp,utc=True)
frames={k:df.dropna(subset=cols).sort_values('time').drop_duplicates('time') for k,cols in {'pos':['latitude','longitude'],'alt':['altitude']}.items()}
def interp(t,frame,cols):
 a=frame.time.searchsorted(t)
 if a==0 or a==len(frame):return None
 before,after=frame.iloc[a-1],frame.iloc[a];d1=(t-before.time).total_seconds();d2=(after.time-t).total_seconds()
 if d1>10 or d2>10 or d1<0 or d2<0:return None
 w=d1/(d1+d2)
 return [float(before[c])*(1-w)+float(after[c])*w for c in cols]
rows=[];count=0
for f in files:
 for body in messages(f):
  v=parse(body)
  if v is None:continue
  t,az,el,en,m=v;t=pd.Timestamp(t);count+=1
  p=interp(t,frames['pos'],['latitude','longitude']);h=interp(t,frames['alt'],['altitude'])
  if p is None or h is None:continue
  km,bearing=distaz(25.611084,-80.412666,*p);delta=((az-bearing+180)%360)-180
  if abs(delta)>2:continue
  center=(math.sqrt(km**2+8495**2+2*km*8495*math.sin(math.radians(el)))-8495)*3280.84+13.12
  half=km*1000*math.tan(math.radians(.5))*3.28084
  d=h[0]-center
  if abs(d)>half+4000:continue
  row=dict(volume=f.name,utc=t.isoformat(),azimuth_offset_deg=round(delta,3),elevation_deg=round(el,3),range_km=round(km,3),aircraft_alt_ft=round(h[0]),beam_center_ft=round(center),beam_halfwidth_ft=round(half),vertical_distance_to_envelope_ft=round(max(0,abs(d)-half)))
  for tag,(first,step,vals,scale,offset) in m.items():
   ix=round((km-first)/step)
   if 0<=ix<len(vals):
    raw=int(vals[ix]);row[tag]=round((raw-offset)/scale,2) if raw>=2 else np.nan
  rows.append(row)
out=pd.DataFrame(rows);out.to_csv(P/'N722BD_neighbor_beam_candidates.csv',index=False)
print('radials parsed',count,'near candidates',len(out))
if len(out):
 print('vertical overlap and abs az <=0.6:',len(out[(out.vertical_distance_to_envelope_ft==0)&(out.azimuth_offset_deg.abs()<=.6)]))
 print('vertical overlap and abs az <=1:',len(out[(out.vertical_distance_to_envelope_ft==0)&(out.azimuth_offset_deg.abs()<=1)]))
 print('vertical overlap and abs az <=2:',len(out[out.vertical_distance_to_envelope_ft==0]))
 print(out.sort_values(['vertical_distance_to_envelope_ft','azimuth_offset_deg']).head(20).to_string(index=False))
