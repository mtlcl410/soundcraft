from quality import *
f=d/'host-256'/'exact-b-out.wav';x=stereo(f);y=stereo(f.with_name('exact-b-in.wav'))
base=quality(x,y);i=np.argmax(abs(y).max(axis=1));start=(i-max(0,base['lag_frames']))//64*64+max(0,base['lag_frames'])
z=y.copy();z[start:start+64]=0;drop=quality(x,z)
z=y.copy();z[start+128,0]+=256;pop=quality(x,z)
assert base['drop_windows']==0 and base['impulse_samples']==0 and drop['drop_windows']>=1 and pop['impulse_samples']>=1
out=dict(baseline_drop_windows=base['drop_windows'],injected_mute_frames=64,injected_drop_windows=drop['drop_windows'],injected_impulse_counts=256,baseline_residual_over_64=base['impulse_samples'],injected_residual_over_64=pop['impulse_samples'])
(d/'detector-controls.json').write_text(json.dumps(out,indent=2));print(out)
