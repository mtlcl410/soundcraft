from pathlib import Path
from collections import defaultdict
import csv,sys
D=Path(__file__).resolve().parent
def read(f):
 with (D/f).open(encoding='utf-8-sig') as h:return list(csv.DictReader(h))
def table(rows):
 return '\n'.join('| '+' | '.join(map(str,r))+' |' for r in [rows[0],['---']*len(rows[0]),*rows[1:]])
cases={r['case']:r for r in read('cases-isolated.csv')}
assert len(cases)==109
notes=read('notes-isolated.csv');states=read('transitions.csv')
groups=defaultdict(list); percase=defaultdict(list); transitions=defaultdict(list)
for row in notes:percase[row['case']].append(row)
for r in states:transitions[r['case']].append(r)
for name,r in cases.items():groups[name.split('_')[0]].append(r)
cols=['項目','實例','預期音數','配對','漏音','重複','超過來源末位置的音','已證實波形不同','最大早／晚 ms','大變速通報','實際 F8 期間失鎖']
def gv(r,k):return int(r[k])
def rng(vals):return f'{min(vals,default=0):+.3f} / {max(vals,default=0):+.3f}'
def summarize(title,rows):
 vals=[float(e['error_ms']) for r in rows for e in percase[r['case']] if e['error_ms'] and int(e['eighth'])*12>=int(r['cut_pulse'])]
 return [title,len(rows),*[sum(gv(r,v) for r in rows) for v in ('expected','matched','missing','duplicates','after_last_f8_extra','damaged')],rng(vals),sum(gv(r,'steps') for r in rows),sum(gv(r,'dropouts_before_terminal') for r in rows)]
