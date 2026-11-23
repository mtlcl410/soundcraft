"""Transient pair in the installed Microsoft Windows MIDI Services loopback transport.
No driver installation, saved configuration, registry edits or service restarts.
Uses the Microsoft WindowsMidiServices.idl COM interfaces and the SDK's runtime JSON.
"""
import contextlib,ctypes as C,json,sys,time,uuid
from pathlib import Path
from manual_run import hw,live_midi,save
class Guid(C.Structure):
    _fields_=[('u32',C.c_uint32),('u16a',C.c_uint16),('u16b',C.c_uint16),('tail',C.c_ubyte*8)]
    @classmethod
    def of(cls,val):return cls.from_buffer_copy(uuid.UUID(val).bytes_le)
def checked(value):
    if value<0:raise OSError(f'Windows MIDI Services HRESULT 0x{value&0xffffffff:08x}')
P=C.c_void_p;PP=C.POINTER(P);W=C.c_wchar_p
def call(obj,index,restype,*argtypes):
    address=C.cast(obj,C.POINTER(C.POINTER(P))).contents[index]
    return C.WINFUNCTYPE(restype,P,*argtypes)(address)
transport='942BF02D-93C0-4EA8-B03E-D51156CA75E1'
@contextlib.contextmanager
def pair(evidence):
    ole=C.windll.ole32
    checked(ole.CoInitializeEx(None,0));base=P();manager=P()
    association='{'+str(uuid.uuid4()).upper()+'}'
    label=association[1:7]
    left='SC G11 '+label+' In';right='SC G11 '+label+' Out'
    def update(section):
        body=json.dumps({'endpointTransportPluginSettings':{'{'+transport+'}':section}})
        response=P()
        try:
            checked(call(manager,4,C.c_long,W,PP)(manager,body,C.byref(response)))
            return json.loads(C.wstring_at(response))
        finally:
            if response:ole.CoTaskMemFree(response)
    init=False;created=False
    try:
        checked(ole.CoCreateInstance(C.byref(Guid.of('2BA15E4E-5417-4A66-85B8-2B2260EFBC84')),None,1,C.byref(Guid.of('EA264200-3328-49E5-8815-73649A8748BE')),C.byref(base)))
        checked(call(base,3,C.c_long,C.POINTER(Guid),PP)(base,C.byref(Guid.of('f19dd642-1809-4497-9eee-f230b11bd6fb')),C.byref(manager)))
        checked(call(manager,3,C.c_long,Guid,P,P)(manager,Guid.of(transport),None,None))
        init=True
        spec={k:dict(name=name,description='Temporary SoundCraft G-11 acceptance relay',uniqueIdentifier='SC'+label+k[-1]) for k,name in [('endpointA',left),('endpointB',right)]}
        answer=update({'create':{association:spec}})
        save(evidence/'create.json',dict(association=association,response=answer,names=[left,right]))
        if answer.get('success') is not True:raise RuntimeError(answer)
        created=True
        yield left,right
    finally:
        if created:
            try:
                answer=update({'remove':[association]})
                save(evidence/'remove.json',answer)
            finally:
                if init:call(manager,5,C.c_long)(manager);init=False
        if init:call(manager,5,C.c_long)(manager)
        if manager:call(manager,2,C.c_ulong)(manager)
        if base:call(base,2,C.c_ulong)(base)
        ole.CoUninitialize()
def smoke(d):
    d.mkdir(exist_ok=False)
    with pair(d) as (a,b):
        time.sleep(2)
        with live_midi(tx_name=a,rx_name=b) as (tx,rx,ports):
            delays=[]
            for _ in range(100):
                now=time.perf_counter_ns()
                tx.send_message([248])
                stamp,msg,_=rx.get(timeout=.25)
                assert msg==(248,)
                delays.append((stamp-now)/1e6);time.sleep(.01)
            time.sleep(.05)
            assert rx.empty()
            save(d/'virtual-wire.json',dict(ports=ports,delay_ms=delays))
if __name__=='__main__':smoke(hw/'runs'/sys.argv[1])

