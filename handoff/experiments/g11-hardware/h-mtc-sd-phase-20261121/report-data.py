from pathlib import Path
import json
d=Path(__file__).resolve().parent
res=json.loads((d/'distribution.json').read_text())
assert len(res['rows'])==10 and res['all']['render']['n']==9
p=d/'REPORT.zh-TW.md';s=p.read_text(encoding='utf-8-sig')
s=s[:s.index('初次方法校準由操作者指定重錄')]
text="""初次方法校準由操作者指定重錄，從統計排除。0011～0020 每首各有一份 CH1 與 CH2 的 SD WAV，原檔均以 SHA-256 核對。0016 的電腦錄製器在端點失效後重新開啟，未涵蓋這首；其餘九首都以同一把主機 QPC 時鐘量到 Windows 播放端與 Model 12 USB 錄音端，並以 CH1 兩個獨立聲音配對。0016 的 2 秒起點依操作者回報。

| SD 歌曲 | 起點 s | SD 的 A4 晚 ms | Windows 播放端相對 DIN 晚 ms | CH1 的 USB 錄音時間原點相對 DIN ms |
|---|---:|---:|---:|---:|
"""
for r in res['rows']:
 val=lambda k:'—' if r[k] is None else f"{r[k]:.3f}"
 text+=f"| {r['song']} | {r['start'] if r['start'] is not None else '2（面板）'} | {val('sd')} | {val('render')} | {val('capture')} |\n"
text+="""
十首 SD 起音的範圍為 +13.896～+56.771 ms，中位數 +52.323 ms，極差 42.875 ms。九首完整分段擷取中，Windows 播放端相對 DIN 的極差已達 43.590 ms。SD 和播放端兩欄逐輪相減的差值只在約 1.5～2.4 ms 間變動。用兩個麥克風標記獨立對齊，USB 輸入時間原點相對 DIN 的九輪極差為 0.353 ms；將 SD 上的鋼琴位置換算成這個 USB 輸入時鐘後，和 Windows 播放端的差值為 31.403～32.256 ms。這是包含回送與擷取時基的合計值。這組試驗將約 43 ms 的跨次變動定位到 Windows 播放端或更早；Model 12 的 SD 錄製、返送、擷取的跨次變化無法解釋該極差。沒有獨立的電氣與取樣時鐘校準，不能從 29.944 ms 的中位數推論 Model 12 本身的絕對發碼延遲。[十輪分布](distribution.json) · [單次四路對照](repeat01/partition.json) · [四首歌頭](series/partition.json) · [五首非零位置](series2/partition.json)

資料顯示 0011 在 Windows 播放端晚 11.583 ms，進出一次 STORAGE 後，0012～0015 均晚 46.454～54.799 ms。後續 2 秒起錄的完整四首晚 47.614～55.173 ms。第三批後半段診斷中，reported_lead_us 為零，lead_clamps 隨回呼增加，表示播放引擎拒用了裝置回報的呈現延遲。這項觀察須以同一時碼輸入主動重開音訊端點才能檢查因果。[逐次呈現延遲診斷](series2-lead.jsonl)
"""
p.write_text(s+text,encoding='utf-8')
