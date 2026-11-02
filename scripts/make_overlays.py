"""Export explicit lon/lat GeoJSON gate footprints and labeled figures.

Footprints are projected angular-cone/range-cell envelopes, not storm boundaries.
WGS84 forward geodesy matches the reconstruction's ground distance model.
GeoJSON third coordinates are omitted because modeled MSL is not ellipsoid height.
"""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pyproj import Geod
from scipy.spatial import ConvexHull
from run_investigation import flight_features
from radar_geometry import beam_height

ROOT = Path(__file__).resolve().parents[1]
GEOD = Geod(ellps='WGS84')


def destination(lat, lon, bearing, distance):
    longitude,latitude,_ = GEOD.fwd(lon,lat,bearing,distance)
    return [longitude,latitude]


def ground_from_slant(slant, elevation, k=4/3):
    e = math.radians(elevation); r = 6371000*k
    return r*math.atan2(slant*math.cos(e), r+slant*math.sin(e))


def gate_footprint(row):
    """Convex projected envelope sampled around a circular cone; display only."""
    az, el, half = np.radians([row.azimuth_deg, row.elevation_deg, .5])
    axis = np.array([np.sin(az)*np.cos(el), np.cos(az)*np.cos(el), np.sin(el)])
    side = np.array([np.cos(az), -np.sin(az), 0.])
    up = np.array([-np.sin(az)*np.sin(el), -np.cos(az)*np.sin(el), np.cos(el)])
    points = []
    for phi in np.linspace(0, 2*np.pi, 72, endpoint=False):
        direction = axis*np.cos(half)+(side*np.cos(phi)+up*np.sin(phi))*np.sin(half)
        bearing = np.degrees(np.arctan2(direction[0], direction[1]))
        elev = np.degrees(np.arctan2(direction[2], np.hypot(*direction[:2])))
        for sign in (-1, 1):
            ground = ground_from_slant(row.REF_range_m+sign*row.REF_gate_spacing_m/2, elev)
            points.append(destination(row.radar_latitude, row.radar_longitude, bearing, ground))
    hull = ConvexHull(points)
    outline = [points[i] for i in hull.vertices]
    return outline+[outline[0]]


def plot_observed_track(ax, positions):
    """Use the GeoJSON segmentation rule for PNGs, including isolated points."""
    positions=positions.sort_values('time').drop_duplicates('time')
    artists=[]
    for feature in flight_features(positions):
        geometry=feature['geometry']
        coordinates=geometry['coordinates']
        if geometry['type']=='Point':
            x,y=[coordinates[0]],[coordinates[1]]
            style='k.'
        else:
            x,y=zip(*coordinates)
            style='k-'
        artists.extend(ax.plot(x,y,style,lw=1,
            label='FR24 positions during sampled rays' if not artists else '_nolegend_'))
    return artists


