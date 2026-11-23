"""Build one reviewer-accessible #1669 evidence comment from verified profile outputs."""
import argparse
import ast
import base64
import csv
import gzip
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

d = Path(__file__).resolve().parent
ev = d / 'evidence'
ap = argparse.ArgumentParser()
ap.add_argument('folder', type=Path)
ap.add_argument('--status', action='store_true')
ap.add_argument('--ci', default='Hosted CI for this head has not been verified.')
args = ap.parse_args()
folder = args.folder.resolve()
profiles = json.loads((folder / 'profiles.json').read_text(encoding='utf8'))
head = profiles[0]['head']
assert len(profiles) == 13 and all(p['head'] == head and not p['code'] for p in profiles)
by = {p['name']: p for p in profiles}
def log(name):
    return (folder / by[name]['log']).read_text(encoding='utf8')
def must(pattern, text):
    match = re.search(pattern, text)
    if not match:
        raise ValueError(pattern)
    return match
def mifmt(n):
    return f'{n / (1024**2):.1f} MiB'
def sample(x):
    return f'{int(x)/48:.3f}'
def fk(stem):
    return [r for r in profiles if r['name'].startswith(stem)][0]
dj = log('dj_tempos::')
long = log('twenty_full_length_dj_tracks')
ln = must(r'20 tracks, (\d+) eighths, (\d+) outside transitions, p99\.9 (\d+) samples; including burst (\d+) samples; (\d+) batched eighths, wire-relative p99\.9 (\d+) samples; max (\d+) grid events',long).groups()
series = {}
def keyclear(x):
    return re.sub(r'^test \S+ \.\.\. ', '', x)
def collect(text, regex):
    for label, notes in re.findall(regex, text, flags=re.M):
        y=ast.literal_eval(notes)
        if y and isinstance(y[0],list):
            assert all(len(x)==1 for x in y), label
            y=[x[0] for x in y]
        label = keyclear(label)
        if label in series:
            label += ' (second run)'
        assert label not in series, label
        series[label] = y
collect(dj+'\n'+long, r'^(.*?) signed eighth errors \(48 kHz samples\) (\[[^\r\n]+\])')
brk=log('brake::')
collect(brk, r'^(.*?(?:brake \d+ |steady (?:\d+) BPM ).*?): eighth(?: sample)? errors (\[\[.*?\]\])[,;]')
packet=log('packet_steps::')
collect(packet, r'^HITS (.*?) (\[\[.*?\]\])$')
wire={}; summary=[]
for label,k,v,m,r in re.findall(r'PACKED_NOTE (\S+) eighth=(\d+) wire_samples=(\d+) measured_samples=(-?\d+) residual_samples=(-?\d+)', packet):
    wire.setdefault(label,[]).append(list(map(int,[k,v,m,r])))
for label,v,r,e in re.findall(r'PACKED (\S+) max_wire_samples=(\d+) max_residual_samples=(\d+) earliest_samples=(-?\d+)',packet):
    summary.append((label,int(v),int(r),int(e)))
assert len(summary)==16 and len(wire)==16
ramp=log('ramp_response::')
for label,notes in re.findall(r'^(.*?RAMP .*?) samples=(\[.*?\])$',ramp,re.M):
    series[keyclear(label).split(' peak=')[0]]=ast.literal_eval(notes)
a1=re.findall(r'RAMP d=(-?[\d.]+) jitter=(\d+) peak=([\d.]+).*?false_steps=(\d+).*?locked_jump=([\d.]+)',ramp)
assert len(a1)==9, a1
a1peak=max(float(x[2]) for x in a1 if abs(float(x[0]))>9)
drift=sum(int(x[3]) for x in a1 if abs(float(x[0]))<1)
djroot={'build':'build', 'threshold':'threshold', 'one-percent':'staircase','ratio':'half/double','wobble':'wobble','nudge':'nudge','brake':'brake','steady':'5/10/16 BPM'}
groups=defaultdict(list)
for label,y in series.items():
    if label.split()[0] in djroot:
        groups[djroot[label.split()[0]]].append(y)
