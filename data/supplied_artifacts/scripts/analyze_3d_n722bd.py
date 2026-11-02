import bz2,struct,glob,datetime,math,csv
from pathlib import Path
import numpy as np,pandas as pd
P=Path('/mnt/data'); files=sorted(x for x in P.glob('KAMX*') if x.is_file() and x.suffix not in ('.png','.csv'))
def messages(path):
 b=path.read_bytes();o=24
 while o+4<len(b):
  n=abs(struct.unpack_from('>i',b,o)[0]);o+=4
  if n==0 or o+n>len(b):break
  try:d=bz2.decompress(b[o:o+n])
  except Exception:break
  o+=n;k=0
  while k+32<=len(d):
   sz=struct.unpack_from('>H',d,k+12)[0]*2
   if sz<28 or k+sz>len(d):break
   if d[k+15]==31:yield d[k+28:k+sz]
   k+=sz
   if k+16<=len(d) and d[k:k+12]==bytes(12):k+=12
def parse(body):
 if body[:4]!=b'KAMX':return
 ms,day=struct.unpack_from('>IH',body,4);az=struct.unpack_from('>f',body,12)[0];el=struct.unpack_from('>f',body,24)[0];elevnum=body[22]
 n=struct.unpack_from('>H',body,30)[0];ptrs=struct.unpack_from('>'+('I'*min(n,9)),body,32)
 moments={}
 for ptr in ptrs:
  if ptr+28>len(body):continue
  tag=body[ptr:ptr+4]
  if tag not in (b'DREF',b'DVEL',b'DSW '):continue
  bins,first,step=struct.unpack_from('>HHH',body,ptr+8);word=body[ptr+19];scale,offset=struct.unpack_from('>ff',body,ptr+20)
  if not 0<bins<10000 or not 0<step<10000 or not 0<scale<10000 or word not in (8,16):continue
  if ptr+28+bins*(word//8)>len(body):continue
  vals=np.frombuffer(body,dtype=np.uint8,count=bins,offset=ptr+28) if word==8 else np.frombuffer(body,dtype='>u2',count=bins,offset=ptr+28)
  moments[tag.decode().strip()]=(first/1000,step/1000,vals,scale,offset)
 return (datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(days=day-1,milliseconds=ms),az,el,elevnum,moments)
def distaz(lat1,lon1,lat2,lon2):
 a1,a2=map(math.radians,[lat1,lat2]);dl=math.radians(lon2-lon1);da=a2-a1
 a=math.sin(da/2)**2+math.cos(a1)*math.cos(a2)*math.sin(dl/2)**2
 km=6371*2*math.asin(math.sqrt(a));y=math.sin(dl)*math.cos(a2);x=math.cos(a1)*math.sin(a2)-math.sin(a1)*math.cos(a2)*math.cos(dl)
 return km,(math.degrees(math.atan2(y,x))+360)%360
track=pd.read_csv(next(P.glob('Flightradar*.csv')));track['time']=pd.to_datetime(track.Timestamp,utc=True)
# last position and most recent altitude are not necessarily co-temporal
pos=track.dropna(subset=['latitude','longitude']).iloc[-1]; alt=track.dropna(subset=['altitude']).iloc[-1]
radlat,radlon=25.611084,-80.412666
km,az=distaz(radlat,radlon,float(pos.latitude),float(pos.longitude))
print('Last position',pos.Timestamp,pos.latitude,pos.longitude,'radar range km',km,'az',az)
print('Last altitude',alt.Timestamp,alt.altitude)
rows=[]
for f in files:
 print('Reading',f.name,flush=True)
 for body in messages(f):
  parsed=parse(body)
  if not parsed:continue
  t,a,e,num,m=parsed
  if not m:continue
  delta=((a-az+180)%360)-180
  if abs(delta)>0.65:continue
  # 4/3 earth radius beam model; altitude above radar (radar elevation ~4m ASL)
  beam=math.sqrt(km*km+(8495)**2+2*km*8495*math.sin(math.radians(e)))-8495
  row={'volume':f.name,'radial_utc':t.isoformat(),'azimuth_deg':round(a,3),'azimuth_error_deg':round(delta,3),'elevation_deg':round(e,3),'beam_center_m_above_radar':round(beam*1000),'range_km':round(km,3),'elevation_number':num}
  for tag,(first,step,v,scale,offset) in m.items():
   ix=round((km-first)/step)
   if 0<=ix<len(v):
    raw=int(v[ix]);row[tag]=round((raw-offset)/scale,2) if raw>=2 else None
  rows.append(row)
out=P/'N722BD_aircraft_azimuth_radar_samples.csv';pd.DataFrame(rows).to_csv(out,index=False)
print('radials near last aircraft azimuth',len(rows))
if rows:
 d=pd.DataFrame(rows);d['t']=pd.to_datetime(d.radial_utc,utc=True);target=pd.Timestamp(pos.time)
 d['seconds_from_last_position']=(d.t-target).dt.total_seconds().abs();print(d.sort_values('seconds_from_last_position').head(18).to_string(index=False))
 print('moment counts',d[['DREF','DVEL','DSW']].count().to_dict() if all(c in d for c in ['DREF','DVEL','DSW']) else d.columns.tolist())
