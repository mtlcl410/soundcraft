from assess import mono,matches,here
import numpy as np,json,re,ast,sys
def read(f): return json.loads((here/f).read_text())
def corr(file,rate,tpl):
 x=mono(here/file);s=matches(x,tpl);ix=int(s.argmax());c=float(s[ix]);hits=np.flatnonzero(s>.90)
 return ix-round(200*rate/48000),c,len(np.split(hits,np.flatnonzero(np.diff(hits)>rate*.1)+1)) if len(hits) else 0
def chunk(fr,blocks):
 ends=np.cumsum([b[1] for b in blocks]);i=int(ends.searchsorted(fr,side='right'));return blocks[i],fr-(ends[i]-blocks[i][1])
src=mono(here/'Crash.wav'); ix=np.arange(round(200*44100/48000),round(2600*44100/48000))*48000/44100;tpl=np.interp(ix,np.arange(len(src)),src)
log=(here/'trials.log').read_text(encoding='utf-8-sig',errors='replace')
log2=(here/'desktop.log').read_text(errors='replace')
clocks=[(int(b)-(int(a)+int(c))/2)/1e9 for a,b,c in re.findall(r'WALL_ANCHOR (\d+) (\d+) (\d+)',log)]
marks=[ast.literal_eval(x) for x in re.findall(r'CHORUS_STAMPS (\[[^\]]+\])',log2)]
modes=['boundary-a','later-a','boundary-b','later-b','boundary-c','boundary-d','one-beat']
assert len(marks)==len(modes)==len(clocks),(len(marks),len(modes),len(clocks))
out={}
for mode,delta,st in zip(modes,clocks,marks):
 j=read(mode+'.json');a=read(mode+'-analysis.json'); line=next(x for x in a['wire'] if x.startswith('UM-ONE')); wire=a['wire'][line]
 f8=next(t for t,n,m in j['midi'] if n==line and m[0]==248)
 st=np.array(st)/1e6-delta
 assert abs(st[0]-f8)<.015,(mode,st,f8)
 v=dict(spp=wire['preceding_spp'][-1],ticks=wire['clock_count'],digital_count=a['crash_count'],input_tap_delta_ms=1000*(st[0]-f8),input_to_ui_ms=1000*(st[1]-st[0]),ui_to_start_ms=1000*(st[2]-st[1]),prepare_session_ms=1000*(st[3]-st[2]),queue_to_callback_ms=1000*(st[4]-st[3]),callback_to_render_ms=1000*(st[5]-st[4]),input_to_render_ms=1000*(st[5]-st[0]))
 paths={}
 for name in ['bridgein','asio','']:
  suffix=('-'+name if name else '')+'-main';fr,c,count=corr(mode+suffix+'.wav',44100,tpl);timestamps=read(mode+suffix+'-times.json'); b,i=chunk(fr,timestamps); v[(name or 'main')+'_count']=count
  if count!=1:continue
  if name=='bridgein': paths['b']=b[0]-(b[1]-i)/44100;paths['b_actual']=b[0]
  elif name=='asio': paths['o']=b[0]+i/44100;paths['o_actual']=b[0];paths['dac']=b[2]*1000;paths['adc']=b[3]*1000
  else:paths['m']=b[0]+i/44100
 if a['crash_count'] and mode!='one-beat':
  b,i=chunk(a['crash_recording_frames'][0],j['blocks']);d=b[0]-(b[1]-i)/48000
  v.update(digital_ms=(d-f8)*1000,render_to_digital_ms=(d-st[5])*1000)
  if all(k in paths for k in ['b','o','m']):
   v.update(taps_ms=(paths['b']-d)*1000,bridge_to_output_ms=1000*(paths['o']-paths['b']),observed_fifo_ms=(paths['o_actual']-paths['b_actual'])*1000,output_to_main_ms=(paths['m']-paths['o'])*1000,main_ms=(paths['m']-f8)*1000,digital_to_main_ms=(paths['m']-d)*1000,asio_reported_dac_ms=paths['dac'],asio_reported_adc_ms=paths['adc'])
 out[mode]={k:round(float(val),3) if isinstance(val,(float,np.floating)) else val for k,val in v.items()}
print(json.dumps(out,indent=1));(here/'split.json').write_text(json.dumps(out,indent=2))
