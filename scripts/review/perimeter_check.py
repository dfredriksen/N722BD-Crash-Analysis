"""Geographic diagnostics only: no claim that any restriction was operative.

Center and 1-NM proposed geometry from FAA NPRM 2026-17957, page 3 (PDF p2).
No property boundary or historical operational NOTAM is present in the PR.
"""
import json,math
from pathlib import Path
import pandas as pd
from scipy.optimize import minimize_scalar
from pyproj import Geod
from scientific_challenges import vincenty

from review_context import HERE, REPO
G=Geod(ellps='WGS84')

def segment_distance_lower_bound(endpoint_a, endpoint_b, length):
    """Triangle-inequality bound, valid even if a long segment crosses the circle."""
    return max(0., (endpoint_a+endpoint_b-length)/2)


def main():
    lat=26+40/60+37/3600;lon=-(80+2/60+16/3600)
    raw=pd.read_csv(next((REPO/'data/flight_tracking').glob('*.csv')))
    p=raw.dropna(subset=['latitude','longitude']).copy()
    p['time']=pd.to_datetime(p.Timestamp,utc=True)
    p=p.sort_values('time').drop_duplicates('time')
    _,_,d=G.inv([lon]*len(p),[lat]*len(p),p.longitude,p.latitude)
    p['distance_m']=d;p['distance_NM']=p.distance_m/1852
    p['outside_proposed_1NM_by_m']=p.distance_m-1852
    p[['Timestamp','latitude','longitude','altitude','distance_m','distance_NM','outside_proposed_1NM_by_m']].to_csv(HERE/'perimeter_point_distances.csv',index=False)
    closest=p.loc[p.distance_m.idxmin()]
    vd,az=vincenty(lat,lon,closest.latitude,closest.longitude)
    # Minimize distance along only supported <=20-second geodesic segments.
    best=(float(closest.distance_m),closest.Timestamp,closest.Timestamp)
    pts=list(p.itertuples())
    for a,b in zip(pts,pts[1:]):
        if (b.time-a.time).total_seconds()>20:continue
        bearing,_,length=G.inv(a.longitude,a.latitude,b.longitude,b.latitude)
        if segment_distance_lower_bound(a.distance_m,b.distance_m,length)>=best[0]:continue
        def distance_at(fraction):
            xx,yy,_=G.fwd(a.longitude,a.latitude,bearing,length*fraction)
            return G.inv(lon,lat,xx,yy)[2]
        r=minimize_scalar(distance_at,bounds=(0,1),method='bounded')
        if r.fun<best[0]:best=(float(r.fun),a.Timestamp,b.Timestamp)
    result=dict(source='https://public-inspection.federalregister.gov/2026-17957.pdf',
        source_status='NPRM proposed geometry; not evidence of operative restrictions on 2026-11-01',
        reference_center_lat=lat,reference_center_lon=lon,reference_radius_m=1852.,
        closest_reported_position=dict(utc=closest.Timestamp,latitude=float(closest.latitude),longitude=float(closest.longitude),
            distance_m=float(closest.distance_m),distance_NM=float(closest.distance_NM)),
        independent_vincenty_distance_difference_m=float(vd-closest.distance_m),
        minimum_on_supported_geodesic_segments_m=best[0],bracketing_utc=[best[1],best[2]],
        property_perimeter_reproducible=False,historical_TFR_active_verified=False,
        interpretation='Distance to a proposed circular reference only; no conclusion about intent, compliance, or unobserved intervals')
    (HERE/'perimeter_audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
