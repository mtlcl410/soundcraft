from partition import *
def meter(folder):
 p=d/folder
 w=wire(p);a=Audio(p/'loop')
 out=[]
 for z,sc,n,f in w:
  x=[v for i in range(2) if (v:=a.find(z+5,i,ref))]
  t,c=max(x,key=lambda v:abs(v[1]),default=(0,0))
  out.append(dict(first_frame=f,pieces=n,wire_range_ms=sc,windows_render_ms=round((t-z-5)*1000,3) if abs(c)>.9 else None,match=round(c,5)))
 return out
if __name__=='__main__':
 for folder in sys.argv[1:]:
  print(folder,meter(folder))
