from bench import *
import round4_follow_loop as loop
# The existing receiver oracle samples the desktop while injecting transport and a clock outage.
with app(d/'Back to the Chorus.scraft','clock-loss') as c:
    p=int((d/'clock-loss.log').read_text().split('SOUNDCRAFT_CONTROL_PORT=')[1].split()[0])
    sys.argv=['round4_follow_loop','--run','--port',str(p),'--source-head','5b1418a','--directory',str(d/'physical-clock-loss')]
    loop.main()
