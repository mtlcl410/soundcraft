from pathlib import Path
import json,statistics,datetime
root=Path(__file__).resolve().parent
runs=root/'runs'
def load(p): return json.loads(p.read_text('utf-8-sig'))
rows=[];invalid=[];midi=[]
for d in sorted(runs.iterdir()):
    result=d/'environment-result.json'
    if not result.exists():continue
    r=load(result)
    if not r['environment_valid']:
        invalid.append(f"- {d.name}：{', '.join(r['reasons'])}。")
        continue
    stats=d/'data/m2-result.json'
    if stats.exists():
        z=load(stats);t=z['path_delay'];j=z['absolute_jitter_around_median'];ports=load(d/'data/ports.json')
        midi.append(f"| {ports['send']} → {ports['receive']} | {z['pairs']} | {t['median_ms']:.4f} | {t['p99_ms']:.4f} | {t['max_ms']:.4f} | {j['median_ms']:.4f} / {j['p99_ms']:.4f} / {j['max_ms']:.4f} |")
    if not d.name.startswith(('m1-independent','m1-soundcraft','m1-integration')):continue
    docs=[load(p) for p in sorted(d.glob('take-*/summary.json'))]
    if not docs:continue
    vals=[v for s in docs for v in s['offsets']];md=docs[0]['driver']
    assert all(s['reported_samples']==docs[0]['reported_samples'] for s in docs)
    a,b=min(vals),max(vals); reported=docs[0]['reported_samples']
    passed='預演' if len(docs)!=20 else ('通過' if b-a<=1 else '未達門檻')
    rows.append(f"| {d.name} | {md['buffer']} | {len(docs)} | {a}–{b} | {b-a} | {md['input_latency']} + {md['output_latency']} | {a-reported:+d} 至 {b-reported:+d} | {passed} |")
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
text=f"""# G-11 實機驗收（Model 12 韌體 1.50 0103）

**效能驗收暫停。** 退出 STORAGE 後的 ASIO 回呼異常只供環境診斷；下列原始門檻判讀保留為當時量測紀錄。[驅動版本、main 對照、回呼分布及 #1663 重新定位判定](ASIO-environment.zh-TW.md)

更新於 {now}。操作員確認本機、48/24、OUTPUT DELAY 為 DISABLE，USB 路由經面板照片核對。Windows 重插後同時列出 Model 12 與 UM-ONE。各輪環境紀錄與原始 PCM／事件檔在 [runs](runs/)。

| PR | 實測用程式碼基準 | 規定項目 |
|---|---|---|
| #1662 | 8fd15068 | H-1、H-2、H-3 |
| #1663 | bab99312 | H-4 |
| #1669 | 33dfa5f5 | H-5、H-6、H-7、H-9 |
| 三支 | 上列版本 | H-8、H-10 |

## M-1　USB 1/2 經 CH9/10 回錄

同一 ASIO callback 觀測輸出 1、輸入 9，使用每次六個不同的低振幅脈衝序列，逐個互相關。驗證 ASIO 連續取樣位置與回呼序號，每個緩衝目標獨立開串流 20 次。48 kHz，通過門檻為極差 ≤ 1 取樣。差額為實測減驅動回報，保留正負號。

| 量測組 | 緩衝 | 有效次數 | 往返取樣 | 極差 | 回報輸入 + 輸出 | 差額 | 判定 |
|---|---:|---:|---:|---:|---:|---:|---|
"""+'\n'.join(rows)+"""

## SoundCraft 目前版本的 ASIO 狀態

#1662 的 8fd15068 已實際啟動並透過正常音訊設定指令選取 Model Mixer ASIO。128、256、512 取樣全部退到靜音，三份 application.log 都記錄 unsupported device sample format I24，相同連線上的獨立播放器有聲音資料。Packed I24 由尚未合併的 [#1634](https://github.com/storytold/soundcraft/pull/1634) 處理。原 head 下可報告啟動失敗，無法計算 SoundCraft 音訊往返。此結果及獨立基準已放入 [#1662 實機留言](https://github.com/storytold/soundcraft/pull/1662#issuecomment-7078832958)。[測法與無效嘗試說明](前置紀錄.zh-TW.md)

## M-2　雙向 DIN 延遲

原始 QPC 從主機送出呼叫到另一介面輸入回呼。每個方向單獨計時，各自 10,000 個 F8；jitter 為相對中位延遲的絕對差。初探每方向各 4 個，兩向均經一般 Model 12 MIDI 埠全部到達；MIDIIN2／MIDIOUT2 均為 0/4。原始檔在 [routes.json](runs/m2-identify-a/routes.json)。

| 實際方向 | F8 數 | median ms | p99 ms | max ms | jitter median / p99 / max ms |
|---|---:|---:|---:|---:|---:|
"""+'\n'.join(midi)+"""

## 待驗項目

各項結果依下方實測記錄更新。H-1、H-2、H-3a、H-4a、H-5～H-10 仍需完整驗收。H-6 的錄音差額及追蹤 issue 草稿須待實測；H-8 目前不能填入 SoundCraft 排程誤差。SD、選用的 PC1X 和 USB 拔插集中在一次手動操作。

## 無效嘗試

"""+'\n'.join(invalid)+'\n'
supplement=root/'本機整合版.zh-TW.md'
if supplement.exists():
    text+='\n'+supplement.read_text(encoding='utf8')
