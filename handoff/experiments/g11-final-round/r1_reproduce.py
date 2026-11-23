from pathlib import Path
import json, os, subprocess, re, sys
from owner_probes import test_block
d=Path(__file__).resolve().parent
w=d/'owner-red62'
old='7ff81296'
new='56169122'
e=d/'evidence'/'r1-1662-red'
e.mkdir(exist_ok=True)
def source(name,rev):
    return subprocess.check_output(['git','show',rev+':'+name],cwd=w).decode().replace('\r\n','\n')
def replace(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)
cases={}
def probes(path,ids):
    a,b=source(path,old),source(path,new)
    added=[]
    for num,name in ids.items():
        cases[num]=name
        added.append(test_block(b,name))
    at=a.rfind('\n',0,a.index('#[test]',a.index('mod timing_warning_tests') if path.endswith('/app/audio.rs') else 0))+1
    return a[:at]+'\n'.join(added)+'\n'+a[at:]
def write(f,t):
    if (w/f).read_text(encoding='utf8') != t: (w/f).write_text(t,encoding='utf8')
p='crates/playback/src/beat_clock.rs'
write(p,probes(p,{17:'review_launch_at_a_rounded_pulse_boundary_does_not_send_two_clocks',18:'review_stopped_range_warning_persists_until_the_next_locate'}))
p='crates/playback/src/sync_output_tests.rs'
a=probes(p,{6:'review_unavailable_generation_never_encodes_another_sessions_tempo',7:'review_superseded_pass_discards_locates_both_before_and_at_their_deadline',8:'review_failed_transport_stop_is_retried_before_new_pass_start',14:'review_delay_uses_rate_of_the_audible_callback_after_an_edit',20:'review_a_stall_beyond_the_repayment_beat_relocates_to_the_current_position'})
name='a_missed_timing_gap_invalidates_only_the_compensated_route_queue'
oldtest=test_block(a,name)
s=test_block(source(p,new),name)
s=replace(s,'    // Both callback publications land between two worker polls.', '''    // Mutation control. Mislabel just the queued destinations before resuming, emulating a route swap.
    for event in &mut port.future { event.route = 1 - event.route; }
    // Both callback publications land between two worker polls.''')
cases[19]=name
write(p,replace(a,oldtest,s))
p='crates/playback/src/sync_output/ports.rs'
a=probes(p,{15:'review_unnameable_output_with_the_same_id_never_opens_its_named_sibling'})
a=replace(a,'assert_eq!(assign(&Bindings::new(), found), Bindings::from','assert_eq!(assign(&Bindings::new(), found.into_iter().filter_map(|(name,id): (Option<String>,String)| Some((name?, id)))), Bindings::from')
write(p,a)
p='crates/playback/src/stream_recovery.rs'
a=probes(p,{5:'callback_panic_latched_after_service_check_prevents_handoff',23:'exhausted_recovery_can_reopen_an_endpoint_that_never_disappears'})
a=replace(a,'&running, &fault.failed, now','&running, now')
a=replace(a,'&running, &AtomicBool::new(false), now','&running, now')
write(p,a)
p='crates/ui-egui/src/lib.rs'
write(p,source(p,new))
p='crates/ui-egui/src/app/audio.rs'
a=probes(p,{9:'applied_selection_retargets_a_failed_open_including_equal_names_on_other_hosts',22:'manual_retry_and_apply_clear_only_the_matching_idle_warning',24:'reconnect_uses_the_original_open_host_after_falling_back'})
a=a.replace('name, stalled_at_report:', 'name, system: None, stalled_at_report:').replace('name,\\n','name,\\n')
a=a.replace('                name,\n                stalled_at_report:', '                name,\n                system: None,\n                stalled_at_report:').replace('name: "Output A".into(), stalled_at_report:', 'name: "Output A".into(), system: None, stalled_at_report:')
a=replace(a,'    fn clear_recovered_output(&mut self)', '''    // Test adapters reproduce the old apply, reconnect-result, and config expressions.
    #[cfg(test)]
    fn applied_output_status(&mut self, _changed: bool, silent: bool) {
        if !silent { self.unavailable_output = None; }
    }
    #[cfg(test)]
    fn reconnected_output_status(&mut self, name: Option<String>, _system: Option<String>, silent: bool) {
        self.unavailable_output = name.filter(|_| silent).map(|name| crate::UnavailableOutput {
            name, system: None, stalled_at_report: None, idle_status: None
        });
    }
    #[cfg(test)]
    fn recovery_config(&self) -> soundcraft_playback::AudioConfig { self.ui.audio.clone() }
    fn clear_recovered_output(&mut self)''')
write(p,a)
(e/'lower-head-with-probes.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=w))
target=d.parent/'g11-review3-mtc-playback-target'
env=os.environ|{'CARGO_TARGET_DIR':str(target),'CARGO_TERM_COLOR':'never'}
procs=['cmd','/c',str(d.parent/'g11-a10-recovery'/'run.cmd'),'test','--locked','-j','2','-p','soundcraft-playback','-p','soundcraft-ui-egui','--lib','--no-fail-fast','--','--test-threads=2',*cases.values()]
log=e/'red.log'
with log.open('wb') as f: rc=subprocess.run(procs,cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
text=log.read_text(encoding='utf8',errors='replace')
rows=[]
for number,name in sorted(cases.items()):
    found=re.search(r'test [^\n]+\b'+re.escape(name)+r' \.\.\. (FAILED|ok)',text)
    rows.append({'finding':number,'test':name,'outcome':found[1] if found else 'not_run'})
out={'base':old,'equivalent_fixed_head':new,'command':procs,'cases':rows,'code':rc,'route19':'distinct message types and a scoped deliberately swapped queued route mutation'}
(e/'results.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(out)
raise SystemExit(0 if all(r['outcome']=='FAILED' for r in rows) else 1)



