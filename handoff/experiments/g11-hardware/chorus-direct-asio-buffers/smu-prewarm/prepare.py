from pathlib import Path
s=Path(__file__).parent/'source/src'
def write(f,t):f.write_bytes(t.encode('utf8'))
f=s/'vst3/engine.cpp';t=f.read_text(encoding='utf8')
a=t.index('\t\t// A snapshot skips firmware boot');b=t.index('\t\tlogf(',a)
t=t[:a]+t[b:]
a=t.index('void engine::apply_deferred_state()')
t=t[:a]+'''// Called by the VST3 host on the control thread while configuring a
// processor. A restored snapshot contains DSP state but no compiled ROM.
void engine::prepare_playback()
{
\tstd::lock_guard<std::mutex> lock(m_machine);
\tif (!m_mu || state() != status::ready || m_processing.load() || !m_cold_rom)
\t\treturn;
\tapply_deferred_state();
\tif (!sh2_device::jit_enabled() || native_engine())
\t\treturn;
\tauto reference = std::make_unique<mu2000>();
\treference->set_program_rom(m_mu->program_rom());
\treference->set_wave_rom(m_mu->wave_rom());
\treference->set_sintab_rom(m_mu->sintab_rom());
\treference->set_lcd_font(m_mu->lcd_font());
\treference->set_usb_host(m_mu->usb_host());
\treference->reset();
\tconst auto snapshot = m_mu->save_state();
\tstd::string error;
\tif (!reference->load_state(snapshot.data(), snapshot.size(), error))
\t\treturn;
\t// Exercise both the idle loop and typical MIDI dispatch on the copy.
\t// The live instrument receives no events and advances by zero samples.
\tfor (int sample = 0; sample < 1536; ++sample) {
\t\tif (sample == 256 || sample == 1024) {
\t\t\treference->midi_in(sample == 256 ? 0x90 : 0x80, 0);
\t\t\treference->midi_in(60, 0);
\t\t\treference->midi_in(64, 0);
\t\t}
\t\ts32 left, right;
\t\treference->run_sample(left, right);
\t}
\tm_mu->cpu().prepare_rom_blocks(reference->cpu());
\tm_cold_rom = false;
}

'''+t[a:]
t=t.replace('m_boards_to_apply = boards;','m_boards_to_apply = boards;\n\tm_cold_rom = true;')
write(f,t)
f=s/'vst3/engine.h';t=f.read_text(encoding='utf8');t=t.replace('void fill(float','void prepare_playback();\n\tvoid fill(float');t=t.replace('std::atomic<bool> m_processing','bool m_cold_rom = true; // protected by m_machine\n\tstd::atomic<bool> m_processing');write(f,t)
f=s/'vst3/plugin.cpp';t=f.read_text(encoding='utf8');i=t.index('\n\t\t} else {',t.index('if (!m_engine.wait_ready(30000))'))
t=t[:i]+'\n\t\t\telse\n\t\t\t\tm_engine.prepare_playback();'+t[i:]
t=t.replace('m_engine.publish_xg_now();','m_engine.prepare_playback();\n\t\tm_engine.publish_xg_now();',1);write(f,t)

