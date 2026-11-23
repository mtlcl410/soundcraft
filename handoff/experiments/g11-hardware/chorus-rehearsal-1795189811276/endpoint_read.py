import ctypes as c, uuid, json
ole=c.OleDLL("ole32")
p=c.c_void_p
def guid(s):
    return (c.c_ubyte*16).from_buffer_copy(uuid.UUID(s).bytes_le)
def call(obj, i, *types):
    addr=c.cast(obj,c.POINTER(c.POINTER(p))).contents[i]
    return c.WINFUNCTYPE(c.HRESULT,p,*types)(addr)
ole.CoInitialize(None)
enum=p(); dev=p(); vol=p()
ole.CoCreateInstance(c.byref(guid("bcde0395-e52f-467c-8e3d-c4579291692e")),None,1,c.byref(guid("a95664d2-9614-4f35-a746-de8db63617e6")),c.byref(enum))
call(enum,4,c.c_int,c.c_int,c.POINTER(p))(enum,0,1,c.byref(dev))
call(dev,3,p,c.c_uint,p,c.POINTER(p))(dev,c.byref(guid("5cdf2c82-841e-4546-9722-0cf74078229a")),23,None,c.byref(vol))
level=c.c_float(); mute=c.c_int()
call(vol,9,c.POINTER(c.c_float))(vol,c.byref(level))
call(vol,15,c.POINTER(c.c_int))(vol,c.byref(mute))
print(json.dumps(dict(default_multimedia_mute=bool(mute.value),default_multimedia_volume_scalar=level.value)))