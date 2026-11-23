from pathlib import Path
import sys,json,statistics,subprocess
d=Path(__file__).resolve().parent
data=json.loads((d/'distribution.json').read_text())
assert data['all']['sd']['n']==10 and data['all']['render']['n']==9
ab=[r for label in ['autoA','autoB'] for r in json.loads((d/label/'result.json').read_text())]
stale=[r for r in ab if r['action'].startswith('stale')]
fresh=[r for r in ab if r['action'].startswith('fresh') and r['render_ms'] is not None]
assert len(stale)==3 and len(fresh)==5
assert all(r['lead_range_us']==[0,0] and r['clamp_delta'] for r in stale)
assert all(r['lead_range_us'][0]>0 and r['clamp_delta']==0 for r in fresh)
summ=lambda rows:statistics.median(r['render_ms'] for r in rows)
assert round(summ(stale)-summ(fresh),3)==38.679
p=d/'REPORT.zh-TW.md'
s=p.read_text(encoding='utf-8-sig').replace('這項觀察須以同一時碼輸入主動重開音訊端點才能檢查因果。','下方以相同輸入單獨驗證重開音訊的效果。')
s+='''

## 只重開 SoundCraft 音訊的對照

保持 Model 12 停止，循原有一般 USB MIDI → Model 12 DIN OUT → UM‑ONE 的實體路徑，逐次重送 0004 錄得的同一段 781 筆 quarter-frame，使用同一份 S‑MU2000 專案和鋼琴波形樣板。每次都以 UM‑ONE 實際收到的時碼計算，避免將電腦排程送出的瞬間當成到達。只重新套用該測試程序原本的輸出設定，裝置仍為 Model 12、48 kHz，整段未進 STORAGE 或改變硬體接線。兩個其他 SoundCraft 程序均已確認 MTC Offline，走帶停止。

| 音訊串流狀態 | Windows 數位播放端的 A4 相對 DIN 晚 ms | 中位數 | 引擎有效呈現延遲 |
|---|---|---:|---|
| 進出 STORAGE 後，原串流 | 50.861、50.298、48.713 | 50.298 ms | 全為 0；每次觀測窗拒用時間戳 283～292 次 |
| 同一程序重新開啟相同輸出 | 11.937、11.619、11.943、10.704、11.083 | 11.619 ms | 35.708～42.708 ms；各窗均無新增拒用 |

重開後第一輪的 WASAPI 數位回錄在起音搜尋範圍內標記 data discontinuity，已排除；表中保留其餘五筆有效結果。兩組中位數相差 **38.679 ms**。此對照量的是 Windows 播放端，並未再錄一首 SD 歌曲。[原狀及重開對照](autoA/result.json) · [重開後追加三次](autoB/result.json) · [回錄封包旗標](autoA/loop.csv)

**判定。** 在這台 Windows／Model 12 系統上，進出 STORAGE 曾使 WASAPI 音訊串流失效。SoundCraft 對遺失或超過一秒的呈現延遲採用零，直到重開裝置才恢復有效讀值。實機分段和同輸入對照都把主要跨次差距指向這條音訊呈現路徑。根據現有證據，無須調整 quarter-frame 解碼或加入固定毫秒補償；無法細分是哪一層最先提供了無效時間戳，也不能把剩下約 11.6 ms 全歸給 MTC。十輪原始 SD 驗收仍保留其跨次差距。MTC 協定精度上限及外接取樣時鐘的效果均未由這個測試證實。

**複測步驟。** 從 STORAGE 回歌曲畫面後，待 Model 12 音訊端點恢復，在 SoundCraft 停止時開啟 Setup → Playback Engine，以 Reconnect audio device 重開原輸出（本次自動對照透過重新套用相同的輸出設定達成）。確認裝置仍為 Model 12／48 kHz、輸出時間戳恢復有效，再開始新一輪。跨次比較應記錄是否重開，並保存 reported_lead_us 與 lead_clamps 的增量。[程式的重連與串流失效處理](https://github.com/storytold/soundcraft/blob/ee8092029b37dac7699b6f15bd26a993f6370a54/crates/ui-egui/src/app/audio.rs)
'''
p.write_text(s,encoding='utf-8')
msg="""**Timing investigation (ten additional SD takes).** Five takes started at the song head and five at 2 s. Relative to the scheduled 5.000 s A4, SD onset ranged from +13.896 to +56.771 ms (median +52.323 ms, spread 42.875 ms). Nine takes also had time-stamped WASAPI render and USB input captures aligned to the UM-ONE DIN trace. The render-tap spread was already 43.590 ms. Two independent microphone marks per take placed the SD timeline on the USB input clock with only 0.353 ms of between-take variation in its origin against DIN. Take 0016 had SD audio only after an endpoint invalidation interrupted the external capture. The original 42 ms spread is not evidence of frame quantization or an MTC accuracy ceiling.

A controlled replay sent the same captured quarter-frame sequence back through the physical DIN link. With the invalidated Windows audio stream, SoundCraft rejected the presentation timestamps and used zero lead. The three measured A4 delays at the Windows render tap were 50.861, 50.298 and 48.713 ms. Reopening the same 48 kHz Model 12 output in the same SoundCraft process restored 35.708–42.708 ms of reported lead. Five valid A4 delays ranged from 10.704 to 11.943 ms (median 11.619 ms), a **38.679 ms median improvement**. One additional capture after the reopen had a WASAPI discontinuity in the onset search window and was excluded. This replay measured the Windows render tap; the ten SD takes are the independent recorder measurement.

**Reproduction and recovery.** On this Windows shared-audio setup, switching the Model 12 into and out of USB STORAGE invalidated the playback stream. Stop SoundCraft, restore the recorder to song mode, then reopen the same output in Setup → Playback Engine before judging MTC alignment. Track both the reported presentation lead and the change in the timestamp-clamp counter. Six reader, driver-timestamp and presentation regressions passed. The decoder already uses quarter-frame phase and timestamp age. These results do not warrant a protocol offset change or a claim that a shared sample clock would eliminate this workflow-specific delay."""
sys.path.insert(0,r'E:/soundcraft/tmp/1669-coderabbit-final')
from check import gh,api,env
r='repos/storytold/soundcraft/pulls/1663'
pr=api(r);body=pr['body'];end='<!-- end-H-MTC-SD-results -->'
assert body.count(end)==1 and 'Timing investigation (ten additional SD takes)' not in body
updated=body.replace(end,msg+'\n'+end)
assert api(r)['body']==body
subprocess.run([gh,'api','-X','PATCH',r,'--input','-'],input=json.dumps(dict(body=updated)).encode(),env=env,stdout=subprocess.DEVNULL,check=True)
ver=api(r)
assert ver['body']==updated and pr['head']['sha']==ver['head']['sha'] and pr['draft']==ver['draft']
print('updated and verified',ver['html_url'],pr['head']['sha'])
