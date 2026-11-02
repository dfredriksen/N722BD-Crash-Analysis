"""Review-only byte-level walker: no production parser/geometry imports.

Explicitly limited to these BZip2-compressed Message-31 Archive II files.
Framing and offsets are cross-checked against the installed ARM Py-ART reader;
this does not authenticate archive origin or radar calibration.
"""
import bz2, struct, datetime as dt, hashlib, json, csv, collections
from pathlib import Path
import numpy as np
from pyart.io.nexrad_level2 import NEXRADLevel2File

from review_context import HERE, REPO

def records(path):
    data=path.read_bytes();offset=24;chunks=[]
    while offset<len(data):
        length=abs(struct.unpack_from('>i',data,offset)[0]);offset+=4
        if not length or offset+length>len(data):raise ValueError('Invalid compressed block length')
        chunks.append(bz2.decompress(data[offset:offset+length]));offset+=length
    stream=b''.join(chunks);pos=12
    while pos<len(stream):
        if len(stream)-pos<16:raise ValueError('Incomplete message header')
        words=struct.unpack_from('>H',stream,pos)[0];kind=stream[pos+3]
        if kind!=31:
            if kind not in (0,2,3,5,13,15,18,32):raise ValueError(f'Unhandled non-radial type {kind}')
            pos+=2432
            continue
        end=pos+2*words+12
        # Preserve a strict check on real moment data below. The final framing
        # length can include a 12-byte legacy pad absent from the stream tail.
        tail_pad=max(0,end-len(stream))
        if tail_pad not in (0,12):raise ValueError(f'Truncated radial: missing {tail_pad} bytes')
        body=memoryview(stream)[pos+16:end]
        if body[:4]!=b'KAMX':raise ValueError('Unexpected station')
        ms,day,aznum=struct.unpack_from('>IHH',body,4)
        az=struct.unpack_from('>f',body,12)[0];el=struct.unpack_from('>f',body,24)[0]
        n=struct.unpack_from('>H',body,30)[0]
        ptrs=struct.unpack_from('>'+n*'I',body,32)
        moments={};site=None
        for ptr in ptrs:
            tag=bytes(body[ptr:ptr+4])
            if tag==b'RVOL':
                lat,lon,height,feed=struct.unpack_from('>ffhH',body,ptr+8)
                site=(lat,lon,height+feed)
            if tag not in (b'DREF',b'DVEL',b'DSW '):continue
            bins,first,spacing=struct.unpack_from('>Hhh',body,ptr+8)
            bits=body[ptr+19];scale,bias=struct.unpack_from('>ff',body,ptr+20)
            if bits not in (8,16):raise ValueError('Unsupported word size')
            if ptr+28+bins*(bits//8)>len(body):raise ValueError('Moment exceeds body')
            raw=np.frombuffer(body,dtype='u1' if bits==8 else '>u2',count=bins,offset=ptr+28)
            moments[tag[1:].decode().strip()]=dict(raw=raw,first=first,spacing=spacing,scale=scale,offset=bias)
        yield dict(ms=ms,day=day,aznum=aznum,az=az,el=el,sweep=body[22],moments=moments,site=site,tail_pad=tail_pad)
        pos=min(end,len(stream))
    if pos!=len(stream):raise ValueError('Unconsumed/overrun bytes')

def main():
    summaries=[];metadata=[]
    for path in sorted((REPO/'data/radar/KAMX').iterdir()):
        print('Independent decode',path.name,flush=True)
        native=NEXRADLevel2File(str(path));counts=collections.Counter();rays=0
        for i,r in enumerate(records(path)):
            p=native.radial_records[i];h=p['msg_header'];rays+=1
            counts['declared_tail_pad_bytes']+=r['tail_pad']
            assert (r['ms'],r['day'],r['aznum'],r['az'],r['el'],r['sweep'])==(
                h['collect_ms'],h['collect_date'],h['azimuth_number'],h['azimuth_angle'],h['elevation_angle'],h['elevation_number'])
            assert r['site']==native.location()
            for field in ['REF','VEL','SW']:
                assert (field in r['moments'])==(field in p)
                if field not in p:continue
                a=r['moments'][field];b=p[field]
                assert (a['first'],a['spacing'],a['scale'],a['offset'])==(
                    b['first_gate'],b['gate_spacing'],b['scale'],b['offset'])
                assert np.array_equal(a['raw'],b['data'])
                counts[field+'_gates']+=len(a['raw'])
                counts[field+'_raw_0']+=int((a['raw']==0).sum())
                counts[field+'_raw_1']+=int((a['raw']==1).sum())
            time=dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(days=r['day']-1,milliseconds=r['ms'])
            metadata.append(dict(volume=path.name,ray_index=i,utc=time.isoformat(),
                azimuth_deg=r['az'],elevation_deg=r['el'],elevation_number=r['sweep']))
        assert rays==len(native.radial_records)
        summaries.append(dict(volume=path.name,rays=rays,site=native.location(),**counts))
        native.close()
    with (HERE/'independent_rays.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=metadata[0].keys());w.writeheader();w.writerows(metadata)
    (HERE/'independent_decoder.json').write_text(json.dumps(summaries,indent=2))
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
