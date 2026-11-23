from common import *
import csv
head=git('follow','rev-parse','HEAD')
dest=ev/f'1669-{head[:8]}'
def log(name):return (dest/f'profile-{name}.log').read_text('utf8')
profiles=json.loads((dest/'profiles.json').read_text())
assert len(profiles)==13 and all(x['head']==head and x['code']==0 for x in profiles)
dj=log('twenty_full_length_dj_tracks')
full=re.search(r'20 tracks, (\d+) eighths, (\d+) outside transitions, p99.9 (\d+) samples; including burst (\d+) samples; (\d+) batched eighths, max signed late beyond wire (-?\d+) samples, earliest vs grid (-?\d+) samples, earliest vs wire (-?\d+) samples',dj)
total,ordinary,p99,group99,notes,late,early,earlywire=map(int,full.groups())
l=log('packet_steps')
onset=re.findall(r'ONSET (\S+) worst_late_samples=(-?\d+) earliest_samples=(-?\d+) missing=(\d+) extra=(\d+) damaged=(\d+) dropouts=(\d+)',l)
packed=re.findall(r'PACKED (\S+) max_wire_samples=(\d+) max_residual_samples=(\d+) earliest_samples=(-?\d+)',l)
assert len(onset)==len(packed)==96 and all(list(map(int,x[3:]))==[0]*4 for x in onset)
w=max(int(x[1]) for x in packed); residual=max(int(x[2]) for x in packed)
assert max(int(x[1]) for x in onset)==209 and min(int(x[2]) for x in onset)==-46
ramp=max(map(float,re.findall(r'RAMP[^\n]+?peak=([\d.]+)',log('ramp_response'))))
peak=int(re.search(r'peak phase (\d+) samples',log('eight_hours_of_clock_flutter')).group(1))
hist=[]
for key in ['has_bounded_unreferenced_events','uncapped_control']:
 name='six_hour_clock_history_'+key
 m=re.search(r'peak_events=(\d+).*?end_publish_p95_us=([\d.]+)',log(name))
 hist.append((m[1],m[2],next(x['peak_working_bytes'] for x in profiles if x['name']==name)/1048576))
with (dest/'slow-predict.csv').open(encoding='utf8') as f:
 data=list(csv.DictReader(f))
a,b=[max(int(row['err_samples']) for row in data if row['event_pulse']==row[key]) for key in ['first_offbeat_pulse','first_beat_pulse']]
detail=(f'The 20-track mix rendered {total:,} eighths exactly once, with complete waveforms and tails. Among {ordinary:,} steady eighths outside transitions and batches, absolute error p99.9 was {p99/48:.3f} ms. In the {notes} batched eighths the largest **positive residual after MIDI arrival** fell from +846 to +{late} sample. The earliest onset against the grid was {early} samples. The 96 single-to-group cases peaked at +209 samples (4.354 ms) of extra delay, with zero missing, repeated or damaged attacks. Across 96 established grouped slowdowns, the maximum absolute residual was {residual} samples. The tests rotate group phase for widths 3, 4, 5 and variable groups.\n\n'
f'The ±8% ramps peaked at {ramp:.4f} ms and the eight-hour jitter simulation peaked at {peak} samples. In the paired six-hour history run, capped/uncapped peak events were {hist[0][0]}/{hist[1][0]}, peak process working sets {hist[0][2]:.1f}/{hist[1][2]:.1f} MiB, and end-of-run publish p95 {hist[0][1]}/{hist[1][1]} µs. History required by recorded takes is retained. The EXT UI regression previously observed an empty status after a refused click. It now displays the refusal reason.')
limits=(f'In this 20-track mix, including batches while still excluding the declared tempo transitions gives {group99/48:.3f} ms p99.9 against the grid. An event already predicted on the grid may precede its F8; one arrived {abs(earlywire)} samples after the predicted onset. Grouped slowdown delivery alone added up to {w/48:.3f} ms. After an abrupt slowdown, audio already delivered to a large device buffer can be late: across 18 configurations, the largest observed positive errors were +{a/48:.3f} ms at the first offbeat and +{b/48:.3f} ms at the first beat. For live use, try 64–256 frames where supported. #1686 tracks one unexplained waveform difference in twelve 256-frame takes. A separate 64-frame capture had 40 near-silent samples.')
save('1669-details.json',dict(detail=detail,limits=limits,history=hist,notes=total,late=late,early=early,wire=earlywire,range_samples=[a,b],ramp=ramp,jitter=peak))
print(detail,limits)

