from pathlib import Path
import csv,re
base=Path(__file__).parent
read=lambda p:(base/p).read_text(encoding='utf-8-sig')
slow=list(csv.DictReader((base/'slowdown-summary.csv').open()))
assert len(slow)==36 and all(r['missing']==r['duplicates']==r['bad']=='0' for r in slow)
peak=max(int(r['off']) for r in slow if r['policy']=='predict');assert peak==4152
out='Across both policies the slowdown sweep verified 58,752 attacks and their complete waveforms. An initial projection implementation muted 201 sampler notes and damaged 28 tails on the return from a slowdown. Keeping overdue MIDI events ordered when prediction resumes removed all 229 failures. The selected policy’s first offbeat spanned −25.000 to +86.500 ms, and the next beat −25.000 to +83.771 ms. The −25.000 ms attack was already in the device queue before an old-rate pulse first became overdue. The largest positive error occurred at 300 BPM, 2,048 frames and 50 ms lead after falling back to the wire limit.'
zh='兩種策略各驗證 29,376 個起音及完整波形，共 58,752 聲。初版預測在減速後重新啟用時，會把逾期的起音與放鍵擠到同一取樣；這輪掃描抓到 201 個帽鈸整聲消失，另有 28 個波形受損。保留逾期事件的順序後，全矩陣漏音、重複、截尾均為 0。採用新策略，第一次反拍分布 −25.000～+86.500 ms，下一拍 −25.000～+83.771 ms。早 25 ms 的那一音，在第一個應到的慢 pulse 能被辨識之前就已經交付。最晚值發生在 300 BPM、2048 取樣、50 ms 提前量，由於已回到硬上限而延後，並非全部都來自驅動。'
doc=read('measurement-template.md').replace('{{PACKETS}}',read('packet-matrix.md')).replace('{{DEVICE}}',read('matrix.md')).replace('{{DEVICE_RESULT}}',out)
txt=read('local-template.md').replace('{{PACKETS}}',read('packet-matrix.md')).replace('{{DEVICE}}',read('matrix.md')).replace('{{DEVICE_ZH}}',zh)
import sys
if len(sys.argv)>1:
    log=read('validated-integrated-tests.log')
    counts=re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored',log)
    assert len(counts)==3
    passed=sum(int(t[0]) for t in counts)
    assert 'Finished' in read('release-clippy.log')[-800:] and not re.search(r'^error',read('release-clippy.log'),re.M)
    summary=f'Windows 上 mix、playback 與 UI 的 library tests 合計 {passed} 項通過。另行啟用 A-4 四組 10 分鐘測試、96 相位的裝置矩陣及八小時 profile。這三個 crate 的 Clippy（lib、tests、--no-deps、-D warnings）通過；engine 原有 autosave.rs:481 警告仍可見。'
    txt=txt.replace('{{TESTS_ZH}}',summary+'[整合測試](validated-integrated-tests.log) · [Clippy](release-clippy.log) · [穩速 p95](steady-gate.log) · [第一版穩定預測在推速時的紅測](prediction-ramp-red.log) · [交接漏音紅測](lead-data/handoff-note-red.log)')
    (base/'REPORT.zh-TW.md').write_text(txt,encoding='utf8')
p=base/'integration/docs/external-clock-response-measurements.md'
p.write_text(doc,encoding='utf8')
