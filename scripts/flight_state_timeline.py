"""Create position-time aircraft states with explicit, bounded interpolation.

Preserve original reported vertical rate and distinguish altitude-derived rate.
Track interpolation follows the shortest circular arc. No extrapolation.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from run_investigation import interpolate


def main():
    root = Path(__file__).resolve().parents[1]
    p = root/'results/independent'
    df = pd.read_csv(p/'flight_observations.csv')
    df['time'] = pd.to_datetime(df.Timestamp,utc=True,format='ISO8601')
    columns = ['altitude','ground_speed','track','vertical_rate']
    frames = {c:df.dropna(subset=[c]).sort_values('time').drop_duplicates('time') for c in columns}
    # Circular unwrapping changes no source evidence; interpolation output wraps back.
    frames['track'] = frames['track'].copy()
    frames['track']['track'] = np.degrees(np.unwrap(np.radians(frames['track']['track'])))
    positions = df.dropna(subset=['latitude','longitude']).sort_values('time').drop_duplicates('time')
    rows = []
    for _, point in positions.iterrows():
        row = dict(utc=point.time.isoformat(),latitude=point.latitude,longitude=point.longitude,
                   position_status='reported',altitude_datum='unverified')
        for c in columns:
            result = interpolate(frames[c],point.time,[c])
            row[c] = np.nan
            row[c+'_before_s'] = row[c+'_after_s'] = np.nan
            row[c+'_status'] = 'unavailable_within_10s_brackets'
            if result:
                (value,),before,after = result
                row[c] = value % 360 if c == 'track' else value
                row[c+'_before_s'],row[c+'_after_s'] = before,after
                row[c+'_status'] = 'reported' if before == after == 0 else 'interpolated'
        rows.append(row)
    timeline = pd.DataFrame(rows)
    times = pd.to_datetime(timeline.utc,utc=True,format='ISO8601')
    seconds = times.diff().dt.total_seconds()
    timeline['altitude_difference_rate_ft_min'] = (timeline.altitude.diff()/seconds*60).where(
        (seconds > 0)&(seconds <= 10)&timeline.altitude.notna()&timeline.altitude.shift().notna())
    timeline.to_csv(p/'flight_state_timeline.csv',index=False)
    print('Position-time states:',len(timeline),'with bounded altitude:',timeline.altitude.notna().sum())


if __name__ == '__main__':
    main()
