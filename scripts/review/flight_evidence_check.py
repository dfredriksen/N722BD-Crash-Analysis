"""Source-reported late altitude sequence; no claim of physical vertical rate.

Use source altitude observations only. The endpoint difference is a calculation
from a provider series, not independent corroboration of the vertical-rate field.
"""
import json
import pandas as pd
from review_context import HERE, REPO


def main():
    raw=pd.read_csv(next((REPO/'data/flight_tracking').glob('*.csv')))
    raw['time']=pd.to_datetime(raw.Timestamp,utc=True)
    altitude=raw.dropna(subset=['altitude']).sort_values('time').drop_duplicates('time')
    late=altitude[altitude.time>=pd.Timestamp('2026-11-01T17:40:00Z')]
    plateau=late[late.altitude==35000.].iloc[-1]
    first_low=late[late.altitude==8750.].iloc[0]
    descent=late[(late.time>=plateau.time)&(late.time<=first_low.time)]
    changes=descent.altitude.diff().dropna()
    elapsed=(first_low.time-plateau.time).total_seconds()
    tail=late[late.time>=first_low.time]
    rates=raw.dropna(subset=['vertical_rate'])
    coincident=rates[(rates.time>=tail.time.min())&(rates.time<=tail.time.max())]
    result=dict(source='preserved FR24 CSV; source units inherited and altitude datum unverified',
        last_reported_35000ft_utc=plateau.Timestamp, first_reported_8750ft_utc=first_low.Timestamp,
        reported_altitude_difference_ft=float(first_low.altitude-plateau.altitude),
        elapsed_s=elapsed, endpoint_difference_ft_min=float((first_low.altitude-plateau.altitude)/elapsed*60),
        altitude_observations_in_interval=len(descent), positive_steps=int((changes>0).sum()),
        negative_steps=int((changes<0).sum()), unchanged_steps=int((changes==0).sum()),
        largest_altitude_observation_gap_s=float(descent.time.diff().dt.total_seconds().max()),
        final_repeated_altitude_observations=len(tail), final_plateau_duration_s=float((tail.time.max()-tail.time.min()).total_seconds()),
        contemporaneous_reported_vertical_rate_count=len(coincident),
        contemporaneous_reported_vertical_rate_min_ft_min=float(coincident.vertical_rate.min()) if len(coincident) else None,
        contemporaneous_reported_vertical_rate_max_ft_min=float(coincident.vertical_rate.max()) if len(coincident) else None,
        interpretation='A decreasing provider-reported altitude sequence; rates and final plateau are not a verified aircraft trajectory, level-off or impact state')
    descent[['Timestamp','latitude','longitude','altitude']].to_csv(HERE/'reported_descent_observations.csv',index=False)
    (HERE/'flight_evidence_check.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
