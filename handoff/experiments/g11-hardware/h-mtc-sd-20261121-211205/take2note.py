from pathlib import Path
p=Path(r'E:/soundcraft/compatibility-audit/g11-hardware/ROUND4-ACCEPTANCE.zh-TW.md')
data=p.read_bytes()
old='| 2 非零 | 待測 | 待測 | 待測 | 待測 | 待測 | — |'.encode()
new='| 2 非零 | 歌曲 `040208_0005`，00:00:02:00／DIN 65.856 s | 7,904 筆 DIN QF | 起播前停在 96,000 samples，鎖定跟播並跟停至 00:01:07:26；錄音旗標全程 false，輪詢無錯誤 | 待分析 SD | 待測 | — |'.encode()
assert data.count(old)==1
p.write_bytes(data.replace(old,new))
