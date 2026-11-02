"""Explicit effective-Earth-radius geometry; not a measured antenna pattern.

WGS84 surface distance is supplied by the caller. The vertical model uses kR,
with the radar height added as a datum offset, consistent with beam_height.
A circular angular cone models the nominal full half-power beamwidth. Neither
its edge nor a gate's half-spacing is a hard physical sensitivity boundary.
"""
import math


def slant_from_ground(ground, elevation, k=4/3):
    radius = 6371000*k
    angle = ground/radius
    return radius*math.sin(angle)/math.cos(math.radians(elevation)+angle)


def beam_height(slant, elevation, site_height, k=4/3):
    radius = 6371000*k
    return math.sqrt(radius**2+slant**2+2*radius*slant*
                     math.sin(math.radians(elevation)))-radius+site_height


def height_at_ground(ground, elevation, site_height, k=4/3):
    return beam_height(slant_from_ground(ground, elevation, k), elevation, site_height, k)


def point_geometry(ground, altitude, site_height, elevation, azimuth_offset, k=4/3, width=1.):
    """Range and angular separation to the aircraft point, in the same kR model."""
    if not all(math.isfinite(x) for x in (ground, altitude, site_height, elevation, azimuth_offset, k, width)):
        raise ValueError('Nonfinite geometry input')
    if ground <= 0 or k <= 0 or not 0 < width < 180:
        raise ValueError('Unsupported geometry domain')
    radius = 6371000*k
    angle = ground/radius
    x = (radius+altitude-site_height)*math.sin(angle)
    z = (radius+altitude-site_height)*math.cos(angle)-radius
    apparent = math.atan2(z, x)
    e = math.radians(elevation)
    daz = math.radians(azimuth_offset)
    dot = math.sin(e)*math.sin(apparent)+math.cos(e)*math.cos(apparent)*math.cos(daz)
    separation = math.degrees(math.acos(max(-1., min(1., dot))))
    # Solve A sin(apparent) + B cos(apparent) >= cos(half-width) for
    # the altitude interval intercepted by the cone at this ground/bearing.
    a, b = math.sin(e), math.cos(e)*math.cos(daz)
    amplitude = math.hypot(a, b)
    threshold = math.cos(math.radians(width/2))
    lower = upper = math.nan
    slice_exists = amplitude >= threshold and b > 0
    if slice_exists:
        middle = math.atan2(a, b)
        half = math.acos(min(1., threshold/amplitude))
        lower = height_at_ground(ground, math.degrees(middle-half), site_height, k)
        upper = height_at_ground(ground, math.degrees(middle+half), site_height, k)
    return dict(aircraft_slant_range_m=math.hypot(x, z),
        aircraft_apparent_elevation_deg=math.degrees(apparent),
        axis_to_aircraft_angle_deg=separation,
        nominal_joint_overlap=separation <= width/2,
        cone_slice_intersects_bearing=slice_exists,
        cone_lower_m_msl=lower, cone_upper_m_msl=upper)


def altitude_interval_overlap(geometry, altitude, tolerance):
    """Possible cone overlap for a bounded altitude scenario; not a probability."""
    return bool(geometry['cone_slice_intersects_bearing'] and
                altitude+tolerance >= geometry['cone_lower_m_msl'] and
                altitude-tolerance <= geometry['cone_upper_m_msl'])
