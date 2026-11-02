"""Review-only geometry and all-ray sensitivity audit; no production imports.

Position/altitude/clock perturbations are diagnostic assumptions, not measured
error distributions. Circular-cone results are another explicit beam model.
"""
import json,math
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Geod
from pyart.io.nexrad_level2 import NEXRADLevel2File

from review_context import HERE, REPO
G=Geod(ellps='WGS84');R=6371000.

def vincenty(lat1,lon1,lat2,lon2):
    a=6378137.;f=1/298.257223563;b=a*(1-f)
    u1=math.atan((1-f)*math.tan(math.radians(lat1)));u2=math.atan((1-f)*math.tan(math.radians(lat2)))
    su1,cu1,su2,cu2=math.sin(u1),math.cos(u1),math.sin(u2),math.cos(u2)
    L=math.radians(lon2-lon1);lam=L
    for _ in range(100):
        sl,cl=math.sin(lam),math.cos(lam)
        ss=math.hypot(cu2*sl,cu1*su2-su1*cu2*cl)
        if ss==0:return 0.,0.
        cs=su1*su2+cu1*cu2*cl;sigma=math.atan2(ss,cs)
        sa=cu1*cu2*sl/ss;c2a=1-sa*sa
        c2s=cs-2*su1*su2/c2a if c2a else 0.
        C=f/16*c2a*(4+f*(4-3*c2a));old=lam
        lam=L+(1-C)*f*sa*(sigma+C*ss*(c2s+C*cs*(-1+2*c2s*c2s)))
        if abs(lam-old)<1e-12:break
    else:raise ValueError('Vincenty did not converge')
    u2p=c2a*(a*a-b*b)/(b*b)
    A=1+u2p/16384*(4096+u2p*(-768+u2p*(320-175*u2p)))
    B=u2p/1024*(256+u2p*(-128+u2p*(74-47*u2p)))
    ds=B*ss*(c2s+B/4*(cs*(-1+2*c2s*c2s)-B/6*c2s*(-3+4*ss*ss)*(-3+4*c2s*c2s)))
    dist=b*A*(sigma-ds)
    az=math.degrees(math.atan2(cu2*math.sin(lam),cu1*su2-su1*cu2*math.cos(lam)))%360
    return dist,az

def interpolate(frame,cols,query,maxgap):
    t=frame.t.to_numpy(dtype='int64');q=np.asarray(query,dtype=np.int64)
    ix=np.searchsorted(t,q);safe=np.clip(ix,0,len(t)-1)
    exact=t[safe]==q;left=np.clip(ix-1,0,len(t)-1);right=safe
    before=(q-t[left])/1e9;after=(t[right]-q)/1e9
    ok=exact|((ix>0)&(ix<len(t))&(before>=0)&(after>=0)&(before<=maxgap)&(after<=maxgap))
    denom=(t[right]-t[left]).astype(float);denom[denom==0]=1
    w=(q-t[left])/denom
    result=[]
    for col in cols:
        x=frame[col].to_numpy(float);value=x[left]+w*(x[right]-x[left]);value[exact]=x[safe[exact]]
        value[~ok]=np.nan;result.append(value)
    return result,ok

