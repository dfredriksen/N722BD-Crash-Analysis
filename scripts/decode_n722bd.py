import bz2,struct,glob,os,datetime,math
import numpy as np,pandas as pd,matplotlib.pyplot as plt
from pathlib import Path
P=Path('/mnt/data'); files=sorted(x for x in P.glob('KAMX*') if x.is_file() and x.suffix not in ('.png','.csv'))[:3]
def unpack_file(path):
 b=path.read_bytes();o=24
 while o+4<len(b):
  n=abs(struct.unpack_from('>i',b,o)[0]);o+=4
  if n==0 or o+n>len(b):break
  try: d=bz2.decompress(b[o:o+n])
  except Exception:break
  o+=n; k=0
  while k+32<=len(d):
   size=struct.unpack_from('>H',d,k+12)[0]*2
   if size<28 or k+size>len(d):break
   if d[k+15]==31:yield d[k+28:k+size]
   k+=size
   if k+16<=len(d) and d[k:k+12]==bytes(12):k+=12

def radials(path):
 for body in unpack_file(path):
  if body[:4]!=b'KAMX':continue
  tms,day,aznum=struct.unpack_from('>IHH',body,4)
  az=struct.unpack_from('>f',body,12)[0];elevnum=body[22];elev=struct.unpack_from('>f',body,24)[0]
  nblocks=struct.unpack_from('>H',body,30)[0]
  ptrs=struct.unpack_from('>'+('I'*min(nblocks,9)),body,32)
  for ptr in ptrs:
   if ptr+28>len(body) or body[ptr:ptr+4]!=b'DREF':continue
   bins,first,step=struct.unpack_from('>HHH',body,ptr+8);word=body[ptr+19]
   scale,offset=struct.unpack_from('>ff',body,ptr+20)
   if not 0<bins<10000 or not 0<step<10000 or scale==0:continue
   vals=np.frombuffer(body,dtype=np.uint8,count=bins,offset=ptr+28).astype(float) if word==8 else np.frombuffer(body[ptr+28:ptr+28+bins*2],dtype='>u2').astype(float)
   vals[vals<2]=np.nan;vals=(vals-offset)/scale
   yield {'time':datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(days=day-1,milliseconds=tms),'az':az,'elev':elev,'elevnum':elevnum,'range':(first+np.arange(bins)*step)/1000,'dbz':vals}
   break

tracks=pd.read_csv(next(P.glob('Flightradar*.csv')));tracks['time']=pd.to_datetime(tracks.Timestamp,utc=True)
tracks=tracks.dropna(subset=['latitude','longitude'])
radlat,radlon=25.611,-80.413 # overwritten with decoded RVOL location below if possible
results=[]
for file in files:
 rr=list(radials(file));print(file.name,'decoded radials',len(rr),'elevations',sorted(set(round(x['elev'],2) for x in rr))[:20],flush=True)
 if not rr:continue
 # radar lat lon from volume header block
 for body in unpack_file(file):
  ptr=struct.unpack_from('>I',body,32)[0] if len(body)>36 else 0
  if ptr and body[ptr:ptr+4]==b'RVOL':
   radlat,radlon=struct.unpack_from('>ff',body,ptr+8);break
 r0=[x for x in rr if x['elevnum']==1 and np.isfinite(x['dbz']).any()]
 if not r0:continue
 fig,ax=plt.subplots(figsize=(9,8))
 # point samples scatter radar polar-> lat lon; subselect gates for reasonable performance
 xx=[];yy=[];zz=[]
 for r in r0:
  km=r['range'][::8];v=r['dbz'][::8];angle=np.deg2rad(r['az']);north=km*np.cos(angle);east=km*np.sin(angle)
  xx.extend(radlon+east/(111.32*np.cos(np.deg2rad(radlat))));yy.extend(radlat+north/111.32);zz.extend(v)
 xx=np.asarray(xx);yy=np.asarray(yy);zz=np.asarray(zz)
 valid=np.isfinite(zz)&(xx>-81.5)&(xx<-79.3)&(yy>25.2)&(yy<27.4)
 sc=ax.scatter(xx[valid],yy[valid],c=zz[valid],s=3,vmin=-10,vmax=65,cmap='turbo',rasterized=True)
 plt.colorbar(sc,ax=ax,label='Lowest-sweep reflectivity (dBZ)')
 t0=min(r['time'] for r in rr);t1=max(r['time'] for r in rr)
 positions=tracks[(tracks.time>=pd.Timestamp(t0)-pd.Timedelta('5min'))&(tracks.time<=pd.Timestamp(t1)+pd.Timedelta('5min'))]
 ax.plot(positions.longitude,positions.latitude,'k-',lw=1.4,label='FR24 reported positions')
 if len(positions):ax.scatter(positions.longitude.iloc[-1],positions.latitude.iloc[-1],c='white',edgecolors='black',s=45,zorder=10)
 ax.scatter([radlon],[radlat],marker='+',s=120,c='black',label='KAMX radar')
 ax.set(xlim=(-80.8,-79.8),ylim=(25.7,27.0),xlabel='Longitude',ylabel='Latitude',title=f'KAMX lowest sweep / N722BD track\n{file.name} (UTC)')
 ax.legend(loc='upper left',fontsize=8);ax.grid(alpha=.2);fig.tight_layout()
 out=P/(file.name.replace('(','_').replace(')','')+'_reflectivity_overlay.png');fig.savefig(out,dpi=150);plt.close(fig)
 results.append({'file':file.name,'radials':len(rr),'lowest_sweep_radials':len(r0),'radar_lat':radlat,'radar_lon':radlon,'start':t0.isoformat(),'end':t1.isoformat(),'overlay':out.name})
print(pd.DataFrame(results).to_string(index=False))
pd.DataFrame(results).to_csv(P/'N722BD_radar_decode_summary.csv',index=False)
