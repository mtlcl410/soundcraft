from pathlib import Path
p=Path(r'E:/soundcraft/compatibility-audit/g11-hardware/ROUND4-ACCEPTANCE.zh-TW.md')
with p.open('r',encoding='utf8',newline='') as f:s=f.read()
nl='\r\n' if '\r\n'in s else '\n'
old='| 3 拔線 | 待測 | 待測 | 待測 | 待測 | 待測 | 待聽 |'
assert s.count(old)==1
new='| 3 拔線 | 歌曲 `040208_0006`，歌頭／DIN 65.456 s | DIN 7,405 筆 QF，USB 7,856 筆 | 鎖定、失碼後停播、接回重新鎖定、跟停至 00:01:05:15；錄音旗標全程 false，輪詢無錯誤 | CH2 WAV 為空 | 無法量測 | 操作者不確定 |'
s=s.replace(old,new).replace('| 待分析 SD | 待測 | — |','| CH2 WAV 為空 | 無法量測 | — |')
anchor='三輪極差與最終判定待填。'
assert s.count(anchor)==1
extra='補查：`040208_0005` 與 `040208_0006` 的 CH1、CH2 WAV 都只有檔頭（0 frames），各首 MAIN 的 L/R 有資料。操作者在第一、二輪均聽到鋼琴。第三輪 DIN 中斷 3,616.53 ms，SoundCraft 在最後一筆有效 QF 後 267.28 ms 的輪詢觀測到 8/8、停止；恢復訊號後 316.83 ms 的輪詢觀測到 Locked。之後還有一次 158 ms 的短中斷。USB 路徑持續收碼。第三輪 SD MAIN 在第 19–22 秒低於正常輪，23 秒起音恢復；此為波形觀察，是否聽到接回跳音由聽者判讀。此輪比指定的約 1 秒中斷長。保留參考，但偏差比較需要重錄獨立音軌。[第二輪 SD 清單](h-mtc-sd-20261121-211205/take2-sd.json) · [第三輪 SD 清單](h-mtc-sd-20261121-211205/take3-sd.json) · [斷線與重新鎖定診斷](h-mtc-sd-20261121-211205/take3-mtc.json) · [接回前後的 SD MAIN 原聲](h-mtc-sd-20261121-211205/take3-main-relock-listen.wav)。'
s=s.replace(anchor,anchor+nl+nl+extra)
with p.open('w',encoding='utf8',newline='') as f:f.write(s)
