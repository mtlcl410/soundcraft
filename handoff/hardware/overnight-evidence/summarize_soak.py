import csv,json,sys
from pathlib import Path
from bisect import bisect_left
from statistics import median
p=Path(sys.argv[1])
def stamps(name,key,kind):
    with (p/name).open() as f:
        return [int(r[key]) for r in csv.DictReader(f) if r['hex'].startswith(kind)]
def spread(v):
    v=sorted(v);return dict(p50=median(v),p99=v[(len(v)*99+99)//100-1],minimum=v[0],maximum=v[-1])
def analyze():
    result=json.loads((p/'result.json').read_text())
    wire=stamps('ingress.csv','at_ns','f8');out=stamps('egress.csv','at_ns','f8')
    qf=stamps('egress.csv','at_ns','f1')
    # Estimate startup displacement independently of final counts. Then count
    # and compare only the FIRST and LAST complete common ten-minute windows.
    i=bisect_left(wire,out[0]); i=min(range(max(0,i-1),min(len(wire),i+2)),key=lambda k:abs(wire[k]-out[0]))
    start_index = i
    n=min(len(out),len(wire)-i); width=min(28800,max(1,n//2-48)); guard=48
    head=[(out[k]-wire[k+i])/1e6 for k in range(guard,guard+width)]
    tail=[(out[k]-wire[k+i])/1e6 for k in range(n-width-guard,n-guard)]
    state=[json.loads(l) for l in (p/'state.jsonl').read_text().splitlines()]
    win=min(600,len(state)//2)
    early=median(s['private_bytes'] for s in state[:win]);late=median(s['private_bytes'] for s in state[-win:])
    summary=dict(seconds=result['seconds'],strict_pass=False,expected_clock=result['expected_clock'],clock=len(out),expected_qf=result['expected_qf'],qf=len(qf),qf_discontinuities=result['discontinuous_qf_pieces'], observed_dropouts=result['dropout_count'], counted_window_pulses=width, first_output_closest_ingress_index=i,phase_head_ms=spread(head),phase_tail_ms=spread(tail),drift_median_ms=median(tail)-median(head),private_bytes_first_window_median=early, private_bytes_last_window_median=late, private_bytes_delta=late-early, max_egress_observer_queue=result['output_capture_queue_max'],relay_delay_ms=result.get('added_ms'))
    summary['counts_match']=(len(out)==result['expected_clock'] and len(qf)==result['expected_qf'])
    summary['observer_queue_windows']={name:spread([s['drain_q'] for s in samples]) for name,samples in [('head',state[:win]),('tail',state[-win:])]}
    summary['queue_scope']='Egress observer depth sampled once per status poll. Internal scheduler queue growth is not directly instrumented.'
    # An unattended pass on memory/drift needs declared tolerances; retain raw numbers.
    source=stamps('source.csv','send_ns','f8')
    physical=stamps('relay.csv','arrival_ns','f8')
    def intervals(st):
        gaps=[(later-early)/1e6 for early,later in zip(st,st[1:])]
        return dict(p50_ms=median(gaps),p99_ms=sorted(gaps)[(len(gaps)*99+99)//100-1],max_ms=max(gaps),
                    over_150ms=sum(g>150 for g in gaps),index_of_largest=gaps.index(max(gaps)))
    summary['physical_gap_distributions']={label:intervals(ts) for label,ts in [('sender',source),('din',physical),('software_ingress',wire),('return_clock',out),('return_qf',qf)]}
    deadline=stamps('source.csv','due_ns','f8')
    summary['reference_max_dispatch_late_ms']=max(s-t for s,t in zip(source,deadline))/1e6
    if len(source)==len(physical)==len(wire):
        summary['largest_source_gap_by_stage']=[]
        for i in sorted(range(len(source)-1),key=lambda k:source[k+1]-source[k],reverse=True)[:8]:
            summary['largest_source_gap_by_stage'].append(dict(ordinal=i,sender_ms=(source[i+1]-source[i])/1e6,din_ms=(physical[i+1]-physical[i])/1e6,ingress_ms=(wire[i+1]-wire[i])/1e6))
    summary['strict_pass']=False if not summary['counts_match'] or result['dropout_count'] or result['discontinuous_qf_pieces'] else None
    summary['ordinal_drift_interpretable'] = bool(summary['counts_match'] and not result['dropout_count']
        and not result['discontinuous_qf_pieces'] and not summary['physical_gap_distributions']['sender']['over_150ms'])
    interpretation = ('首末窗可按相同序號比較。' if summary['ordinal_drift_interpretable']
        else '輸入空檔、失鎖或邊界計數差會改變序號映射。此處列出的相位差僅供追查，不能當作累積時鐘漂移。')
    stages=summary['physical_gap_distributions']
    from wire_boundaries import data
    (p/'edge-analysis.json').write_text(json.dumps(data(p),indent=2))
    (p/'window-analysis.json').write_text(json.dumps(summary,indent=2))
    (p/'RESULT.zh-TW.md').write_text(f"""# 同時收發 Clock 與 MTC 的硬體長測

實測 {summary['seconds']} 秒。Clock 收到 {len(out)}/{result['expected_clock']}；MTC quarter-frame 收到 {len(qf)}/{result['expected_qf']}，piece 次序跳號 {result['discontinuous_qf_pieces']} 次，跟隨失鎖計數 {result['dropout_count']}。

按第一次 Clock 的實體收發時間配對，起點相差 {start_index} 個輸入 pulse。扣除首尾各一秒邊界後，每個視窗使用 {width} 個 pulse。首段中位相位 {median(head):+.3f} ms，末段 {median(tail):+.3f} ms，兩窗差 {median(tail)-median(head):+.3f} ms。{interpretation} 程序 private bytes 的前後視窗中位數差 {late-early:+.0f} bytes。

各段最大 F8 間隔為送碼工具 {stages['sender']['max_ms']:.3f} ms、第一段 DIN 收件 {stages['din']['max_ms']:.3f} ms、轉送後輸入 {stages['software_ingress']['max_ms']:.3f} ms、實體 Clock 輸出 {stages['return_clock']['max_ms']:.3f} ms。各自的最大值可能來自不同 pulse；JSON 另列送端最長八個空檔在相同 ordinal 的三段對照。送端若超過 150 ms，該段不符合連續穩速輸入假設。

[逐項數值](window-analysis.json) · [裝置與程式狀態](result.json) · [環境檢查](environment-result.json)
""",encoding='utf-8')
if __name__=='__main__':analyze()

