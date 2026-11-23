from pathlib import Path
s=Path(__file__).parent/'source/src'
def put(f,t):f.write_bytes(t.encode('utf8'))
f=s/'mame/sound/swp30.h';t=f.read_text(encoding='utf8');key='\tvoid dump_meg(';assert t.count(key)==1;t=t.replace(key,'\tvoid prepare_restored_meg();\n'+key);t=t.replace('\tvoid meg_jit_rebuild();','\tvoid refresh_meg_program();\n\tvoid meg_jit_rebuild();');put(f,t)
f=s/'mame/sound/swp30.cpp';t=f.read_text(encoding='utf8');i=t.index('void swp30_device::run_sample(s32 &left, s32 &right)');a=t.index('\t\tm_meg->decode_program();',i);b=t.index('\n\t} else if(m_meg_jit_wait',a)
setup=t[a:b];helper='void swp30_device::refresh_meg_program()\n{\n'+'\n'.join(line[1:] if line.startswith('\t') else line for line in setup.split('\n'))+'\n}\n\n'
t=t[:a]+'\t\trefresh_meg_program();'+t[b:];pos=t.rindex('// S-MU2000: execute_run()',0,i)
t=t[:pos]+helper+'''// Restoring a snapshot invalidates derived MEG code even when its program
// is unchanged. Build it on the control thread without running a DSP step.
// Keep the normal write-settling delay for firmware edits in progress.
void swp30_device::prepare_restored_meg()
{
\tif (!m_meg_ops_stale || m_meg_program_changed || !meg_jit_enabled())
\t\treturn;
\trefresh_meg_program();
\tmeg_jit_rebuild();
\tm_meg_jit_wait = 0;
}

'''+t[pos:];put(f,t)
f=s/'vst3/engine.cpp';t=f.read_text(encoding='utf8');a=t.index('if (!sh2_device::jit_enabled()');t=t[:a]+'m_mu->swpm().prepare_restored_meg();\n\tm_mu->swps().prepare_restored_meg();\n\t'+t[a:];put(f,t)

