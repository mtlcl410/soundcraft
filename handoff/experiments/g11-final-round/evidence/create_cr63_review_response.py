from pathlib import Path
import json,re
p=Path('../evidence')
d=json.loads((p/'1663-671b6672'/'coderabbit-increment.json').read_text('utf8'))
rows=[
('Major','Pending integrated evidence','The 48→96 kHz retained tail must drain and advance with its original session rate.','cr63-red-retained_audio_uses.log'),
('Major','Pending integrated evidence','A stopped locate with input monitoring must publish the located playhead. Monitor samples do not consume timeline samples.','cr63-red-a_stopped_locate_while.log'),
('Major','Passed in b3a3ed9','For a channel event with wire time 90 µs and a take boundary followed by queue time 250 µs, the old code stamped 90 and the fix stamps 250. Quarter frames retain their wire timestamp.','cr63-transport-red.log'),
('Major','Passed in 59b5e3c','At 25 fps with eight-frame freewheel, omitting the last group before midnight previously left the reader at quarter 8,639,991. It now resumes on the next day at 8,640,007, with one lock, zero losses and zero inferred seeks.','cr63-rx-red.log'),
('Major','Pending integrated evidence','Recheck the previous callback fault under the graph lock before accepting the replacement stream.',None),
('Major','Passed in 93d18d1','Nine active revisions evict generation one from an eight-entry table. An uncached route now waits for a presentation with an available matching map, then sends Start and F8 on the new pass. A route already holding the exact map can continue.','cr63-transport-red.log'),
('Major','Passed in 93d18d1','A pending Song Position Pointer scheduled for 10 ms is discarded if a locate supersedes its pass at 4 ms or precisely at its 10 ms deadline. The unchanged-pass test still delivers both queued messages in order.','cr63-transport-red.log'),
('Major','Passed in 93d18d1','After a rejected transport Stop, the old reconnect sequence was Start, F8. The repaired sequence is Stop, Start, F8. A Stop already handed off is left delivered.','cr63-transport-red.log'),
('Major','Pending integrated evidence','Applying output B while A is unavailable must replace the recovery target even when opening B fails.',None),
('Major','Pending integrated evidence','A connected MIDI input alone must not start recording when no player is available.',None),
('Minor','Pending integrated evidence','On an explicit edit to the session offset, remove the conflicting legacy value, including when the new offset is zero.','cr63-red-explicitly_resetting.log'),
('Minor','Pending integrated evidence','When crash recovery restores a session, combine the normal recovery status with the timecode-offset conflict explanation.',None),
('Minor','Pending integrated evidence','Describe Clock following as the later stacked feature and make clear that this layer handles MTC Online.',None),
('Minor','Passed in 93d18d1','After editing from 48 to 96 kHz, the published 4,800-sample delay is again reported as 100 ms using the callback’s original 48 kHz rate. It formerly displayed 50 ms.','cr63-transport-red.log'),
('Minor','Passed in 94f463e','If an unnamed output shares an ID with DIN, DIN is unavailable; the other uniquely identified output remains usable.','cr63-transport-red.log'),
('Minor','Pending integrated evidence','Refusing an online record start must discard the pending MIDI-record pass as well.','cr63-red-rejected_online_recording.log'),
('Minor','Passed in 93d18d1','At 126 BPM and 48 kHz the first F8 after the origin rounds to sample 952. Polling there now sends Start and one F8; the following F8 is delivered on the next wake, at least 1 ms later.','cr63-transport-red.log'),
('Minor','Passed in 93d18d1','An unencodable stopped SPP remains visible through repeated polls and clears after a valid stopped locate.','cr63-transport-red.log'),
('Minor','Passed in 93d18d1','The compensated route queues F1 and the direct route queues F8. Only the direct F8 reaches the sink across the timing interruption.','cr63-all.log'),
('Minor','Passed in 93d18d1','A second worker stall that extends beyond the scheduled repayment window returns to position recovery. The 120 BPM regression with a 240→1,200 ms worker stall sends Stop, SPP, Continue. The uninterrupted repayment control still sends all 49 of 49 ticks.','cr63-transport-red.log'),
('Minor','Passed in b3a3ed9','A wake callback invoked during MIDI-port close can acquire the writer guard; the gate closure and loss marker stay serialized.','cr63-transport-red.log'),
('Minor','Pending integrated evidence','Dismiss the saved idle warning once manual reconnect succeeds, including after a previously failed attempt.',None),
('Minor','Pending integrated evidence','After the bounded initial retries, allow a later recovery probe when the unavailable endpoint remains listed.',None),
('Minor','Pending integrated evidence','Reconnect to the actual original host and device when startup selected a fallback host.',None),
('Nit','Pending integrated evidence','Document out-of-range sampling and the zero-padding expectation of the public waveform search helper.',None),
]
out=['# Response draft for the #1663 review of 671b6672','',
     'Local draft. The [formal review]('+d['reviews'][0]['html_url']+') contains 10 inline Major findings, 14 Minor findings in its body, and one documentation nit.','',
     '## Findings and verification','','| # | Severity | Finding | Status | Response and evidence |','|---:|---|---|---|---|']
titles=[]
for c in d['inline']:
 title=re.findall(r'^\*\*([^*\n]+)\*\*\s*$',c['body'],re.M)[0]
 titles.append('['+title+']('+c['html_url']+')')
for m in re.finditer(r'^\*\*([^*\n]+)\*\*\s*$',d['reviews'][0]['body'],re.M):
 if not m.group(1).startswith('Actionable'):titles.append(m.group(1))
assert len(titles)==len(rows)==25
for n,(title,(severity,status,description,link)) in enumerate(zip(titles,rows),1):
 out.append(f'| {n} | {severity} | {title} | {status} | {description}'+(f' [Local log]({link}).' if link else '')+' |')
out+=['','## Reviewer reply draft','','The update addresses transport, callback and device recovery during MIDI synchronization. Recorded channel messages take their time under the take-writer lock. Forward MTC keeps its absolute reader day through a short dropout over midnight. The output scheduler checks that its tempo map and transport pass match audible audio, and retries a failed Stop before resuming a new pass.','',
      'At 120 BPM in the compensated Clock tests, a 100 ms or 200 ms timestamp interruption still delivers all 49 expected F8 pulses over the one-second observation. The interval during repayment is 17–18 ms for the 100 ms gap and 15 ms for the 200 ms gap, after which spacing returns to the source grid. A separate test removes a 100 ms timestamp gap, lets repayment begin, and then prevents the worker from running from 240 ms to 1,200 ms. The repayment beat has already expired when the worker next gets CPU time. It sends Stop, SPP and Continue at the current position rather than replaying old debt.','',
      'The lane’s playback library suite passed 214 tests with the two OS-dependent cases ignored. Final integration results and the other review groups will be appended when verified.','',
      '[Full playback results](cr63-all.log) · [Timing and routing reproductions](cr63-transport-red.log) · [Midnight reproduction](cr63-rx-red.log) · [Midnight correction](cr63-rx-green.log) · [Complete original review index](1663-671b6672/coderabbit-index.md)','']
(p/'cr63-review-response.md').write_text('\n'.join(out),encoding='utf8')