assert [len(groups[k]) for k in ['nudge','half/double','build','staircase','threshold','wobble','brake','5/10/16 BPM']]==[36,24,4,2,120,8,32,6], {k:len(v) for k,v in groups.items()}
phase=log('eight_hours_of_clock_flutter')
phase_peak=must(r'peak phase (\d+) samples',phase)[1]
hc=[]
for name in ['six_hour_clock_history_has_bounded_unreferenced_events','six_hour_clock_history_uncapped_control']:
    row=by[name]; line=must(r'A6 pulses=(\d+) changes=(\d+) edits=(\d+) peak_events=(\d+) final_events=(\d+) end_publish_p95_us=([\d.]+)',log(name)).groups()
    assert row['peak_working_bytes']>0
    hc.append((line[3], line[4], mifmt(row['peak_working_bytes']),line[5],line[0]))
sweeps={}
for which in ['hard','predict']:
    with (folder/f'slow-{which}.csv').open(encoding='utf8',newline='') as f:
        group=defaultdict(lambda: [[],[]])
        total=0
        for x in csv.DictReader(f):
            total+=1
            if x['stem']!='hat':
                continue
            key=(int(float(x['from_bpm'])),int(x['buffer']), int(float(x['lead_ms'])))
            for i,c in enumerate(['first_offbeat_pulse','first_beat_pulse']):
                if x['event_pulse']==x[c]:
                    group[key][i].append(int(x['err_samples']))
    assert len(group)==18 and total, group.keys()
    sweeps[which]={k:[(min(t),max(t)) for t in v] for k,v in group.items()}
pred=sweeps['predict']
mx=max(v[0][1] for v in pred.values())
mxbeat=max(v[1][1] for v in pred.values())
# JSON encoded with signed sample offsets and lossless delta encoding for the long render.
records={'sample_rate':48000,'baseline':'signed attack error, actual minus ideal, in samples',
         'cases':series, 'packed_columns':['eighth','wire delay','measured error','measured minus wire'],'packed':wire}
details={
    'edge cut and detection':[(case,int(cut),ast.literal_eval(at)) for case,at,cut in re.findall(r'(threshold .*?): confirmed at (\[.*?\]), cut (\d+)',dj)],
    'brake changes [pulse,time_us,state,gap_us]':[[keyclear(name),trans] for name,trans in re.findall(r'^(.*?brake \d+ .*?): eighth errors .*?state transitions \(pulse, time_us, state, gap_us\) (\[.*?\]);',brk,re.M)],
    'ramp mode toggles': re.findall(r'(wobble [^:\n]+): ramp toggles (\d+)',dj),
    'nudge two beats after release in BPM': re.findall(r'(nudge [^:\n]+): readout after two beats ([.\d]+) BPM',dj),
    'ideal large steps in ms': [(k,ast.literal_eval(v)) for k,v in re.findall(r'STEP ([^\n]+?) hits=\d+ ms=(\[.*?\])',log('large_steps::'))]}
assert [len(v) for v in details.values()]==[120,32,8,36,12], {k:len(v) for k,v in details.items()}
records['per-case counters']=details
with (folder/'all-eighths.csv').open('w',encoding='utf8',newline='') as out:
    allrows=csv.writer(out)
    allrows.writerow(['case','eighth_index_zero_based','signed_samples','signed_ms'])
    for label, values in series.items():
        allrows.writerows((label,i,n,format(n/48,'+.6f')) for i,n in enumerate(values))
with (folder/'packed-components.csv').open('w',encoding='utf8',newline='') as out:
    packedrows=csv.writer(out)
    packedrows.writerow(['case','eighth_index_zero_based','wire_samples','measured_samples','residual_samples','wire_ms','measured_ms','residual_ms'])
    for label,values in wire.items():
        packedrows.writerows([label,i,w,m,r,*[format(n/48,'+.6f') for n in [w,m,r]]] for i,w,m,r in values)
