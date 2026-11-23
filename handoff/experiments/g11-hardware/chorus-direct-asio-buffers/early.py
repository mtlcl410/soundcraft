from quality import *
p=Path(__file__).resolve().parent
sys.path.insert(0,str(p.parent/'chorus-direct-asio'))
from assess import matches, mono
t=mono(p.parent/'chorus-direct-asio'/'Crash.wav');rate=44100
tmpl=np.interp(np.arange(0,360),np.arange(len(t))*rate/48000,t)
for case in sys.argv[1:]:
 for f in sorted((p/case).glob('exact-*-in.wav')):
    j=json.loads(f.with_name(f.name.replace('-in.wav','.json')).read_text());buf=j['in']['size'];first=next(t for t,m in j['events'] if m==[248]);x=stereo(f).mean(1);s=matches(x,tmpl);within=np.flatnonzero((np.repeat(np.array(j['in']['ns'])*1.e-9,buf)[:len(s)]>first)&(np.repeat(np.array(j['in']['ns'])*1.e-9,buf)[:len(s)]<first+.1));i=int(within[s[within].argmax()]);lat=(j['in']['ns'][i//buf]/1e9-j['in']['adc'][0]/1e9+i%buf/rate-first)*1000
    print(case,f.name,round(lat,3),round(s[i],3))

