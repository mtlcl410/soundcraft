"""Port the MTC-owned changes after the output layer is merged."""
from pathlib import Path
import subprocess
from owner_probes import test_block

d=Path(__file__).resolve().parent
w=d/'mtc'
def source(p):
    return subprocess.check_output(['git','show','c093aedb:'+p],cwd=w).decode()
def apply_upstream(p):
    patch=subprocess.check_output(['git','diff','14030820','c093aedb','--',p],cwd=w)
    subprocess.run(['git','apply','-'],input=patch,cwd=w,check=True)
def edit(p,a,b):
    f=w/p
    t=f.read_text(encoding='utf8')
    assert t.count(a)==1,(p,a,t.count(a))
    f.write_text(t.replace(a,b),encoding='utf8')
for p in ['crates/engine/src/cmd/options.rs','crates/playback/src/mtc.rs','crates/playback/src/mtc/tests.rs','crates/playback/src/mtc_input.rs']:
    apply_upstream(p)
p='crates/engine/src/cmd.rs'
f=w/p
t=f.read_text(encoding='utf8')
u=source(p)
i=t.index('    Ok(position_param_raw')
j=t.index('    let Some(v) = p.get(key)',i)
t=t[:i]+u[u.index('    Ok(parse_position_param'):u.index('    let Some(v) = p.get(key)',u.index('fn parse_position_param'))]+t[j:]
t=t.replace('if let Ok(x) = s.parse_position(body, f) {','''let parsed = match timecode_from_zero {
                Some(rate) => soundcraft_time::parse_position(body, f, s.sample_rate, &s.tempo, rate, 0, 0),
                None => s.parse_position(body, f),
            };
            if let Ok(x) = parsed {''').replace('if f == soundcraft_time::TimeFormat::Timecode && x < 0 {','if timecode_from_zero.is_none() && f == soundcraft_time::TimeFormat::Timecode && x < 0 {')
t=t.replace('let len = position_param(e, cmd, p, "length")?;', 'let len = duration_param(e, cmd, p, "length")?;')
f.write_text(t,encoding='utf8')
p='crates/playback/src/midi.rs'
edit(p,'r.options = crate::mtc_input::Options {','r.set_options(crate::mtc_input::Options {')
edit(p,'offset: external_offset_samples,\n        };','offset: external_offset_samples,\n        });')
p='crates/ui-egui/src/app/mtc.rs'
guard='        self.engine.transport_requests.retain(|r| !matches!(r, TransportRequest::Record));'
edit(p,guard,'''        let queued = self.engine.transport_requests.len();
'''+guard+'''
        if self.engine.transport_requests.len() != queued {
            self.ui.status = crate::localization::text("Take MTC chase offline before recording").into();
        }''')
tests='\n'.join(test_block(source(p),n) for n in ['offset_edit_repositions_a_stopped_reader_without_another_packet','online_transition_gates_a_record_command_already_in_the_queue'])
tests+='''
    #[test]
    fn online_service_reports_why_a_pending_record_was_refused() {
        let mut host = app();
        let reason = host.run("transport.record", json!({})).unwrap_err();
        host.ui.status.clear();
        host.engine.transport_requests.push(TransportRequest::Record);
        host.service_mtc_chase();
        assert_eq!(host.ui.status, reason);
        assert!(host.engine.transport_requests.is_empty());
        assert!(!host.engine.transport.recording);
    }
'''
edit(p,'    #[test]\n    fn before_start_external',tests+'\n    #[test]\n    fn before_start_external')
p='crates/ui-egui/src/app/playback.rs'
edit(p,'    fn start_recording(&mut self) {','''    fn start_recording(&mut self) {
        if self.mtc_online {
            self.ui.status = crate::localization::text("Take MTC chase offline before recording").into();
            return;
        }''')
p='crates/engine/src/cmd/options.rs'
edit(p,'    #[test]\n    fn external_timecode_offset_is_one_value', '''    #[test]
    fn timecode_retention_respects_automation_switch_and_keeps_both_rulers_on_undo() {
        for follows in [false, true] {
            let mut e = crate::demo::demo_engine();
            e.session_mut().edit.automation_follows_edit = follows;
            e.session_mut().timecode_start = e.session().sample_rate.samples(3600.);
            let before = e.session().clone();
            assert!(!before.markers.is_empty());
            let delta = before.sample_rate.samples(1800.);
            e.execute("setup.session", &json!({"start_timecode":"00:30:00:00","keep":"timecode"})).unwrap();
            let after = e.session();
            assert_eq!(json!(after.markers), json!(before.markers));
            assert_eq!(json!(after.tempo), json!(before.tempo));
            for (old, new) in before.tracks.iter().zip(&after.tracks) {
                for (a,b) in old.automation.iter().flat_map(|l| &l.points).zip(new.automation.iter().flat_map(|l| &l.points)) {
                    assert_eq!(b.at, a.at + if follows { delta } else { 0 });
                }
                for (a,b) in old.playlists.iter().flat_map(|p| &p.clips).zip(new.playlists.iter().flat_map(|p| &p.clips)) {
                    assert_eq!(b.start, a.start + delta);
                }
            }
            assert!(e.undo());
            assert_eq!(e.session().to_json().unwrap(), before.to_json().unwrap());
        }
    }

    #[test]
    fn external_timecode_offset_is_one_value''')