raw=json.dumps(records,separators=(',',':')).encode()
(folder/'signed-eighths.json.gz').write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
rec=[]
for label,y in series.items():
    rec.append([label,len(y),y[0],*[b-a for a,b in zip(y,y[1:])]])
blob=json.dumps([rec,wire,details],separators=(',',':')).encode()
blob64=base64.b64encode(gzip.compress(blob,compresslevel=9,mtime=0)).decode()
sha=hashlib.sha256(blob).hexdigest()
c7st=json.loads((ev/'c7-idle-comparison.json').read_text(encoding='utf8'))
c7='The separate 150-track C-7 idle control is pending. The earlier timing run coincided with compilation and cannot establish a mixer limit.'
if c7st.get('done'):
    c7='The independent 150-track idle reference used the original benchmark executable. '
    for z in c7st['attempts']:
        if z['quiet_run']:
            contents=Path(z['log']).read_text(encoding='utf-8-sig',errors='replace')
            misses=must(r'software_deadline_misses=(\d+)',contents)[1]
            c7+=f"{z['inserts']} inserts: {misses}/1,500 software callbacks over budget. "
if not c7st.get('done') and (ev/'c7-desktop-comparison.json').is_file():
    desktop=json.loads((ev/'c7-desktop-comparison.json').read_text(encoding='utf8'))
    valid=[x for x in desktop['attempts'] if x.get('quiet_run')]
    if desktop.get('done') and len(valid)==3:
        c7+=' The separately labelled compiler-free desktop control measured '
        c7+=', '.join(str(x['inserts'])+' inserts '+must(r'software_deadline_misses=(\d+)',Path(x['log']).read_text(encoding='utf-8-sig',errors='replace'))[1]+'/1,500 over budget ('+str(x['quiet_8s']['system_percent'])+'% host CPU before start)' for x in valid)+'. The strict idle measurement remains open.'
metrics={'head':head,'ci':args.ci,'dj':f'The 20-track mix rendered all {int(ln[0]):,} eighths once with complete waveforms and tails. Ordinary steady-state p99.9 was {sample(ln[2])} ms. The ±8% ramps peaked at {a1peak:.4f} ms.',
'history':f'Six-hour tempo history, capped vs uncapped: {hc[0][0]}/{hc[1][0]} peak events, {hc[0][2]}/{hc[1][2]} peak process memory, {hc[0][3]}/{hc[1][3]} µs end-of-run publish p95. Recorded takes retain their required grid history, even above the cap on unreferenced events.',
'burst':f'In 16 batched slowdowns the largest observed delivery delay was {sample(max(s[1] for s in summary))} ms; after subtracting it the largest absolute error was {sample(max(s[2] for s in summary))} ms.',
'deadline':f'Over 18 device configurations the worst predictive output after slowing was +{sample(mx)} ms at the first offbeat and +{sample(mxbeat)} ms at the first beat.',
'ci_note':args.ci,'c7':c7, 'a1':a1peak,'drift_false':drift,'jitter8h_samples':phase_peak,'twenty':ln,'six_hours':hc,'profiles':len(profiles)}
(folder/'review-metrics.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf8')
comments=[f'## External Beat Clock verification on {head}', '',
'DJ timing measures actual 48 kHz PCM under a simulated Clock. CPU, memory and publish-time measurements are listed separately. Positive error means late. Hats mark each eighth, kicks mark beats; attack count, waveform and tail are checked. Hardware observations are in the [Model 12 report](https://github.com/storytold/soundcraft/pull/1669#issuecomment-7072496268).','',
'| DJ case | Trains | Eighths measured | Signed range (ms) |','|---|---:|---:|---:|']
for k,v in groups.items():
    notes=[a for y in v for a in y]; comments += [f'| {k} | {len(v)} | {len(notes):,} | {min(notes)/48:+.3f} to {max(notes)/48:+.3f} |']
