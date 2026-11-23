from pathlib import Path
import json,re,subprocess,sys,os
base=Path(__file__).parent
root=base/'publish'
gh='E:/soundcraft/tools/gh/bin/gh.exe'
env=os.environ|{'GH_CONFIG_DIR':'E:/soundcraft/tools/gh-config','GH_PROMPT_DISABLED':'1'}
pr='repos/storytold/soundcraft/pulls/1669'
def api(*args): return subprocess.check_output([gh,'api',*args],env=env)
rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
info=json.loads(api(pr));assert info['draft'] and (info['head']['sha']==rev or '--preview' in sys.argv and '--apply' not in sys.argv)
s=info['body'].replace('\r','')
url=f"https://github.com/mtlcl410/soundcraft/blob/{rev}/docs/external-clock-response-measurements.md"
label=f'[PCM tables, signed errors and reproduction commands]({url})'
assert '### External Clock tempo steps (af4af80b)' in s
old='The sequencer releases events through the last received F8 plus one pulse.'
assert old in s
s=s.replace(old,'At af4af80b the sequencer released events through the last received F8 plus one pulse. The device-buffer exception verified below applies to the current revision.')
s=s.replace('## Coast recovery when the external clock returns',f'''### External Clock under jitter, tempo ramps and device buffering

At 48 kHz, all 1,782 eighth notes in the 36 tempo-step cases retained a single complete PCM waveform. The first offbeat peaked at 6.604 ms with ±1 ms input jitter and 5.875 ms with ±2 ms. Later peaks were 4.750 and 4.188 ms. Across four ten-minute steady packet-burst runs there were zero false steps, dropouts or onset errors. Grouped 180→60 BPM input remains a limitation: a subsequent eighth sounded up to 196.896 ms early.

Continuous ±8% pitch-fader moves improved from 9.0625 to 3.8333 ms peak. All nine steady p95 pairs and the original 12 ideal-input vectors matched the previous head. The eight-hour grid peak remained 148 samples; a separate eight-hour audio render produced identical records for all 115,201 attacks (234-sample peak). The slow 124.0→124.3 BPM drift triggered neither response mode. The largest consecutive BPM change after acquisition was 0.09139 BPM.

When the device buffer is shorter than a pulse, both policies render sample-identical output. In the ten eligible steady conditions, scheduling to the measured device deadline reduced late attacks from +28.646…+85.104 ms to zero samples. The 18-condition slowdown sweep checked 58,752 note and click attacks across both policies. A separate red regression reproduces an entire overdue note disappearing on return to prediction; all waveform and release checks now pass. {label}

## Coast recovery when the external clock returns''')
old=re.findall(r'^- Does this external tempo-follow response meet live performance needs\?.*$',s,flags=re.M);assert len(old)==1
s=s.replace(old[0],f'''- Should tempo-follow response be fixed or user-adjustable? The measured ±8% ramp peak is 3.8333 ms, while the unchanged clean step cases remain within one sample on the first offbeat and three samples from the second beat. Packed delivery can take 7 or 15 F8s to confirm and reach 196.896 ms early. Bitwig offers a response slider for this trade-off. [Bitwig Studio User Guide, Dashboard › Synchronization Settings](https://www.bitwig.com/userguide/latest/the_dashboard/)
- Is this bounded policy acceptable on large device buffers? Previously committed PCM cannot be recalled when the clock slows. In the 20% slowdown sweep, the earliest first offbeat and next beat were −25.000 ms, already committed before the missing pulse could be observed. After falling back to the one-pulse wire limit, the latest first offbeat was +86.500 ms and the next beat +83.771 ms (300 BPM / 2,048 frames / 50 ms). The amount of late fallback error depends on the policy and device. Short buffers retain the hard limit even with a long lead. {label}''')
assert s.count('### External Clock under jitter')==1 and s.count('Should tempo-follow response be fixed')==1
payload=base/'pr-update.json';payload.write_text(json.dumps({'body':s},ensure_ascii=False),encoding='utf8')
if '--apply' in sys.argv:
    fresh=json.loads(api(pr));assert fresh['head']['sha']==rev and fresh['body']==info['body']
    result=json.loads(api('-X','PATCH',pr,'--input',str(payload)))
    assert result['head']['sha']==rev and result['draft'] and result['body'].replace('\r','')==s
    print(result['html_url'],rev)