m3=runs/'m3-sd-01'
if (m3/'pc-markers.json').exists() and (m3/'environment-result.json').exists():
    pc=load(m3/'pc-markers.json')
    valid=load(m3/'environment-result.json')['environment_valid']
    text+='\n## M-3　SD 錄音與 USB 同步回錄\n\n'
    text+=f"測試使用 Model Mixer ASIO、48 kHz、256 取樣。操作員確認 CH9/10 的 REC 燈常亮且本體計數前進。電腦記錄的環境為{'有效' if valid else '無效，本次資料只能供診斷'}。"
    text+=f"輸出 1 辨認到 {pc['output_codes']} 個已知標記，輸入 9 辨認到 {pc['input9_codes']} 個。兩端共同辨認 {pc['matched']} 個，首末間隔 {pc['matched_span_s']:.6f} 秒，往返 {pc['min_loop_samples']}–{pc['max_loop_samples']} 取樣。"
    text+=f"量測區間的 ASIO 取樣位置中斷 {pc['measurement_gaps']['position']} 次，回呼序號中斷 {pc['measurement_gaps']['sequence']} 次。[逐標記檢查摘要](runs/m3-sd-01/pc-markers.json)\n\n"
    if (m3/'sd-drift.json').exists():
        sd=load(m3/'sd-drift.json')
        text+=f"SD 與 USB 共同標記 {sd['matched']} 個，跨越 {sd['span_s']:.6f} 秒。SD 減 USB 的首末間距差 {sd['sd_minus_usb_samples']:+d} 取樣（{sd['sd_minus_usb_ppm']:+.3f} ppm），與 Windows QPC 的端點差折合 {sd['sd_minus_host_ppm']:+.3f} ppm。SD 和 USB 來自同一台 Model 12；QPC 端點亦包含回呼到達抖動。[SD 與 USB 配對](runs/m3-sd-01/sd-drift-pairs.csv)\n"
    else:
        text+='SD WAV 待 STORAGE 階段唯讀複製與比對。時鐘漂移尚待 SD 標記證實。\n'
    if (m3/'sd-drift-pairs.csv').exists():
        import csv
        with (m3/'sd-drift-pairs.csv').open(newline='') as paired:
            data=list(csv.DictReader(paired))
        if data:
            out_offsets=[int(x['sd'])-int(x['asio_output']) for x in data]
            in_offsets=[int(x['sd'])-int(x['asio_input9']) for x in data]
            changes=[f"{x['code_index']}（{after-before:+d}）" for x,before,after in zip(data[1:],in_offsets,in_offsets[1:]) if before!=after]
            text+=f"\n逐一比對全部 {len(data)} 個標記，SD 對 ASIO 輸出 1 的相對距離極差為 {max(out_offsets)-min(out_offsets)} 取樣。SD 對 USB 輸入 9 的距離變動發生在標記 {', '.join(changes)}，括號內為取樣數。首末差換算的 ppm 是全段平均值，五次跳變的原因尚待確認。[SD 原檔校驗](runs/m3-sd-01/sd/040209_0002/manifest.json)\n"
from hardware_tables import tables
(root/'REPORT.zh-TW.md').write_text(text+tables(root),encoding='utf8')
