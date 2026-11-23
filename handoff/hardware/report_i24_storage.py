"""Write the local comparison using only complete physical observation windows."""
from pathlib import Path
import json

hw = Path(__file__).resolve().parent
run = hw / "runs/storage-main-i24-01"
def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

current = read(run/"histograms.json")
previous = read(hw/"runs/asio-environment-histogram.json")
env = read(run/"environment-result.json")
assert env["command_exit"] == 0
rows = []
for key, label in zip(("baseline","post-1","post-2","post-3"), ("進入前","第一次退出","第二次退出","第三次退出")):
    for name,s in [("main + #1634", current[key]), ("G-11 + #1634", previous[key]["roll"])]:
        total = s["intervals"]
        normal, slow = s["bins"][2], s["bins"][7]
        other = total - normal - slow
        assert total and total == sum(s["bins"])
        rows.append(f"| {label} | {name} | {total} | {normal} | {slow} | {other} | {s['min_ms']:.3f}／{s['median_ms']:.3f}／{s['max_ms']:.3f} |")
        if name == "main + #1634":
            assert s["wire_bound"] and s["qf"]==960
            assert all(x["meta"]["sample_rate"]==48000 and x["meta"]["buffer"]==256 for x in s["segments"])
samples = [json.loads(s) for s in (run/"environment-during.jsonl").read_text().splitlines()]
changes = sum(a[4] != b[4] for a,b in zip(samples, samples[1:]))
builds = sum(bool(r[2]) for r in samples)
remote = sum(r[3] for r in samples)
lines = [
    "# Model 12 退出 STORAGE 後的 ASIO 回呼對照",
    "",
    "2026-11-22，以同一台 Model 12（1.50 0103）、TASCAM v2.20、48 kHz／256 取樣，在 Windows 本機量測。對照版是 upstream main `85623f28` 與 #1634 `a89e9a4e` 的本機合併 `0d490c68`。相對 main 僅增加 #1634 的五個提交；產品原始碼差異共六檔。G-11 比較組沿用先前的整合版 `f561a57a`。兩版使用相同的 ASIO 底層記錄工具。",
    "",
    "量測同一程序、同一雙向原生 ASIO 串流，取輸出 1 與輸入 9，裝置實報輸入／輸出延遲 304／728 取樣。每輪用 UM-ONE 實收 960 個 MTC quarter-frame 的首末時間界定約 8 秒觀測窗。對照版由本機走帶播放，G-11 版由 MTC 驅動走帶。觀測值是相鄰 ASIO 回呼的主機時間差。三次 STORAGE 之間保持程式開啟，無手動重新連線；這三輪不能當成三次獨立冷啟動。",
    "",
    "| 階段 | 版本 | 間隔數 | 4 至 <7 ms | 240 至 <260 ms | 其他 | 最小／中位／最大（ms） |",
    "|---|---|---:|---:|---:|---:|---|",
    *rows,
    "",
    "兩組均在進 STORAGE 前呈現約 5 ms、退出後三個觀測窗呈現約 251 ms 的回呼節奏。對照版沒有 G-11，足以排除 G-11 為重現此現象的必要條件。兩組共用 #1634、ASIO 後端、Windows、TASCAM 驅動與裝置；本次無法進一步分開歸因。未合入 #1634 的 main 已實測退到 I24 靜音，無可比的原生回呼。",
    "",
    f"Windows 預設播放端點在整段切換 {changes} 次；監看記錄中，出現編譯程序的取樣有 {builds} 個、遠端桌面取樣有 {remote} 個，CPU 最高 {max(r[1] for r in samples):.1f}%。環境檢查因此排除本輪作一般效能驗收，保留作裝置恢復診斷。名義緩衝週期為 5.333 ms；四個觀測窗內回呼序號連續，裝置取樣位置每次仍只增加 256。",
    "",
    "[原始回呼分布](runs/storage-main-i24-01/histograms.json) · [對照版原生裝置設定](runs/storage-main-i24-01/driver/epoch-0.json) · [環境監看](runs/storage-main-i24-01/environment-result.json) · [G-11 版原始分布](runs/asio-environment-histogram.json) · [前次環境診斷與純 main 實測](ASIO-environment.zh-TW.md)",
]
(hw/"ASIO-storage-main-I24.zh-TW.md").write_text("\n".join(lines)+"\n", encoding="utf8")
