import csv,json
from pathlib import Path
from statistics import median
from hardware_tables import tables
root=Path(__file__).resolve().parent
runs=root/'runs'
data=[]
for d in sorted(runs.glob('h4a-integration-*')):
    if not (d/'environment-result.json').is_file():continue
    if not json.loads((d/'environment-result.json').read_text())['environment_valid']:continue
    def wire(name):
        with (d/name).open() as f:return [r['hex'] for r in csv.DictReader(f) if r['hex'].startswith(('f1','f0'))]
    tx,rx=wire('tx.csv'),wire('wire.csv');m=json.loads((d/'result.json').read_text())
    data.append(dict(pair=d.name,rate=m['rate'],direction=m['direction'],qf=sum(p.startswith('f1') for p in rx),full=sum(p.startswith('f0') for p in rx),wire_equal=rx==tx,spread_ms=m['spread_ms'],locates=len(json.loads((d/'locates.json').read_text())),errors=len(m['locate_mismatches'])))
assert len(data)==10 and all(x['wire_equal'] and x['errors']==0 for x in data)
(root/'runs/h4a-wire-audit.json').write_text(json.dumps(data,indent=2))
old=(root/'1663-manual-20261122.md').read_text().strip()
old=old.replace('The ownership and cause of the omission still need a deterministic regression.', 'The marker lies wholly inside the interval skipped to rejoin the master.')
text=old+'\n\n**Independent MTC generator over physical DIN**\n\nEach direction used ten takes per rate, alternating start at zero and a nonzero locate. The receiving WinMM interface captured every generated full-frame and quarter-frame message byte for byte. All 200 stopped locates landed on the requested sample. All ten runs passed the environment checks.\n\n| Session fps | UM-ONE → Model 12 onset spread (ms) | Model 12 → UM-ONE onset spread (ms) |\n|---|---:|---:|\n'
for rate in ('24','25','29.97df','29.97nd','30'):
    a,b=[next(x for x in data if x['rate']==rate and x['direction']==s) for s in ('forward','reverse')]
    text+=f"| {rate} | {a['spread_ms']:.3f} | {b['spread_ms']:.3f} |\n"
text+='\nThe target was ≤3 ms. None of the ten groups met it. Subtracting a constant audio loop delay and accounting for the direction-specific MIDI path time do not change the spread. The 29.97 non-drop case uses the actual 30000/1001 cadence with non-drop labels.\n\n**Isolated playback regression**\n\nReplaying 301 recorded quarter frames and 478 callback times on #1663 alone ('+chr(96)+'bab99312'+chr(96)+') reproduced the missing attack without Model 12 hardware, an ASIO driver or #1634. Four PCM markers were scheduled at 0.25, 0.75, 1.25 and 1.75 s. The callback rendered three attacks and recorded one hard relocation. The assertion expected four and exited 101. The existing design protects the stopped locate at startup, then seeks forward after one second of sustained phase error. The skipped interval can contain music even with a continuously running master.\n\nThe preceding firmware was 1.30 0088. This run used 1.50 0103 and a different audio path and stimulus. There is no firmware-only timing comparison. [TASCAM firmware release notes](https://cf.tascam.com/wp-content/uploads/downloads/products/tascam/model_12/e_model12_rn_vl.txt)\n'
text=text.replace('**Isolated playback regression**','**Offline replay of the accepted MTC chase rule**')
text+='\nThe four-attack assertion represented a superseded expectation. A short sound entirely within the skipped span is correctly omitted. All three hardware rolls preceded STORAGE. Across their 39,824 callback intervals the maximum was 6.499 ms, ruling out the later sustained 251 ms cadence as their trigger. The source of the initial phase difference has not been apportioned. Performance assessment is paused.\n\n**Known limitation.** SoundCraft restores controller state on a seek. It does not re-trigger a sustained MIDI note whose note-on precedes the landing point. Pro Tools documents per-track Note Chasing in the [2026.4 Reference Guide, p. 1043](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2026.4.pdf#page=1145).\n'
(root/'1663-evidence-current.md').write_text(text,encoding='utf8')
(root/'1663-evidence-payload.json').write_text(json.dumps(dict(body=text)),encoding='utf8')