def main():
    raw=pd.read_csv(next((REPO/'data/flight_tracking').glob('*.csv')))
    raw['t']=pd.to_datetime(raw.Timestamp,utc=True).astype('int64')
    pos=raw.dropna(subset=['latitude','longitude']).sort_values('t').drop_duplicates('t')
    alt=raw.dropna(subset=['altitude']).sort_values('t').drop_duplicates('t')
    reference=pd.read_csv(REPO/'results/independent/aircraft_radar_matches.csv')
    geocheck=[];beamcheck=[]
    for row in reference.itertuples():
        dist,bearing=vincenty(row.radar_latitude,row.radar_longitude,row.aircraft_latitude,row.aircraft_longitude)
        geocheck.append(dict(utc=row.utc,distance_difference_m=dist-row.ground_range_m,
            bearing_difference_deg=(bearing-row.aircraft_bearing_deg+180)%360-180))
        radius=R*4/3;theta=dist/radius;e=math.radians(row.elevation_deg)
        exact_lower=radius*(math.cos(e-math.radians(.5))/math.cos(e-math.radians(.5)+theta)-1)+row.radar_height_m_msl
        h=row.reported_altitude_ft*.3048-row.radar_height_m_msl
        x=(radius+h)*math.sin(theta);z=(radius+h)*math.cos(theta)-radius
        elevation=math.atan2(z,x);actual_slant=math.hypot(x,z)
        daz=math.radians(row.azimuth_difference_deg)
        separation=math.degrees(math.acos(np.clip(math.sin(e)*math.sin(elevation)+math.cos(e)*math.cos(elevation)*math.cos(daz),-1,1)))
        beamcheck.append(dict(utc=row.utc,ray_index=row.ray_index,
            production_ground_consistent_lower_m=row.beam_lower_m_msl,lower_at_fixed_ground_distance_m=exact_lower,
            difference_m=row.beam_lower_m_msl-exact_lower,
            point_slant_difference_m=row.aircraft_slant_range_m-actual_slant,
            angular_difference_deg=row.axis_to_aircraft_angle_deg-separation,
            pr_axis_slant_m=row.axis_ground_slant_range_m,aircraft_point_slant_m=actual_slant,
            aircraft_apparent_elevation_deg=math.degrees(elevation),axis_to_aircraft_angle_deg=separation,
            production_joint_overlap=bool(row.nominal_joint_overlap),
            circular_half_power_overlap=separation<=.5))
    pd.DataFrame(geocheck).to_csv(HERE/'geodesic_check.csv',index=False)
    pd.DataFrame(beamcheck).to_csv(HERE/'beam_geometry_check.csv',index=False)
    cases=[dict(name='nominal')]
    cases += [dict(name=f'clock_{s:+g}s',shift=s) for s in [-10,-5,-2,-1,1,2,5,10]]
    cases += [dict(name=f'k_{k:g}',k=k) for k in [1.,1.5]]
    cases += [dict(name=f'beam_{w:g}deg',width=w) for w in [.8,1.2,1.5]]
    cases += [dict(name=f'altitude_bias_{h:+g}m',bias=h) for h in [-304.8,-152.4,152.4,304.8]]
    cases += [dict(name=f'position_{d}m_bearing_{b}',displace=d,direction=b) for d in [100,500,1000] for b in range(0,360,45)]
    cases += [dict(name=f'max_bracket_{gap:g}s',gap=gap) for gap in [.5,1,5]]
    cases += [dict(name='remove_repeated_8750ft',drop8750=True),dict(name='positions_every_5th',stride=5)]
    cases += [dict(name=f'joint_clock_{s:+g}_alt_{h:+g}_k_{k:g}',shift=s,bias=h,k=k)
              for s in [-2,2] for h in [-304.8,304.8] for k in [1.,1.5]]
    totals={c['name']:dict(c,bracket_supported_rays=0,within_2deg=0,legacy_fixed_slant_rectangular_joint=0,circular_joint=0,
        legacy_fixed_slant_rectangular_joint_REF_valid=0,circular_joint_REF_valid=0) for c in cases}
    examples=[];target_cases=[]
    stored_clock=pd.read_csv(REPO/'results/independent/clock_ray_coverage.csv')
    stored_keys={(r.volume,r.ray_index,r.aircraft_clock_shift_s) for r in stored_clock.itertuples()}
    newly_supported=[]; clock_checks=[]
    for path in sorted((REPO/'data/radar/KAMX').iterdir()):
        radar=NEXRADLevel2File(str(path));rr=radar.radial_records
        q=np.array([(r['msg_header']['collect_date']-1)*86400000000000+r['msg_header']['collect_ms']*1000000 for r in rr],dtype=np.int64)
        az=np.array([r['msg_header']['azimuth_angle'] for r in rr]);el=np.radians([r['msg_header']['elevation_angle'] for r in rr])
        site_lat,site_lon,site_h=radar.location()
        for case in cases:
            shift=case.get('shift',0);gap=case.get('gap',10);radius=R*case.get('k',4/3);half=math.radians(case.get('width',1)/2)
            af=alt[alt.altitude!=8750] if case.get('drop8750') else alt
            pf=pos.iloc[::case.get('stride',1)]
            (lat,lon),pok=interpolate(pf,['latitude','longitude'],q+int(shift*1e9),gap)
            (height,),hok=interpolate(af,['altitude'],q+int(shift*1e9),gap)
            if 'displace' in case:
                lon,lat,_=G.fwd(lon,lat,np.full(len(lat),case['direction']),np.full(len(lat),case['displace']))
            bearing,_,distance=G.inv(np.full(len(lat),site_lon),np.full(len(lat),site_lat),lon,lat)
            daz=np.radians((az-bearing+180)%360-180);theta=distance/radius
            slant=radius*np.sin(theta)/np.cos(el+theta)
            low=np.sqrt(radius**2+slant**2+2*radius*slant*np.sin(el-half))-radius+site_h
            high=np.sqrt(radius**2+slant**2+2*radius*slant*np.sin(el+half))-radius+site_h
            height=height*.3048+case.get('bias',0)
            valid=pok&hok
            rectangular=valid&(np.abs(daz)<=half)&(height>=low)&(height<=high)
            x=(radius+height-site_h)*np.sin(theta);z=(radius+height-site_h)*np.cos(theta)-radius
            apparent=np.arctan2(z,x);target_slant=np.hypot(x,z)
            cosangle=np.sin(el)*np.sin(apparent)+np.cos(el)*np.cos(apparent)*np.cos(daz)
            circular=valid&(np.arccos(np.clip(cosangle,-1,1))<=half)
            if path.name=='KAMX20261101_174032_V06(2)':
                i=7728
                target_cases.append(dict(case=case['name'],brackets_available=bool(valid[i]),
                    ground_range_m=distance[i],axis_slant_m=slant[i],aircraft_point_slant_m=target_slant[i],
                    aircraft_altitude_m=height[i],azimuth_offset_deg=np.degrees(daz[i]),
                    angular_separation_deg=np.degrees(np.arccos(np.clip(cosangle[i],-1,1))),
                    legacy_fixed_slant_rectangular_gap_m=max(0.,float(low[i]-height[i]),float(height[i]-high[i])),
                    legacy_fixed_slant_rectangular_overlap=bool(rectangular[i]),circular_overlap=bool(circular[i])))
            count=totals[case['name']];count['bracket_supported_rays']+=int(valid.sum())
            count['within_2deg']+=int((valid&(np.abs(daz)<=np.radians(2))).sum())
            count['legacy_fixed_slant_rectangular_joint']+=int(rectangular.sum());count['circular_joint']+=int(circular.sum())
            for i in np.flatnonzero(rectangular|circular):
                moment=rr[i].get('REF');pr_valid=cone_valid=False
                if moment is not None:
                    for rge,kind in [(slant[i],'pr'),(target_slant[i],'cone')]:
                        index=int(np.floor((rge-moment['first_gate'])/moment['gate_spacing']+.5))
                        value=0<=index<len(moment['data']) and moment['data'][index]>1
                        if kind=='pr':pr_valid=bool(value)
                        else:cone_valid=bool(value)
                count['legacy_fixed_slant_rectangular_joint_REF_valid']+=int(rectangular[i] and pr_valid)
                count['circular_joint_REF_valid']+=int(circular[i] and cone_valid)
                values={}
                for field in ('REF','VEL','SW'):
                    mm=rr[i].get(field)
                    values[field+'_value']=np.nan
                    values[field+'_status']='moment_absent'
                    if mm is not None:
                        ix=int(np.floor((target_slant[i]-mm['first_gate'])/mm['gate_spacing']+.5))
                        values[field+'_status']='outside_range'
                        if 0<=ix<len(mm['data']):
                            code=int(mm['data'][ix])
                            values[field+'_status']='valid' if code>1 else 'range_folded' if code==1 else 'below_threshold_or_missing'
                            if code>1:values[field+'_value']=(code-mm['offset'])/mm['scale']
                examples.append(dict(case=case['name'],volume=path.name,ray_index=int(i),
                    utc=pd.Timestamp(q[i],tz='UTC').isoformat(),rectangular=bool(rectangular[i]),circular=bool(circular[i]),
                    axis_range_REF_valid=pr_valid,aircraft_range_REF_valid=cone_valid,
                    axis_to_aircraft_angle_deg=float(np.degrees(np.arccos(np.clip(cosangle[i],-1,1)))),
                    modeled_aircraft_altitude_m=float(height[i]),**values))
            if case['name'] in ('nominal','clock_-2s','clock_-1s','clock_+1s','clock_+2s'):
                stored=stored_clock[(stored_clock.volume==path.name)&(stored_clock.aircraft_clock_shift_s==shift)].sort_values('ray_index')
                assert len(stored)==len(rr)
                assert np.array_equal(stored.brackets_available.to_numpy(),valid)
                assert np.array_equal(stored.within_2deg.to_numpy(),valid&(np.abs(daz)<=np.radians(2)))
                assert np.array_equal(stored.nominal_joint_overlap.to_numpy(),circular)
                clock_checks.append(dict(volume=path.name,shift_s=shift,compared_rays=len(rr),flags_identical=True))
            if case['name'] in ('clock_-2s','clock_-1s','clock_+1s','clock_+2s'):
                near=valid&(np.abs(daz)<=np.radians(2))
                for i in np.flatnonzero(near):
                    if (path.name,int(i),shift) not in stored_keys:
                        newly_supported.append(dict(shift_s=shift,volume=path.name,ray_index=int(i),
                            utc=pd.Timestamp(q[i],tz='UTC').isoformat(),joint_overlap=bool(rectangular[i])))
        radar.close()
    pd.DataFrame(totals.values()).to_csv(HERE/'all_ray_sensitivity.csv',index=False)
    pd.DataFrame(examples).to_csv(HERE/'sensitivity_overlap_examples.csv',index=False)
    pd.DataFrame(clock_checks).to_csv(HERE/'clock_independent_check.csv',index=False)
    pd.DataFrame(newly_supported,columns=['shift_s','volume','ray_index','utc','joint_overlap']).to_csv(HERE/'clock_candidates_not_in_pr_scenarios.csv',index=False)
    pd.DataFrame(target_cases).to_csv(HERE/'target_sensitivity.csv',index=False)
    assert max(abs(r['difference_m']) for r in beamcheck)<1e-4
    assert max(abs(r['point_slant_difference_m']) for r in beamcheck)<1e-4
    assert max(abs(r['angular_difference_deg']) for r in beamcheck)<1e-7
    assert all(r['production_joint_overlap']==r['circular_half_power_overlap'] for r in beamcheck)
    (HERE/'geometry_summary.json').write_text(json.dumps(dict(
        max_WGS84_distance_difference_m=max(abs(r['distance_difference_m']) for r in geocheck),
        max_WGS84_bearing_difference_deg=max(abs(r['bearing_difference_deg']) for r in geocheck),
        nominal=totals['nominal'],case_count=len(cases),
        target=[r for r in beamcheck if '17:44:26.796' in r['utc']]),indent=2))
    print(json.dumps(totals['nominal'],indent=2))

if __name__=='__main__':main()
