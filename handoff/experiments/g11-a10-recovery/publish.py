import json,re,sys,subprocess,os
from pathlib import Path
d=Path(__file__).resolve().parent
env=dict(os.environ,GH_CONFIG_DIR='E:/soundcraft/tools/gh-config')
repo='storytold/soundcraft'
gh='E:/soundcraft/tools/gh/bin/gh.exe'
def run(*args):return subprocess.check_output(list(args),env=env).decode('utf-8').strip()
def ghview(i):return json.loads(run(gh,'pr','view',str(i),'-R',repo,'--json','headRefOid,body,isDraft'))
clock_question='When output timing returns during the same rolling transport, SoundCraft now spreads all missed F8 ticks evenly over at most one quarter note, then resumes the normal intervals. Neither the MIDI specification nor the Pro Tools Reference Guide prescribes recovery from this audio-output timestamp gap. This is a conservative policy pending user confirmation. Does it suit devices that count every tick? [MIDI timing messages](https://midi.org/summary-of-midi-1-0-messages) · [Pro Tools Reference Guide, MIDI Beat Clock](https://resources.avid.com/SupportFiles/PT/Pro_Tools_Reference_Guide_2020.12.pdf)'
coast_question='Does the current Coast behavior suit a live change of clock source? Since 82cc19c, a rolling transport relocks to the tempo and relative phase of returning F8 pulses once a valid tempo is available, without waiting for Start/Continue. Stop on loss stays stopped on F8 alone.'
clk='At 48 kHz and 120 BPM, a deterministic port polled every 1 ms lost output timing from 100 to 200 ms. Previously it delivered five expired clocks, starting 95.833 ms late, with four successive 1 ms intervals. After the fix the first F8 was due at 208.333 ms and handed off at 209 ms (+0.667 ms). Five owed ticks were spread over the next beat: 29 clocks from 209 to 688 ms, at 17–18 ms intervals (28 intervals). At 700 ms the pulse count matched uninterrupted playback; subsequent handoffs matched it exactly. Both runs sent 49 clocks through 1000 ms inclusive, with identical transport commands. A 200 ms gap also finished at 49/49. These are simulated MIDI handoffs.'
mtc='At 25 fps, after timing was unknown from 100 to 200 ms, the old first QF was 100 ms late. The fix sends one full-frame locate at 200 ms for 00:00:00:05, skips the obsolete pieces, and starts the next complete QF group at 240 ms. Piece 0 reached the simulated port at its deadline (+0 ms), followed by pieces 1–7 every 10 ms. The 40 ms wait is the time to the next group boundary. A separate 20–50 ms gap verifies a live locate even close to the transport origin.'
for i,n in [(1662,'beat'),(1663,'mtc'),(1669,'follow')]:
 sha=run('git','-C',str(d/n),'rev-parse','HEAD')
 v=ghview(i)
 assert v['headRefOid']==sha and v['isDraft']
 body=v['body']
 forremove={1662:'- Should a recovered output discard expired Clock messages immediately?',1663:'- Should recovery immediately discard expired QFs even for a short loss?'}
 if i in forremove:
  rx=re.compile('(?m)^'+re.escape(forremove[i])+r'[^\r\n]*')
  assert len(rx.findall(body))==1
  body=rx.sub('- '+clock_question if i==1662 else '',body)
 if i==1669:
  body=body.replace('## Open questions','## Open questions\n\n- '+coast_question,1)
 num={'beat':154,'mtc':191,'follow':227}[n]
 log=(d/(n+'-paced-suite.log')).read_text(encoding='utf-8-sig',errors='replace')
 assert f'{num} passed; 0 failed' in log
 assert 'Finished `dev`' in (d/(n+'-paced-clippy.log')).read_text(encoding='utf-8-sig',errors='replace')
 verification=f'Local Windows playback suite: {num} passed. Workspace rustfmt and playback Clippy (all targets, warnings denied) passed.'
 desc={1662:clk,1663:mtc,1669:'The integrated branch inherits the Clock fix from #1662 and the MTC fix from #1663. The same regressions on upstream main had no output implementation to exercise.\n\n'+clk+'\n\n'+mtc}[i]
 heading='## A-10 verification after output timing loss'
 assert heading not in body
 summary=heading+'\n\n'+desc+'\n\n'+verification+' Merge order: #1662 → #1663 → #1669.\n\n'
 body=body.replace('## Open questions',summary+'## Open questions',1)
 assert heading in body
 payload=d/f'{i}-body.json'
 payload.write_text(json.dumps({'body':body},ensure_ascii=True))
 assert ghview(i)==v
 run(gh,'api','-X','PATCH',f'repos/{repo}/pulls/{i}','--input',str(payload))
 after=ghview(i)
 assert after['isDraft'] and after['headRefOid']==sha and heading in after['body'] and desc.splitlines()[0] in after['body'] and (i!=1662 or clock_question in after['body']) and (i!=1669 or coast_question in after['body'])
 print(i,sha,'verified')