comments += ['',f'20 tracks: {ln[0]} eighths, including {ln[4]} received in bursts. Excluding the declared transitions and groups, {ln[1]} eighths have p99.9 {sample(ln[2])} ms. Including groups gives {sample(ln[3])} ms; on the grouped subset, p99.9 relative to arrival is {sample(ln[5])} ms. Maximum tempo history size during the mix: {ln[6]} events; peak process working set {mifmt(fk("twenty_full")["peak_working_bytes"])}. No missed or repeated attacks, altered waveforms, or open tails.',
f'±8% ramp peak {a1peak:.4f} ms. 124.0→124.3 BPM drift: {drift} false large steps. Largest displayed BPM update after lock across these nine runs: {max(float(r[4]) for r in a1):.5f}. Eight simulated hours of flutter: peak {phase_peak} samples. In the 7.9/8.0/8.1% trials the classifier stayed below threshold in all 40 subthreshold runs and fired once in each of the 80 at or above it. Four ten-minute stable coalescing runs produced zero false confirmations.','',
'| 6-hour history | Peak events | Final events | Process peak | Publish p95 at end (µs) | Pulses |','|---|---:|---:|---:|---:|---:|']
for label,row in zip(['512 cap, take ranges retained','Uncapped control'],hc):
    comments+=['| '+' | '.join([label,*row])+' |']
comments+=['','### Timing on grouped input','',
'The input timestamp for each group is its actual arrival near the last member. The irreducible component is the wait for the event’s F8 to arrive, clipped at zero. Residual is measured PCM error minus that wait. The table lists separate maxima; they need not coincide on the same note.','',
'| Source → target / cut pulse / batch | Max arrival delay (ms) | Max absolute residual (ms) | Worst early (ms) |','|---|---:|---:|---:|']
for k,w,r,e in summary:
    comments.append(f'| {k} | {sample(w)} | {sample(r)} | {sample(e)} |')
comments+=['','### ASIO-style delivery-deadline sweep','',
'Each cell is the signed minimum/maximum error (ms) over cuts and callback phases, measured on the hat PCM after the slowdown. For a locked, stable source the predictor uses the actual requested deadline. A falling or missing clock returns to the one-pulse fence. At a short device buffer the hard and predictive policies coincide.','',
'| BPM / frames / lead (ms) | Hard offbeat | Predict offbeat | Hard first beat | Predict first beat |','|---|---:|---:|---:|---:|']
for k in sorted(pred):
    boxes=[sweeps[policy][k][i] for i in [0,1] for policy in ['hard','predict']]
    comments+=['| ' + ' / '.join(map(str,k))+' | '+' | '.join(f'{a/48:+.3f}/{b/48:+.3f}' for a,b in boxes)+' |']
baseline = (ev/'steady-original-p95.log').read_text(encoding='utf8')
rx = r'steady (\d+) (\d+) BPMp95=([\d.]+) phasep95_us=([\d.]+)'
now = re.findall(rx, log('locks_and_predicts_pulses_across_tempos_jitter_and_usb_quantization'))
assert len(now)==9 and now == re.findall(rx,baseline)
comments += ['', '### Stable clock and reconnect controls', '', '| BPM | jitter (µs) | BPM p95 | Phase p95 (µs) |','|---:|---:|---:|---:|']
comments += ['| '+' | '.join(row)+' |' for row in now]
comments += ['', 'All nine steady BPM and phase p95 values matched the original reference. Coast relocked on F8 alone: 65/65 attacks and final error +2 samples (+0.042 ms). Stop on loss stayed stopped. Under braking, reaching 5 BPM gave a nominal 1.5-second loss bound; the 1 ms watchdog observed transitions at +1.501 s. A real loss at 128 BPM retains the 150 ms bound. The per-case states and pulse times are included below.']
inherited=folder/'inherited-mtc-rate-jitter.log'
if inherited.exists():
    assert '1 passed; 0 failed' in inherited.read_text(encoding='utf8')
    comments+=['', 'The inherited MTC ten-minute four-rate jitter test passed separately on this head. The optional OS virtual-MIDI receiver test was skipped; WinMM enumerated the hardware interfaces and no dedicated virtual cable. It does not replace the previously reported hardware runs.']
