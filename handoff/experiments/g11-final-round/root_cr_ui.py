from pathlib import Path
def rep(path,a,b):
 p=Path(path);s=p.read_text('utf8');assert s.count(a)==1,(path,a);p.write_text(s.replace(a,b),'utf8')
p='crates/ui-egui/src/app/playback.rs'
msg='Cannot record MIDI: open an audio output in Setup > Playback Engine to start the audio engine.'
rep(p,'        } else if midi_ready {\n            // MIDI alone makes a pass.',f'''        }} else if midi_ready {{
            if self.player.is_none() {{
                self.ui.status = crate::localization::text("{msg}").into();
                return;
            }}
            // MIDI alone makes a pass.''')
p='crates/ui-egui/locales/pt-BR/mod.rs'
rep(p,'        "Cannot record: no MIDI input device',f'''        "{msg}" => {{
            "Não é possível gravar MIDI: abra uma saída de áudio em Configuração > Mecanismo de reprodução para iniciar o mecanismo de áudio."
        }}
        "Cannot record: no MIDI input device''')
p='crates/ui-egui/src/app/files.rs'
rep(p,'                self.document_replaced();\n                if self.write_autosave()', '''                self.document_replaced();
                let offset_warning = self.engine.has_conflicting_timecode_offsets().then(|| self.ui.status.clone());
                if self.write_autosave()''')
rep(p,'                };\n            }\n            Err(e) => self.ui.status', '''                };
                if let Some(warning) = offset_warning {
                    self.ui.status.push(' ');
                    self.ui.status.push_str(&warning);
                }
            }
            Err(e) => self.ui.status''')

