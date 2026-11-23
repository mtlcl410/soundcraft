from pathlib import Path
p=Path(__file__).parent/'source/src/vst3'
def repl(name, a,b):
 f=p/name;s=f.read_text(encoding='utf8');assert a in s
 with f.open('w',encoding='utf8',newline='\n') as out:out.write(s.replace(a,b))
repl('warm_probe.h','inline thread_local long long totals[6]{};','extern thread_local long long totals[6];')
repl('plugin.cpp','#include "warm_probe.h"','#include "warm_probe.h"\nnamespace cold {thread_local long long totals[6]{};}')
repl('plugin.cpp','m_xg.begin_block();','const auto phase1=cold::ns();\n\tm_xg.begin_block();')
repl('plugin.cpp','const int32 n = data.numSamples;', 'const auto phase2=cold::ns();\n\tconst int32 n = data.numSamples;')
repl('plugin.cpp','if (left && done < n)','const auto phase3=cold::ns();\n\tif (left && done < n)')
repl('plugin.cpp','msgs=%zu','pre=%lld events=%lld deliver=%lld render=%lld msgs=%zu')
repl('plugin.cpp','cold::totals[5],m_msgs.size()', 'cold::totals[5],phase1-probe0,phase2-phase1,phase3-phase2,cold::ns()-phase3,m_msgs.size()')