def main():
    p = ROOT/'results/independent'
    m = pd.read_csv(p/'aircraft_radar_matches.csv')
    flight = pd.read_csv(p/'flight_observations.csv')
    flight['time'] = pd.to_datetime(flight.Timestamp, utc=True)
    positions=flight.dropna(subset=['latitude','longitude']).sort_values('time').drop_duplicates('time')
    features = flight_features(positions)
    (p/'flight_path.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features)))
    for _, row in m.iterrows():
        spacing = row.REF_gate_spacing_m
        if not np.isfinite(row.REF_range_m):
            continue
        corners = gate_footprint(row)
        props = {key: (None if pd.isna(v) else v) for key,v in row.to_dict().items()}
        props.update(geometry_model='WGS84_geodesic_spherical_vertical_k4/3', footprint='convex_projected_1deg_cone_REF_range_cell_display_only',
                     height_reference='modeled_MSL_not_GeoJSON_ellipsoid_altitude')
        features.append(dict(type='Feature',properties=props,
                             geometry=dict(type='Polygon',coordinates=[corners])))
    (p/'radar_flight_overlay.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features),allow_nan=False))
    for volume, rays in m.groupby('volume'):
        fig, axes = plt.subplots(1,2,figsize=(13,6))
        start, end = pd.to_datetime(rays.utc,utc=True,format='ISO8601').agg(['min','max'])
        track = flight[(flight.time >= start)&(flight.time <= end)].dropna(subset=['latitude','longitude'])
        ax = axes[0]
        plot_observed_track(ax,track)
        for _, row in rays.iterrows():
            if not np.isfinite(row.REF_range_m): continue
            x,y=destination(row.radar_latitude,row.radar_longitude,row.azimuth_deg,ground_from_slant(row.REF_range_m,row.elevation_deg))
            ax.scatter(x,y,c=[row.REF_value],vmin=-10,vmax=65,cmap='turbo',s=13)
        color = plt.cm.ScalarMappable(norm=plt.Normalize(-10,65),cmap='turbo')
        fig.colorbar(color,ax=ax,label='Reflectivity at modeled aircraft slant range (dBZ)')
        ax.set(xlabel='Longitude (deg)',ylabel='Latitude (deg)')
        ax.set_aspect(1/math.cos(math.radians(26.5)));ax.grid(alpha=.3);ax.legend(fontsize=7)
        ax=axes[1]; times=pd.to_datetime(rays.utc,utc=True,format='ISO8601')
        ax.scatter(times,rays.reported_altitude_ft*.3048,s=8,c='k',label='Interpolated reported altitude; datum assumed MSL')
        ax.errorbar(times,rays.beam_center_m_msl,
                    yerr=[rays.beam_center_m_msl-rays.beam_lower_m_msl,
                          rays.beam_upper_m_msl-rays.beam_center_m_msl],fmt='.',alpha=.4,
                    label='Vertical projection at aircraft ground range (not joint overlap)')
        ax.set(ylabel='Height (m MSL, modeled)',xlabel='UTC');ax.grid(alpha=.3);ax.legend(fontsize=7)
        fig.suptitle(volume+'\nRays sampled at different times/elevations; proximity does not establish an encounter',fontsize=10)
        fig.autofmt_xdate();fig.tight_layout()
        fig.savefig(p/(volume.replace('(','_').replace(')','')+'_overlay.png'),dpi=130)
        plt.close(fig)
    # Focus figure on the requested event, including all neighboring candidate rays.
    r=m[m.utc.str.contains('17:44:26')].copy()
    fig,ax=plt.subplots(figsize=(9,5))
    ax.errorbar(r.azimuth_difference_deg,r.beam_center_m_msl/.3048,
        yerr=[(r.beam_center_m_msl-r.beam_lower_m_msl)/.3048,
              (r.beam_upper_m_msl-r.beam_center_m_msl)/.3048],fmt='o',color='gray',alpha=.5,label='Vertical projection only')
    sliced = r[r.cone_slice_intersects_bearing]
    for i, (_, row) in enumerate(sliced.iterrows()):
        ax.plot([row.azimuth_difference_deg]*2, [row.cone_lower_m_msl/.3048,row.cone_upper_m_msl/.3048],
            color='tab:blue',lw=5,label='Circular cone at aircraft bearing' if i==0 else '_nolegend_')
    ax.axhline(35000,c='k',label='Reported aircraft altitude; datum assumed MSL')
    ax.set(xlabel='Ray minus aircraft bearing (deg)',ylabel='Modeled height (ft MSL)',
           title='17:44:26 UTC: modeled 1-degree cone and vertical projection\nHalf-power convention; actual beam and altitude datum unverified')
    ax.legend(fontsize=8);ax.grid(alpha=.3);fig.tight_layout();fig.savefig(p/'174426_beam_geometry.png',dpi=140);plt.close(fig)
    # This plot is a sequence of samples, not a simultaneous atmospheric volume.
    fig=plt.figure(figsize=(11,7));ax=fig.add_subplot(111,projection='3d')
    focus=m[pd.to_datetime(m.utc,utc=True,format='ISO8601')>=pd.Timestamp('2026-11-01T17:40:00Z')]
    origin_lat,origin_lon=26.5,-80.4
    def xy(lat,lon):
        az,_,dist=GEOD.inv(origin_lon,origin_lat,lon,lat)
        return dist*math.sin(math.radians(az))/1000,dist*math.cos(math.radians(az))/1000
    x,y=zip(*(xy(r.aircraft_latitude,r.aircraft_longitude) for _,r in focus.iterrows()))
    ax.scatter(x,y,focus.reported_altitude_ft*.3048/1000,c='k',s=8,label='Reported/interpolated aircraft')
    focus = focus[np.isfinite(focus.REF_range_m)]
    radarxy=[destination(r.radar_latitude,r.radar_longitude,r.azimuth_deg,ground_from_slant(r.REF_range_m,r.elevation_deg)) for _,r in focus.iterrows()]
    rx,ry=zip(*(xy(lat,lon) for lon,lat in radarxy))
    heights=[beam_height(r.REF_range_m,r.elevation_deg,r.radar_height_m_msl)/1000 for _,r in focus.iterrows()]
    points=ax.scatter(rx,ry,heights,c=focus.REF_value,cmap='turbo',vmin=-10,vmax=65,s=15)
    fig.colorbar(points,ax=ax,shrink=.6,pad=.1,label='Reflectivity (dBZ)')
    ax.set(xlabel='East of 26.5 N, 80.4 W (km)',ylabel='North (km)',zlabel='Modeled height (km MSL)',
           title='N722BD and neighboring KAMX samples after 17:40 UTC\nSamples vary in time and elevation; aircraft altitude datum unverified')
    ax.legend();fig.tight_layout();fig.savefig(p/'aircraft_radar_3d.png',dpi=140);plt.close(fig)


if __name__ == '__main__':
    main()
