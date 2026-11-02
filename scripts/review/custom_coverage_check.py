"""Run the preserved custom functions against review-only byte-walker records."""
import ast,datetime,bz2,struct,math,json
from pathlib import Path
import numpy as np
from independent_decode import records

from review_context import HERE, REPO

def main():
    source=(REPO/'data/supplied_artifacts/scripts/analyze_3d_n722bd.py').read_text()
    tree=ast.parse(source);tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
    scope=dict(datetime=datetime,bz2=bz2,struct=struct,np=np,math=math)
    exec(compile(tree,'preserved_custom_parser','exec'),scope)
    results=[]
    for path in sorted((REPO/'data/radar/KAMX').iterdir()):
        old={};body_lengths={}
        for body in scope['messages'](path):
            r=scope['parse'](body)
            if r:
                time,az,el,sweep,moments=r;key=(time,az,el,sweep)
                assert key not in old;old[key]=moments;body_lengths[key]=len(body)
        total=common=missing_sw=0;gate_counts={'REF':0,'VEL':0,'SW':0};raw_diff=0;truncation_examples=[]
        for r in records(path):
            total+=1
            time=datetime.datetime(1970,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(days=r['day']-1,milliseconds=r['ms'])
            key=(time,r['az'],r['el'],r['sweep'])
            if key not in old:continue
            common+=1
            for field,moment in r['moments'].items():
                tag='D'+field
                if field=='SW' and tag not in old[key]:
                    missing_sw+=1
                    if len(truncation_examples)<1:truncation_examples.append(dict(utc=time.isoformat(),custom_body_bytes=body_lengths[key]))
                if tag not in old[key]:continue
                first,step,raw,scale,offset=old[key][tag]
                assert (first*1000,step*1000,scale,offset)==(moment['first'],moment['spacing'],moment['scale'],moment['offset'])
                assert len(raw)==len(moment['raw'])
                raw_diff+=int(np.count_nonzero(raw!=moment['raw']));gate_counts[field]+=len(raw)
        assert common==len(old)
        results.append(dict(volume=path.name,review_byte_walker_rays=total,preserved_custom_rays=len(old),
            matched_custom_rays=common,omitted_by_custom=total-common,missing_SW_on_shared_rays=missing_sw,
            compared_gates=gate_counts,raw_mismatches=raw_diff,truncation_examples=truncation_examples))
        print(path.name,total,len(old),missing_sw,flush=True)
    (HERE/'custom_independent_comparison.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__':main()
