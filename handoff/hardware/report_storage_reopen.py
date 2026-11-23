"""Compare measured native SDK windows and retain the exact reopen operations."""
from pathlib import Path
import json

from storage_sdk_run import normal_window, np

root=Path(__file__).resolve().parent
run=root/"runs/storage-native-reopen-01"
def read(path):
    return json.loads(path.read_text("utf-8-sig"))

h=read(run/"histograms.json")
m=read(run/"native.json")
finish=read(run/"end.json")
env=read(run/"environment-result.json")
assert env["command_exit"]==0
dtype=np.dtype([("qpc","<i8"),("pos","<u8"),("flags","<i4"),("index","<i4")])
raw=np.fromfile(run/"callbacks.bin",dtype=dtype)
assert len(raw)==finish["callbacks"] and np.all(np.diff(raw["qpc"])>0)
requests=iter(sorted(run.glob("reopen-*.json")))
rows=[]
ops=[]
outcomes=[]
def row(label, values):
    b=values["bins"]
    n=values["intervals"]
    assert sum(b)==n
    timing="／".join(f"{values[k]:.4f}" for k in ("mean_ms","median_ms")) if n else "無間隔"
    rows.append(f"| {label} | {n} | {b[2]} | {b[7]} | {n-b[2]-b[7]} | {timing} |")
row("初始對照",h["baseline"])
for cycle in range(1,4):
    row(f"{cycle}．退出後、重開前",h[f"post-{cycle}"])
    recovered=None
    for mode,label in (("stream","重建雙向串流"),("driver","重載 ASIO 驅動後重建")):
        key=f"after-{mode}-{cycle}"
        if key not in h and not (run/(key+"-error.json")).is_file(): continue
        path=next(requests)
        op=read(path)
        assert op["mode"]==mode
        op_time=(op["done_qpc"]-op["start_qpc"])*1000/m["qpc_hz"]
        ops.append(f"| {cycle} | {label} | {op['pid']} | {op_time:.1f} | {op['sample_rate']}／{op['preferred']} | {op['error'] or '成功'} |")
        if key in h:
            row(f"{cycle}．{label}後",h[key])
            if normal_window(h[key]): recovered=mode
    outcomes.append(recovered)
assert next(requests,None) is None
before_slow=sum(x["intervals"]>0 and x["intervals"]==x["bins"][7] for k,x in h.items() if k.startswith("post-"))
all_wire=all(x["qf"]==960 and x["wire_bound"] for x in h.values())
if not all_wire: raise RuntimeError("Non-wire window needs separate interpretation")
events=[json.loads(line) for line in (run/"environment-during.jsonl").read_text().splitlines()]
endpoint_changes=sum(a[4]!=b[4] for a,b in zip(events,events[1:]))
lines=["# Model 12 退出 USB STORAGE 後重建 ASIO 串流","",
       "2026-11-22。沿用獨立 Steinberg SDK 播放器、TASCAM Model Mixer ASIO、韌體 1.50 0103、原廠 Windows 套件 v2.20。新增的本機控制指令只負責重開，播放及回呼入口計時方式與上一輪相同。整段保持單一程序，12 個輸入及兩個輸出，packed I24。每窗用 UM-ONE 實收的 960 個 quarter-frame 界定約 8 秒，直方圖只計窗內相鄰回呼。","",
       "主測方法為停止 ASIO 串流、釋放緩衝、在同一個驅動實例重建雙向緩衝、重新啟動。若重建後仍失常或 API 失敗，再於同一程序內釋放並重新初始化同一驅動、設回 48 kHz、重建串流重測。當輪在操作員確認回到歌曲畫面後先量舊串流；各段重開由電腦自動執行。","",
       "| 量測窗 | 間隔總數 | 4 至 <7 ms | 240 至 <260 ms | 其他 | 平均／中位數 ms |",
       "|---|---:|---:|---:|---:|---|",*rows,"",
       "| 輪次 | 操作 | 程序 ID | 主機 API 操作用時 ms | 重開時實報 Hz／取樣 | API 結果 |",
       "|---|---|---:|---:|---|---|",*ops,"",
       f"三輪中有 {before_slow} 輪舊串流的所有間隔均落在 240 至 <260 ms。只重建串流即恢復 {outcomes.count('stream')} 輪，另需重載驅動才恢復 {outcomes.count('driver')} 輪，未恢復 {outcomes.count(None)} 輪。判定恢復要求約 8 秒內至少 1,400 個間隔、平均位於名義週期 5.333 ms 的 ±5%、沒有 240–260 ms 間隔，且裝置取樣位置有效並每次增加 256。表中的 API 用時不等於聲音中斷時間。","",
       f"Windows 預設播放端點切換 {endpoint_changes} 次。環境監看有編譯程序的取樣 {sum(bool(e[2]) for e in events)} 個，遠端工作階段取樣 {sum(bool(e[3]) for e in events)} 個。數據用於裝置恢復診斷。","",
       "SoundCraft 整合版的自動重開端點邏輯只接受 WASAPI。播放停滯檢查監看連續 2 秒沒有新增回呼的情況；每 251 ms 仍持續到達的回呼不符合這個條件。本輪測試的是同一個獨立程序內可用的恢復操作。SoundCraft 透過 CPAL 管理雙向 ASIO 串流，尚未驗證產品自行觸發並重建後的結果。","",
       "[回呼直方圖與逐窗核對](runs/storage-native-reopen-01/histograms.json) · [驅動實報](runs/storage-native-reopen-01/native.json) · [擷取與每次重開紀錄](runs/storage-native-reopen-01/) · [保持原串流的對照](ASIO-storage-independent.zh-TW.md) · [SoundCraft 自動恢復路徑](integrated-follow/crates/playback/src/stream_recovery.rs)"]
(root/"ASIO-storage-reopen.zh-TW.md").write_text("\n".join(lines)+"\n",encoding="utf8")
