"""Report measured windows only; preserve an empty window as missing evidence."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
run = root/"runs/storage-native-sdk-01"
def load(path):
    return json.loads(path.read_text("utf-8-sig"))

native=load(run/"histograms.json")
control=load(root/"runs/storage-main-i24-01/histograms.json")
g11=load(root/"runs/asio-environment-histogram.json")
start=load(run/"device-start.json")
end=load(run/"end.json")
env=load(run/"environment-result.json")
assert env["command_exit"]==0 and end["sample_rate"]==48000 and end["preferred"]==256
rows=[]
for key,label in zip(("baseline","post-1","post-2","post-3"),("進入前","第 1 次退出","第 2 次退出","第 3 次退出")):
    for host,data in (("獨立 SDK",native[key]),("main + #1634",control[key]),("G-11 + #1634",g11[key]["roll"])):
        bins,n=data["bins"],data["intervals"]
        assert sum(bins)==n
        timing="/".join(f"{data[field]:.3f}" for field in ("min_ms","median_ms","max_ms")) if n else "無間隔"
        rows.append(f"| {label} | {host} | {n} | {bins[2]} | {bins[7]} | {n-bins[2]-bins[7]} | {timing} |")
timeline=[json.loads(s) for s in (run/"environment-during.jsonl").read_text().splitlines()]
changes=sum(x[4]!=y[4] for x,y in zip(timeline,timeline[1:]))
slow=sum(d["bins"][7] for k,d in native.items() if k!="baseline")
total=sum(d["intervals"] for k,d in native.items() if k!="baseline")
matched=all(native[f"post-{i}"]["intervals"]>0 and native[f"post-{i}"]["bins"][7]==native[f"post-{i}"]["intervals"] for i in range(1,4))
verdict=("三個退出後的觀測窗均重現持續慢速回呼。SoundCraft、#1634、G-11 和 Rust 的 ASIO 封裝都不是重現的必要條件。"
         if matched else "三輪未全部重現同一分布，依逐輪數字判讀。")
wire=[d["qf"] for d in native.values()]
assert all(d["wire_bound"] for d in native.values()) and all(n==960 for n in wire)
gaps=sum(d["position_jumps"] for d in native.values())
invalid=sum(d["invalid_position"] for d in native.values())
duplicate=sum(d["buffer_index_repeats"] for d in native.values())
report=[
    "# 退出 USB STORAGE 後的原生 ASIO 回呼：三個播放程式對照","",
    f"{verdict} 退出後落在 240 至 <260 ms 的間隔合計 {slow}/{total}。本輪只判定持續開啟的串流遇到 STORAGE 後的回呼節奏。","",
    "## 裝置與測法","",
    "同一台 TASCAM Model 12，韌體 1.50 0103、原廠 Windows 套件 v2.20，USB 1/2 回到 CH9/10。獨立 C++ 播放器由 Steinberg ASIO SDK 直接載入原廠 us_asio.dll。程序清單未見 SoundCraft，建置命令沒有連結 CPAL、asio-sys 或 #1634。輸出低電平 A4 測試聲；在 buffer-switch 入口讀 QPC，預留記憶體暫存時間戳，檔案寫入在主執行緒。前兩版用的是 asio-sys 內的 QPC 記錄點，兩種測法皆取連續回呼的牆鐘間隔。","",
    f"ASIO 實報 {start['sample_rate']:,} Hz，偏好與開啟的 buffer 均為 {start['buffer_frames']} 取樣，packed I24，{start['inputs']} 進、{start['outputs_open']} 出；驅動回報延遲 {start['input_latency']}/{start['output_latency']} 取樣。每輪依 UM-ONE 收到首末 quarter-frame 界定約 8 秒，四窗各收齊 960 筆。每窗只計其內的相鄰間隔；不含進出選單的過渡段。三次都用同一程序與原串流，不主動重開。","",
    "| 階段 | 播放程式 | 間隔數 | 4 至 <7 ms | 240 至 <260 ms | 其他 | 最小／中位／最大 ms |",
    "|---|---|---:|---:|---:|---:|---|",*rows,"",
    f"獨立播放器四個觀測窗內，無效取樣位置 {invalid} 次、位置增量不等於 256 有 {gaps} 次、雙緩衝索引未交替 {duplicate} 次。Windows 預設播放端點在整段切換 {changes} 次；監看中出現編譯程序 {sum(bool(r[2]) for r in timeline)} 次、遠端工作階段 {sum(bool(r[3]) for r in timeline)} 次。","",
    "三輪退出是同一條串流上的連續操作，不是三次獨立冷啟動。這個設計沒有分離韌體、驅動、Windows USB／裝置切換及用戶端是否重建串流的影響；數據不作正常播放延遲或實際喇叭延遲使用。","",
    "[獨立播放器逐輪直方圖](runs/storage-native-sdk-01/histograms.json) · [原生回呼時間戳](runs/storage-native-sdk-01/callbacks.bin) · [驅動實報](runs/storage-native-sdk-01/native.json) · [載入的 DLL](runs/storage-native-sdk-01/loaded-client.json) · [環境紀錄](runs/storage-native-sdk-01/environment-result.json) · [前兩版原始對照](ASIO-storage-main-I24.zh-TW.md)"
]
tail = load(run/"continuous-tail.json")
report.extend(["", f"從第一次出現 ≥200 ms 間隔一路算到第 3 次觀測窗結束，共 {tail['duration_s']:.3f} 秒。{tail['intervals']} 個連續間隔中有 {tail['slow']} 個在 240 至 <260 ms，最小 {tail['min_ms']:.3f}、最大 {tail['max_ms']:.3f} ms。[連續時間序列統計](runs/storage-native-sdk-01/continuous-tail.json)"])
(root/"ASIO-storage-independent.zh-TW.md").write_text("\n".join(report)+"\n",encoding="utf8")
