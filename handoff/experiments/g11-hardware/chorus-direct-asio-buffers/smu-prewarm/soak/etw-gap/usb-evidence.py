"""Match this machine's enumerated Model 12 port path to the USB audio endpoints."""
from pathlib import Path
import bisect,collections,json,sys
tag=sys.argv[1]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def events(p):
    for line in Path(p).open(encoding='utf-8-sig'):
        t,k,fields=line.rstrip('\r\n').split('\t',2)
        yield int(t),int(k),dict(item.split('=',1) for item in fields.split() if '=' in item)
loc=next(x['Data'][0] for x in read('model12-location.json') if x['KeyName']=='DEVPKEY_Device_LocationPaths')
import re
route=tuple(int(x) for x in re.findall(r'#USB\((\d+)\)',loc))
schema=list(events(f'native-usb-schemas-{tag}.tsv'))
def matching_path(d):
    # The display uses decimal for this field and hex for single scalar TDH fields.
    return 'PortPath' in d and tuple(int(v) for v in d['PortPath'].split('.') if int(v))==route
devices={d['fid_UsbDevice'] for _,k,d in schema if k==200005 and matching_path(d)}
assert len(devices)==1,(route,devices)
device=devices.pop()
ep={d['fid_PipeHandle']:d for _,k,d in schema if k==200006 and d.get('fid_UsbDevice')==device}
slots=sorted({d.get('fid_SlotId') for _,k,d in schema if k==100004 and (d.get('fid_UsbDevice')==device or matching_path(d)) and d.get('fid_SlotId')})
assert ep and slots,(device,ep,slots)
if tag=='usbprobe':
    print('route',route,'pipes',len(ep),'slot',slots,[(k,d.get('fid_bEndpointAddress')) for k,d in ep.items()]);quit()
focus=list(events(f'native-usb-{tag}.tsv'))
bins=collections.defaultdict(list); xh=collections.defaultdict(list)
for t,k,d in focus:
    if k in (200030,200031) and d.get('fid_UsbDevice')==device:
        bins[(d.get('fid_PipeHandle'),k)].append((t,d))
    if k in (100041,100042,100043,100044,100045) and d.get('fid_SlotId') in slots:
        xh[(d.get('fid_EndpointContextIndex'),k)].append(t)
def code(d,key):
    return int(d[key],16) if key in d else None
def mill(x):return round(x/1e6,4)
g=read(f'gaps-{tag}.json');p=read(f'partition-{tag}.json');details=[]
for (serial,lo,hi,delta),d in zip(g['rows'],p['details']):
    assert serial==d['serial']
    wake=[w[0] for w in d['ready'] if 0<=w[0]<=delta]
    when=lo+round(1e6*(wake[-1] if wake else delta))
    pipes=[]
    for (pipe,key),data in bins.items():
        if key!=200031:continue
        ts=[v[0] for v in data]
        first,last=bisect.bisect_left(ts,lo),bisect.bisect_right(ts,hi)
        before=bisect.bisect_right(ts,when)-1; narrow=data[max(0,first-1):min(len(ts),last+1)]
        candidates=[(q[0]-a[0],a[0],q[0]) for a,q in zip(narrow,narrow[1:]) if a[0]<=hi and q[0]>=lo]
        descriptor=ep.get(pipe,{})
        addr=code(descriptor,'fid_bEndpointAddress')
        errors=[v for _,v in narrow if any((code(v,f) or 0)!=0 for f in ('fid_IRP_NtStatus','fid_URB_Hdr_Status','fid_URB_ErrorCount'))]
        if not narrow:continue
        pipes.append(dict(address=(hex(addr) if addr is not None else None),pipe=pipe,
            completions_in_gap=last-first,largest_completion_spacing_ms=mill(max(candidates)[0]) if candidates else None,
            before_ready_ms=mill(when-ts[before]) if before>=0 and when-ts[before]<20e6 else None,
            after_ready_ms=mill(ts[before+1]-when) if before+1<len(ts) and ts[before+1]-when<20e6 else None,
            bytes=sorted({code(v,'fid_URB_TransferBufferLength') for _,v in narrow if 'fid_URB_TransferBufferLength' in v}),
            status_fields=sorted(set.intersection(*(set(v) for _,v in narrow))&{'fid_IRP_NtStatus','fid_URB_Hdr_Status','fid_URB_ErrorCount'}),
            status_errors=len(errors)))
    per_xhci={}
    for (index,key),ts in xh.items():
        n=bisect.bisect_right(ts,hi)-bisect.bisect_left(ts,lo)
        if n:per_xhci[f'{index}/{key}']=n
    details.append(dict(serial=serial,gap_ms=delta,ready_reference_ms=wake[-1] if wake else None,pipes=pipes,xhci_event_counts=per_xhci))
out=dict(port_path=route,ucx_device=device,xhci_slots=slots,
    endpoints=[dict(pipe=pipe,address=d.get('fid_bEndpointAddress'),attributes=d.get('fid_bmAttributes')) for pipe,d in ep.items()],
    focus_count=len(focus),details=details)
Path(f'usb-evidence-{tag}.json').write_text(json.dumps(out,indent=2))
print('slot',slots,'endpoints',out['endpoints'],'longest',details[0])
