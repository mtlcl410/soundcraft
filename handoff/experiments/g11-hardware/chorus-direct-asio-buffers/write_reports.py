from pathlib import Path
import json,sys
d=Path(__file__).resolve().parent
summary=json.loads((d/'summary.json').read_bytes())
rows=json.loads((d/'metrics.json').read_bytes())
assert len(rows)==36
delta=summary['256']['mean']-summary['64']['mean']
names=lambda b: ', '.join(k for k,v in rows.items() if v['size']==b and v['peak_residual_step']>16)
def table(en):
 out=['| Actual frames (in/out) | First Clock to MAIN, mean (range) | Takes with waveform deviations | Low-level windows |' if en else '| 實際輸入／輸出（取樣） | 第一個 Clock 至 MAIN 平均（範圍） | 波形偏差次數 | 音量驟降視窗 |','|---|---:|---:|---:|']
 for b,s in summary.items():
    out.append(f"| {b} / {b} | {s['mean']:.2f} ms ({s['lo']:.2f}–{s['hi']:.2f}) | {s['flags']}/12 | {s['drops']} |")
 return '\n'.join(out)
en=f"""### Direct ASIO buffer sizes on the Model 12

At 44.1 kHz, requesting 128 or 64 frames in SoundCraft while the TASCAM panel was set to 256 still delivered 256-frame callbacks in both directions. Changing the vendor panel and reopening the stream produced the requested sizes. The final run restored and verified 256. Two independent stream opens per setting used the same S-MU2000 project and physical Model 12 → UM-ONE MIDI loop described above.

{table(True)}

All 24 starts at 8.000 s produced one crash each. All 12 starts at 8.125 s produced zero, with later accompaniment present in every MAIN recording. The mean includes all eight exact starts per setting. We timestamped the first received Clock and matched the crash on the stereo MAIN USB return, correcting input timestamps by 6.803, 3.900 and 2.449 ms respectively. At 64 frames the mean was {delta:.2f} ms lower than at 256 on this system.

For signal integrity we captured the native 9/10 output and MAIN 11/12 simultaneously. We aligned them once per take, fitted stereo gain, and counted takes with residual steps above 16 counts in 16-bit PCM. A low-level window is 64 consecutive samples with MAIN RMS below 20% of an expected RMS above 30 counts. At both lower sizes the first exact start after reopening showed a discrepancy. The single low-level window at 128 frames lasted 1.45 ms. These are recorded waveform deviations; audibility and their cause remain unverified. No sample clipping or gaps in the callback capture sequence were detected. Injecting a 64-frame mute and a one-sample spike into copies of a clean recording confirmed detector sensitivity. This update adds hardware evidence only.

![Measured MIDI Clock to MAIN latency by actual ASIO callback size](IMAGE_URL)

"""
(d/'pr-section.md').write_text(en,encoding='utf8')
p='chorus-direct-asio-buffers'
zh=f"""### Model 12 直接 ASIO 9/10 的緩衝與音訊完整性

使用上一節的本機整合版本、同一份八小節 S-MU2000 伴奏及 Model 12 USB MIDI → DIN OUT → UM-ONE 實體迴路。Model Mixer Settings Panel 顯示軟體 V2.20 0042、韌體 V1.30 0088、44.1 kHz。原廠面板維持 256 時，SoundCraft 要求 128、64 皆實收 256。調整面板後重開串流，檢查輸入與輸出的每一個擷取區塊。結束時已恢復原有 256，並重新量到雙向 256。

{table(False)}

每檔分兩次開啟串流，每次四次精確起播、兩次晚起播。全部 24 次從 8.000 秒起播都只收到一次銅鈸，12 次從 8.125 秒起播均無補播；36 次 MAIN 回錄都有後續伴奏，與同一參考片段的最低相關係數為 {min(v['later_corr'] for v in rows.values()):.3f}。每次實收 SPP、Continue、144 個 Clock 與 Stop，回錄涵蓋停止後至少一秒。延遲的零點是 UM-ONE 第一個 Clock 的主機時間，以相同銅鈸模板估計 MAIN 起音，逐檔扣除驅動回報的 6.803／3.900／2.449 ms 輸入延遲。表中延遲包含首次起播。64 比本輪 256 平均縮短 {delta:.2f} ms。上輪獨立的 256 對照為 28.07 ms。

音訊完整性以 SoundCraft 剛混好的 9/10 與同時回錄的 MAIN 11/12 做比較。每次固定一個整數取樣位移及一組立體聲增益，再比較全段。任一聲道相鄰樣本的殘差變化超過 16 個 16-bit PCM 單位列為一次有偏差的錄音。每 64 個取樣另查預期 RMS >30、實際 RMS <預期 20% 的視窗。兩項指標可重疊。低緩衝首輪與重開後第一遍都出現波形偏差；不能據此斷定是驅動漏交區塊或演奏時聽得到爆音。所有回錄的診斷區塊序號連續，沒有削波。額外在乾淨錄音副本注入 64 個取樣的靜音與單點 +256 的脈衝，兩者皆成功偵測。本輪使用背景寫檔的雙向診斷版，未量喇叭聲學延遲或長時間演出穩定性。

波形偏差出現於 256 的 {names(256)}；128 的 {names(128)}；64 的 {names(64)}。完整逐次數據含相關值、錄音峰值、殘差與序號。第一次恢復 256 時，測試控制端在開啟裝置階段逾時，未送 MIDI；重新啟動後完成該檔第二批。

![各實際緩衝的逐次起播與波形偏差]({p}/midi-clock-asio-buffer-sizes.png)

[全部逐次數據]({p}/metrics.json) · [分析程式]({p}/measure.py) · [音訊完整性檢查]({p}/quality.py) · [偵測器對照]({p}/detector-controls.json) · [只改主機至 128]({p}/host-128/actual.json) · [只改主機至 64]({p}/host-64/actual.json) · [實收 128]({p}/panel-128/actual.json) · [實收 64]({p}/panel-64/actual.json) · [復原後實收 256]({p}/repeat2-256/actual.json) · [128 疑似瞬斷 MAIN]({p}/repeat-128/exact-a-in.wav) · [對應送出的音訊]({p}/repeat-128/exact-a-out.wav) · [64 晚起播 MAIN]({p}/repeat-64/late-b-in.wav) · [PR #1669](https://github.com/storytold/soundcraft/pull/1669)
"""
report=d.parent/'ROUND4-ACCEPTANCE.zh-TW.md'
assert zh.splitlines()[0] not in report.read_text(encoding='utf-8-sig')
with report.open('a',encoding='utf8') as f:f.write('\n'+zh+'\n')


