"""Reconcile the external-Clock render horizon with the previous-revision tail and input tests."""
from pathlib import Path
import shutil,re,sys
d=Path(__file__).resolve().parent
w=d/'follow'
def resolve(rel,decisions):
 p=w/rel;s=p.read_text('utf8')
 rx=r'^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n'
 matches=list(re.finditer(rx,s,re.M|re.S));assert len(matches)==len(decisions),(rel,len(matches))
 for m,fun in zip(reversed(matches),reversed(decisions)):
  s=s[:m.start()]+fun(*m.groups())+s[m.end():]
 p.write_text(s,'utf8')
def both(a,b):return a+b
def upper(a,b):return a
def lower(a,b):return b
def cap(a,b):
 assert 'self.render_next(quantum);' in b and 'else { quantum }, through, delivery);' in a
 return b[:b.index('                self.render_next(quantum);')]+a
def tests(a,b):return a+'    }\n\n    #[test]\n'+b
resolve('crates/playback/src/callback.rs',[both,cap])
resolve('crates/playback/src/midi.rs',[lower,tests])
resolve('docs/midi-input.md',[upper])