comments+=['','### Red controls and reproduction','',
'- Original follower lost lock in genuine 5/10/16 BPM trains. The original 32 brake renders contained 60 missing and 40 repeated attacks. On the original causal 130→80 cut at 384, groups of five yielded a 144.813 ms worst absolute residual with a separately measured 125.000 ms maximum wire wait.',
'- Original replacement-clip cache overwrote a 24,000-sample clip with 48,000, and a stale track index panicked. A stale MIDI send acknowledgement also panicked on an invalid slice start. Reverting external-loop precedence and held-key release in isolation wrapped around the local loop and suppressed explicit Note Off for held 60/64/67 before reset.',
'- At the first integration the UI fixtures lacked the audio-host field. After those compiled, strict Clippy exposed the hand-written default and optional candidate access in the Clock classifier. The final unit suites, strict Clippy and format commands are independently recorded for this revision.',
'- The original preferences loader dropped an entire configuration after a malformed follow field; reopening a legacy 256-input + 256-output calibration registry also lost every output. Tests exercise field-local recovery, visible diagnostics, and the full migration.',
'- Removing the 512-entry history compaction let 2,692 unreferenced tempo changes accumulate in a six-hour regression and failed the bound. The uncapped timing control on this exact head is shown above; it excludes changes to the estimator between revisions.',
'- The EXT regression queried the actual transport accessibility tree: the old UI had no EXT node. The user guide also describes the Clock recording workflow, and separate Rustdoc describes preparing clock clips and projecting recorded takes.',
'- The old 20-track render changed a waveform. An intermediate candidate fixed the waveform and scored 207 samples (4.313 ms) at ordinary p99.9 against 192 allowed. The new measurement above uses all 20 tracks with the same exclusions.',
'',c7,'',
'To reproduce all short reports set the environment variable ' + chr(96)+'SOUNDCRAFT_PACKET_TRACE=1'+chr(96)+' and run ' + chr(96)+'cargo test --locked -p soundcraft-ui-egui --lib clock_follow -- --nocapture --test-threads=1'+chr(96)+'. Exact ignored commands are in the PR body. Set ' + chr(96)+'SOUNDCRAFT_SWEEP_DIR'+chr(96)+' to an existing directory for the two full delivery-policy CSVs. The waveform checks compare to the native instrument shape. These automated measurements did not involve the Model 12.',
'','<details><summary>All signed eighth-note errors, including the complete 20-track render</summary>','',
'Lossless dataset (gzip/base64). The decompressed JSON contains three parts. For each entry in the first part the initial fields are case name, count and first signed error in samples; reconstruct subsequent values by cumulative sum of the remaining signed deltas. The second part has one row per scored note in a grouped slowdown: eighth index, wire delay, measured error and residual. The third records each threshold confirmation pulse, every brake state transition with the preceding interval, wobble mode switches, post-nudge BPM and ideal tempo-step errors in ms. Divide signed samples by 48 for milliseconds. SHA-256 of uncompressed JSON: '+sha+'.','',
'~~~text',blob64,'~~~','','</details>','']
comment='\n'.join(comments)
if len(comment)>65000:
    raise ValueError(f'Combined comment over GitHub limit: {len(comment)}')
