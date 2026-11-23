from pathlib import Path
from statistics import mean
import json,os
base=Path(__file__).resolve().parent
old=base/'chorus-latency-1674';fix=base/'chorus-latency-1675-fixed';fin=base/'chorus-latency-1675-final';qdir=base/'chorus-latency-1675-queue'
def rd(d,f):return json.loads((d/f).read_text())
a=rd(old,'split.json');b=rd(fix,'split.json');c=rd(fin,'split.json')
def extent(v):return f'{min(v):.1f}–{max(v):.1f}'
def take(d,k):return [v[k] for m,v in d.items() if m.startswith('boundary-')]
def span(d,k):return extent(take(d,k))
def avg(d,k):return mean(take(d,k))
def pairs(ms,k):return [c[f'queue{ms}-{s}'][k] for s in 'ab']
def fp(ms,k):return ' / '.join(f'{x:.1f}' for x in pairs(ms,k))
img='![External MIDI Clock resume latency](IMG/midi-clock-resume-latency.png)\n\n![Crash onset and waveform correlation](IMG/midi-clock-resume-boundary.png)'
pr=f'''## External Clock resume latency

Fixes #1675. Continue used to clone and publish the current project again, including preparing its instruments, before submitting Play. The player now reuses its prepared snapshot only when both the source document and the published tempo grid still match. Edits, a new player, or an unpublished tempo change take the full preparation path. The scheduling change for #1674 stays in place.

Four exact-position resumes per build used the same project and 120 BPM physical MIDI loop. Temporary probes timestamped MIDI reception, host dispatch, session preparation, audio callback receipt and completion of the first mixed block. They are excluded from the PR. Times below are milliseconds.

| First Clock to downbeat, by stage | Before | Fixed |
|---|---:|---:|
| Input to host processing | {span(a,'input_to_ui_ms')} | {span(b,'input_to_ui_ms')} |
| Session preparation | 7.404–7.565 | 0.001–0.002 |
| Command to callback | {span(a,'queue_to_callback_ms')} | {span(b,'queue_to_callback_ms')} |
| Callback to first mixed block | {span(a,'callback_to_render_ms')} | {span(b,'callback_to_render_ms')} |
| Input to completed first mix | {span(a,'input_to_render_ms')} | {span(b,'input_to_render_ms')} |
| First mix to digital loopback | {span(a,'render_to_digital_ms')} | {span(b,'render_to_digital_ms')} |
| First Clock to digital crash, mean (range) | {avg(a,'digital_ms'):.1f} ({span(a,'digital_ms')}) | {avg(b,'digital_ms'):.1f} ({span(b,'digital_ms')}) |

The longest fixed take spent {max(take(b,'input_to_ui_ms')):.1f} ms waiting for host processing. The reduction in repeated preparation does not guarantee a fixed end-to-end response time.

**Monitoring path.** Separate waveform taps sampled digital loopback, bridge input, ASIO 9/10 output callback and the Model 12 USB MAIN mix return. After warming the streams, the uninstrumented Windows integration ran 20/40/60 ms test-queue prefills twice in reverse order on the return pass. Digital-loopback-to-MAIN measured {fp(20,'digital_to_main_ms')} ms, {fp(40,'digital_to_main_ms')} ms and {fp(60,'digital_to_main_ms')} ms respectively. At 60 ms prefill the bridge capture to ASIO callback contributed {fp(60,'bridge_to_output_ms')} ms and callback to MAIN contributed {fp(60,'output_to_main_ms')} ms. The independent digital taps have a small timestamp offset. This accounts for a delay of the size of the earlier ~77 ms observation; the original two recordings lack the intermediate timestamps to identify their exact split. These figures measure the USB mix return, not acoustic speaker latency. One exploratory 20 ms prefill before the warm-up control produced an outlying 145.9 ms bridge-path total (121.7 ms observed software FIFO wait).

The uninstrumented build produced one crash on both digital and MAIN in all six 8.000 s takes, zero in both 8.125 s takes. Later accompaniment was present. On the original PR branch, the mixer, playback and UI libraries passed 672 tests (five ignored). The new regression failed first on the redundant rebuild, then passed; it also checks document edits, tempo-only updates and ordinary playback replacing a snapshot. Formatting and Windows integration strict all-targets Clippy on the changed crates passed.

{img}'''
(fix/'pr-section.md').write_text(pr,encoding='utf8')
zh=f'''### 外部 MIDI Clock 起播延遲與監聽轉送（#1675）

沿用上一節的八小節 S-MU2000 伴奏、Model 12 USB MIDI → DIN OUT → UM-ONE、120 BPM、數位回錄 48 kHz、監聽 ASIO 9/10 與 MAIN USB 11/12 回錄 44.1 kHz。基準為 #1669 修好起點漏音後的 `baab55e`。修正前後各四次從精確的 SPP 64 續播。以讀入第一個 F8 為基準，臨時診斷版在接收、主機處理、專案準備、音訊回呼和第一個區塊混完時記錄時間；校對 UM-ONE 的獨立軟體擷取，兩者觀測同一個外部 Clock。雙路校時與 WAV 使用同一台 Windows 電腦的時鐘，毫秒值包含回呼時間估算。音符辨識沿用相關係數 0.90。

| 量測階段（毫秒）| 修正前，四輪範圍 | 修正後，四輪範圍 |
|---|---:|---:|
| MIDI 接收到主機處理 | {span(a,'input_to_ui_ms')} | {span(b,'input_to_ui_ms')} |
| 主機準備專案 | 7.404–7.565 | 0.001–0.002 |
| 播放指令到音訊回呼收到 | {span(a,'queue_to_callback_ms')} | {span(b,'queue_to_callback_ms')} |
| 回呼收到到第一個混音區塊完成 | {span(a,'callback_to_render_ms')} | {span(b,'callback_to_render_ms')} |
| MIDI 接收到區塊混完 | {span(a,'input_to_render_ms')} | {span(b,'input_to_render_ms')} |
| 混完到電腦數位回錄 | {span(a,'render_to_digital_ms')} | {span(b,'render_to_digital_ms')} |
| 第一個 Clock 到電腦回錄，平均（範圍） | {avg(a,'digital_ms'):.1f}（{span(a,'digital_ms')}） | {avg(b,'digital_ms'):.1f}（{span(b,'digital_ms')}） |

修正讓播放器在文件身分和已送出的速度圖相同時沿用已準備的專案。軌道編輯與尚未送出的速度變更仍會觸發更新。修正前後的端到端平均差 {avg(a,'digital_ms')-avg(b,'digital_ms'):.1f} 毫秒；修正後仍有一次主機派送等了 {max(take(b,'input_to_ui_ms')):.1f} 毫秒。此處能直接歸因的是省去了重複準備，無法從四輪推論所有裝置上的最低延遲。

**MAIN 多出的時間。** 最終版不含臨時時間探針。暖機後只改測試用監聽轉送的軟體佇列，依序做 20、40、60、60、40、20 毫秒，維持相同取樣率、ASIO 緩衝與音量。下表每欄列出兩次實測。逐次以同一個銅鈸波形比對；兩個獨立數位擷取程式的回呼時間戳有約數毫秒的差異，數位到 MAIN 的總數已包含此差異。

| 轉送預填 | 轉送程式收到波形到 ASIO 輸出回呼 | ASIO 輸出回呼到 MAIN USB 回錄 | 電腦數位回錄到 MAIN |
|---|---:|---:|---:|
'''
for ms in (20,40,60):zh+=f'| {ms} ms | {fp(ms,"bridge_to_output_ms")} ms | {fp(ms,"output_to_main_ms")} ms | {fp(ms,"digital_to_main_ms")} ms |\n'
zh+=f'''
早先兩輪多出 77.09 與 76.81 ms，當時只錄兩個端點。本輪的實測解釋了同量級的延遲如何形成，無法追溯先前每個中繼點的確切毫秒數。ASIO 回呼到 MAIN 包含輸出與回錄，不等於 Model 12 本體的單向延遲。前一組未加暖機的探索性 20 ms 首輪，多出 145.9 ms，其中觀察到軟體佇列等待 121.7 ms；記錄一併保留。喇叭的聲學輸出未量測。

未加探針的最終執行檔 SHA-256 `{rd(fin,'control.json')['sha256']}`，原曲 SHA-256 `{rd(fin,'control.json')['project_sha256']}`。6 次 8.000 秒都有一個銅鈸，2 次 8.125 秒均為零，數位與 MAIN 兩路一致。相同音樂片段的後續伴奏另以波形確認。每輪 UM-ONE 收到 144 個 Clock。

原 PR 分支的回歸測試先在舊流程報「Continue rebuilt an unchanged session」，修正後混音 100、播放 189、介面 383，共 672 項通過、5 項略過。格式與 Windows 整合版兩個修改 crate 的嚴格 all-targets Clippy 通過。臨時分段探針與監聽程式均留在本機。

![修正前後延遲與監聽佇列對照](chorus-latency-1675-fixed/midi-clock-resume-latency.png)

![副歌起點與跨過起點時的實錄波形](chorus-latency-1675-fixed/midi-clock-resume-boundary.png)

[基準分段數據](chorus-latency-1674/split.json) · [修正後分段數據](chorus-latency-1675-fixed/split.json) · [未暖機探索紀錄](chorus-latency-1675-queue/split.json) · [最終版暖機對照](chorus-latency-1675-final/split.json) · [缺陷 #1675](https://github.com/storytold/soundcraft/issues/1675) · [原 PR #1669](https://github.com/storytold/soundcraft/pull/1669)
'''
(fix/'local-section.md').write_text(zh,encoding='utf8')
