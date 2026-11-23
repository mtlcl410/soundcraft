from pathlib import Path
import shutil,sys
target=Path(sys.argv[1]).resolve()
audit=Path(__file__).resolve().parent
beat=audit.parent/'g11-beat-clock'
mtc=audit.parent/'g11-mtc'
def src(root,name):return root/'crates/playback/src'/name
for name in ['sync_clock.rs','sync_output.rs','sync_status.rs','beat_clock.rs','stream.rs']:
    shutil.copyfile(src(beat,name),src(target,name))
for name in ['mtc_input.rs','sync_input.rs','midi.rs']:
    shutil.copyfile(src(mtc,name),src(target,name))
for name in ['mtc.rs','mtc/tests.rs']:
    shutil.copyfile(audit/('combined-stack-'+name.replace('/','_')),src(target,name))
# Start from the Beat Clock's presentation path, then insert the chase transport.
s=src(beat,'lib.rs').read_text()
s=s.replace('pub mod midi;','pub mod midi;\npub mod mtc;\npub mod mtc_input;\npub mod sync_input;')
s=s.replace('    Stop,\n    Locate(Samples),','    PlayMtc(Samples),\n    EndChase,\n    Stop,\n    Locate(Samples),')
s=s.replace('        self.shared.position.store(from, Ordering::Relaxed);','        self.begin_play(from,Cmd::Play{from,end,looped});\n    }\n    pub fn play_chasing_mtc(&self,from:Samples){self.begin_play(from,Cmd::PlayMtc(from));}\n    pub fn end_mtc_chase(&self){let _=self.tx.send(Cmd::EndChase);}\n    fn begin_play(&self,from:Samples,cmd:Cmd){\n        self.shared.position.store(from, Ordering::Relaxed);',1).replace('let _ = self.tx.send(Cmd::Play { from, end, looped });','let _ = self.tx.send(cmd);',1)
s=s.replace('        let _ = self.tx.send(Cmd::Midi(feed));','        #[cfg(any(target_os="windows",target_os="linux",target_os="macos"))]\n        feed.set_sync_waker(self.sync_waker());\n        let _ = self.tx.send(Cmd::Midi(feed));')
src(target,'lib.rs').write_text(s)
s=src(beat,'callback.rs').read_text()
mt=src(mtc,'callback.rs').read_text()
s=s.replace('    playing: bool,\n    end:', '    playing:bool,\n    chasing:bool,\n    drift_since:Option<i64>,\n    chase_group:Option<i64>,\n    end:',1)
s=s.replace('            playing: false,','            playing:false,\n            chasing:false,drift_since:None,chase_group:None,',1)
s=s.replace('                    self.recording = r;','                    if r && (self.chasing || self.midi.as_ref().is_some_and(|f|f.mtc_online())) {continue;}\n                    self.recording = r;',1)
a=s.index('                Cmd::Play { from, end, looped } =>');b=s.index('                Cmd::Locate(at)',a)
s=s[:a]+'''                Cmd::Play {from,end,looped}=>self.begin_play(from,end,looped,false),
                Cmd::PlayMtc(from)=>self.begin_play(from,None,None,true),
                Cmd::Stop=>self.halt(),
                Cmd::EndChase=>self.end_chase(),
'''+s[b:]
a=s.index('                Cmd::Locate(at) =>');b=s.index('            }\n        }',a)
s=s[:a]+'''                Cmd::Locate(at) => {
                    self.pos=at;
                    #[cfg(any(target_os="windows",target_os="linux",target_os="macos"))]
                    if let Some(clock)=&mut self.clock {clock.locate(at);}
                    if self.playing {self.midi_stopped=None;self.pending_len=0;self.read=0.;self.mix.reset();}
                }
'''+s[b:]
a=mt.index('    fn begin_play(');b=mt.index('    fn reset_mtc(',a)
fn=mt[a:b].replace('        self.reset_mtc();\n','').replace('        self.pos = from;', '        #[cfg(any(target_os="windows",target_os="macos",target_os="linux"))]\n        if let Some(clock)=&mut self.clock{clock.locate(from);}\n        self.pos = from;')
a=fn.index('        let delay = self.device_timing');b=fn.index('        let desired',a)
fn=fn[:a]+'''        #[cfg(any(target_os="windows",target_os="macos",target_os="linux"))]
        let delay=self.device_timing.map_or(0.,|t| t.heard_instant(self.device_rate,0).saturating_duration_since(t.callback).as_secs_f64());
        #[cfg(not(any(target_os="windows",target_os="macos",target_os="linux")))]
        let delay=0.;
'''+fn[b:]
fn=fn.replace('                self.pos = p.session_sample(rate, sr, start, offset).max(0);','                let at=p.session_sample(rate,sr,start,offset).max(0);\n                #[cfg(any(target_os="windows",target_os="macos",target_os="linux"))]\n                if at!=self.pos && let Some(clock)=&mut self.clock{clock.locate(at);}\n                self.pos=at;')
s=s.replace('    fn send_garbage(&mut self)',fn+'    fn send_garbage(&mut self)')
s=s.replace('        let age_speed = std::mem::replace(&mut self.midi_speed, speed);','        let age_speed=self.midi_speed;')
s=s.replace('        self.drain();\n        if let Some(ended)', '        let was_chasing=self.chasing;\n        self.drain();\n        self.follow_mtc();\n        if let Some(ended)')
s=s.replace('        self.midi_started = false;\n        // A command', '        self.midi_started=false;\n        let speed=if self.chasing || was_chasing{self.speed()}else{speed};\n        self.midi_speed=speed;\n        // A command')
src(target,'callback.rs').write_text(s)
s=src(beat,'tests.rs').read_text()
src(target,'tests.rs').write_text(s)
p=src(target,'midi.rs')
s=p.read_text().replace('    mtc_online: AtomicBool,','    sync_wake:Mutex<Option<Arc<dyn Fn()+Send+Sync>>>,\n    mtc_online: AtomicBool,').replace('            mtc_online: false.into(),','            sync_wake:Mutex::default(),\n            mtc_online: false.into(),')
s=s.replace('    fn wake_mtc_host(&self) {','    pub(crate) fn set_sync_waker(&self,wake:Arc<dyn Fn()+Send+Sync>){*self.sync_wake.lock().unwrap_or_else(PoisonError::into_inner)=Some(wake);}\n    fn wake_mtc_host(&self) {\n        if let Some(wake)=self.sync_wake.lock().unwrap_or_else(PoisonError::into_inner).as_ref(){wake();}')
p.write_text(s)