(folder/'evidence-comment.md').write_text(comment,encoding='utf8')
(ev/'comment-1669.md').write_text(comment,encoding='utf8')
print(head,len(comment),len(blob64))
if args.status:
    status=d/'STATUS.zh-TW.md'; current=status.read_text(encoding='utf8')
    current=re.sub(r'\n<!-- BEGIN #1669 FINAL -->.*?<!-- END #1669 FINAL -->\n?', '\n',current,flags=re.S)
    obsolete=('- #1669 在 10、16、5 BPM','- 播放來源、SPP + Continue','- 外部 tempo map 的快取','- 已執行原版 20 首長測','- 使用實際裝置的排程方式重跑','- #1669 在第一次重開已遷移')
    current='\n'.join(line for line in current.splitlines() if not line.startswith(obsolete))
    rows=json.loads((folder/'results.json').read_text(encoding='utf8'))
    assert len(rows)==7 and all(r['head']==head for r in rows)
    suite=[]
    for row in rows[:5]:
        a,b,c=must(r'(\d+) passed; (\d+) failed; (\d+) ignored',' '.join(row['result'])).groups()
        suite.append(f"| {row['check']} | {a} | {b} | {c} |")
    counts='\n'.join(suite)
    checks='；'.join(r['check']+(' 通過' if r['code']==0 else ' 失敗') for r in rows[5:])
    local=folder.relative_to(d).as_posix()
    section=f'''<!-- BEGIN #1669 FINAL -->
## #1669 最終驗證

本機 Windows 驗證的提交為 {chr(96)}{head}{chr(96)}。

| 執行項目 | 通過 | 失敗 | 預設略過 |
|---|---:|---:|---:|
{counts}

{checks}。另有 13 組指定驗證資料（部分與一般測試重疊），包括六項獨立執行的 ignored 長測。[每份測試輸出]({local}/results.json)

共 20 首、{int(ln[0]):,} 個八分音符均一次起音且波形與尾音完整。排除事先指定的轉場與成組封包後，{int(ln[1]):,} 個八分音符的絕對誤差 p99.9 為 {sample(ln[2])} ms。含成組封包時為 {sample(ln[3])} ms；成組區相對到達時間的 p99.9 為 {sample(ln[5])} ms。±8% 連續推速峰值 {a1peak:.4f} ms；緩慢漂移誤觸 {drift} 次。八小時抖動峰值 {phase_peak} samples。近門檻 120 組、真正煞車 32 組、穩定極慢時脈 6 組以及成組大幅減速 16 組都通過。成組減速最大到線延遲 {sample(max(s[1] for s in summary))} ms，扣除線路等待後的最大絕對誤差 {sample(max(s[2] for s in summary))} ms。

六小時 tempo history 的峰值事件數（有上限／無上限）為 {hc[0][0]}／{hc[1][0]}，程序尖峰記憶體 {hc[0][2]}／{hc[1][2]}，末段發布 p95 為 {hc[0][3]}／{hc[1][3]} µs。錄音範圍所需事件保留。大緩衝慢速切換，第一個反拍／第一拍最差為 +{sample(mx)}／+{sample(mxbeat)} ms。

[逐個八分音符的有號偏差]({local}/all-eighths.csv) · [逐音分解封包時間]({local}/packed-components.csv) · [逐案量測與可解包資料]({local}/evidence-comment.md) · [測試與記憶體原始結果]({local}/profiles.json) · [逐 crate、Clippy、格式]({local}/results.json) · [六小時前後對照]({local}/review-metrics.json) · [先前 38 項情境](../g11-dj-audit/original38/RESULTS-38.zh-TW.md)

實機沿用 Model 12 → UM-ONE 與 S-MU2000 伴奏，8.000 秒銅鈸一次，8.125 秒不補播，100 與 120 BPM 兩遍 MAIN 都有八下小鼓；本輪 DJ 壓力測試為模擬時脈與實際 PCM 渲染。Open questions 保留 EXT 快捷鍵、慢速失鐘政策、Setup 選單命名、MTC chase 是否採用輸入埠 offset。C-7 閒置對照的版號、主機負載和每次執行狀態均獨立記錄：[追蹤紀錄](evidence/c7-idle-comparison.json)。

[煞車舊版逐音](evidence/dj-brake-old-attacks.csv) · [範圍快取原始失敗](evidence/F69-2-red-isolated.log) · [loop 與 held-note 回退對照](evidence/f69-loop-noteoff-red.log) · [256+256 設定遷移回歸](evidence/registry-union-red.log)
<!-- END #1669 FINAL -->'''
    status.write_text(current.rstrip()+'\n\n'+section+'\n',encoding='utf8')