out=['# DJ 情境 PCM 測試（本機）','', '版本 c093aedb，48 kHz，128 samples，30 ms grid guard。來源為理想 F8，音符每八分音符一個，使用 每一個音都使用不同的力度（120 種參考）識別的 96-sample 原生取樣器波形。同一個力度的參考用 MixEngine 實際渲染，逐取樣比對起音至尾音。符號為實際減參考，負值表示早。','',table([cols]+[summarize(k,v) for k,v in groups.items()]+[summarize('所有短情境',cases.values())]),'']
out+=['## 短推拉、微幅搖晃、階梯與衝刺','','短推拉按絕對時間精確切換，跨越邊界的 F8 按音樂相位積分計算。階梯每拍乘 1.01 或 0.99，抵達端點時截到 132／120。搖晃為以牆鐘定義的正弦，4 組各觀察 8 小節。衝刺有兩條參考曲線，分別是按拍線性增加 BPM 及二次曲線增加 BPM，8 小節後直接切回 128。','',table([['情境','早／晚 ms','步階通報','drop 第一反拍／下一拍 ms']]+[[r['case'],rng([float(e['error_ms']) for e in percase[r['case']] if e['error_ms'] and int(e['eighth'])*12>=int(r['cut_pulse'])]),r['steps'], ' / '.join(e['error_ms'] for e in percase[r['case']] if int(e['eighth']) in (97,98)) if r['case'].startswith('sprint_') else '—'] for group in ['nudge','wobble','stair','sprint'] for r in groups[group]]),'']
out+=['## 倍速／半速','','cut 為第 384 或 396 個 pulse，分別對應小節線和拍子中間。所有以下偏差均以音樂位置配對。','',table([['情境','第一個反拍 ms','下一個正拍 ms','最大絕對 ms','漏／重／波形不同']]+[[r['case'],r['first_off_ms'],r['first_beat_ms'],r['peak_affected_ms'],'/'.join(r[k] for k in ('missing','duplicates','damaged'))] for r in groups['ratio']]),'']
out+=['## 8% 門檻','','向上及向下各 10 次；改變的位置從第 384 到 393 個 F8，每次相對八分音符的相位不同。通報計數為在實際 F8 上觀察 step_intervals；偏移量依 BPM 百分比。','']
edge=defaultdict(list)
for r in groups['edge']:edge[r['case'].rsplit('_',1)[0]].append(r)
def seen_steps(r):return [int(t['pulse'])-int(r['cut_pulse']) for t in transitions[r['case']] if t['kind']=='F8' and int(t['step_intervals'])>0]
out.append(table([['門檻','通報實例 / 10','確認間隔（F8）','確認總次數','最大絕對 ms','第一反拍最早／最晚 ms']]+[[k,sum(bool(int(r['steps'])) for r in v),str(sorted(set(i for r in v for i in seen_steps(r)))),sum(int(r['steps']) for r in v),max(float(r['peak_affected_ms']) for r in v),rng([float(r['first_off_ms']) for r in v if r['first_off_ms']])] for k,v in edge.items()]))
out+=['','## 煞車、明確 Stop、靜默與速度恢復','','每個 F8 更新一次來源速度，1 或 2 拍由 128 降到 5 BPM，最後一個實際間隔 500 ms。遇到大於 75 ms 的長間隔，用每毫秒一次的 host poll 查真正的 timeout。stop 在末 F8 後 3 ms 發 FC；silent 在末 F8 後保持 3 秒靜默；rise 在末 F8 後立即回到 128 並持續 8 拍。clip 在末 F8 的音樂位置之後還留有 4 個未被來源指定時間的八分音符。下表「額外」是這些音符實際響起的數目，可能早於末 F8；一拍煞車的 Coast 在明確 Stop 之前已播放下一個未指定音符（比末 F8 早 397.833 ms）；Coast 在真正靜默後繼續出聲本來就是政策，不能一律當成重複。Stop on loss 產生的早停與後續漏音則逐項記錄。','']
def breakgap(r):
 p=[t for t in transitions[r['case']] if t['state'] in ['Coasting','Stopped'] and int(t['dropouts'])>0 and int(t['at_us'])*48//1000<=int(r['terminal_sample'])]
 if not p:return '—'
 x=p[0];return f"{x['ms_since_previous_f8']} ms (p{x['pulse']})"
out.append(table([['情境','首次來源仍在走時失鎖','F8 期間／總掉鎖','漏音','額外','波形不同','末狀態','最大已配對偏差 ms']]+[[r['case'],breakgap(r),r['dropouts_before_terminal']+'/'+r['dropouts_total'],r['missing'],r['after_last_f8_extra'],r['damaged'],r['last_state'],r['peak_affected_ms']] for r in groups['brake']]))
out+=['','## 原始記錄與判讀','','- [逐八分音符紀錄](notes-isolated.csv) 有參考與實際 sample、帶符號 ms、尾音長度及 waveform_match。missing 沒有可量偏差。','- [所有實例](cases-isolated.csv)、[時脈狀態及確認記錄](transitions.csv)、[每一個輸入 F8 的時間](stimulus.tsv)。','- 大變速通報來自 packet 本身的 step_intervals；微幅推拉、搖晃、階梯都未跨 8% 的單次門檻，這些模式的通報才算誤觸。所有 109 個短情境都沒有加輸入抖動。','- 測試不涉及音效卡、驅動或聽感；離線渲染使用與 PR 單元測試相同的 MixEngine、輸入和網格更新流程。所有正常結束或回升的案例都在最後一音後另送 24 個不計分的 F8，避免把晚到的尾音截掉。Stop 由 host 收到實際 transport action 後結束拉取音訊；這無法驗證音訊裝置停止的殘響或實體輸出延遲。超過 ±10／4 ms 的判讀僅套用歷來約定的理想突變矩陣，其他型態保留實測值。','']
(D/'DJ-RESULTS.zh-TW.md').write_text('\n'.join(out),encoding='utf-8')
append="""
## 重疊起音與尾音

兩拍煞車、實際停送、Coast 的 115-sample 連續訊號中有兩顆不同的音。只改其中一音的 MIDI 力度一級再渲染，逐 sample 相減。第 37、38 音的起點分別是 560,732、560,751，差 19 samples（0.396 ms），各自對 PCM 的影響都維持 96 samples。第 39、40 音亦分別確認。這四音都超過最後 F8 的音樂位置，沒有重複，重疊兩音不列入逐音波形相等的分母。一拍煞車後 Coast 的第 34 音比來源早 759.646 ms，三種終點皆在同一 sample 起音，維持完整 96 samples，首 15 samples 與參考一致、後 81 samples 不同（幅度差峰值 0.028381）。其他已配對的指定音均與完整 96-sample 參考一致。本輪沒有聽感判定。[力度差分驗證](differential/velocity-isolation.csv)

## 涵蓋的測試判準

理想來源倍速、半速採先前的 10 / 4 ms 目標。±2～5% 推拉和正弦、階梯，以未誤觸大變速、音符完整為判準，偏差作為測量值。真正起音共 5,758 個已配對音及 9 個超過來源末位置的音；額外 9 音中 4 個出現在一拍煞車的真實靜默／Coast、4 個出現在兩拍煞車的真實靜默／Coast、1 個在一拍煞車且之後發明確 Stop 的輸出。32 個紅色子案例（含對同一現象的重複判準）詳見本機記錄，不等於 32 個獨立問題。[斷言紀錄](acceptance.log)

門檻邊緣在第 4 個 F8 檢查時，長窗已含改速後的 3 個間隔。第 1 次 ±8.0% 試驗相對更新後的長窗只剩 −7.9918%／+7.9922%，低於門檻。±8.1% 仍有 8.0923%／8.0923%。用相同輸入獨立重算 192 點回歸的結果見[第四個 F8 的數據](edge-fourth-f8.csv)。數字為此 head 及此時戳相位下的觀測。
"""
with (D/'DJ-RESULTS.zh-TW.md').open('a',encoding='utf8') as h:h.write(append)
print(table([cols]+[summarize(k,v) for k,v in groups.items()]))
