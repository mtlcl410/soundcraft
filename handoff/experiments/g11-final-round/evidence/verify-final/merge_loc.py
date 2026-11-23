from common import *
tree=d/'verify-final-upper'
dest=tree/'crates/ui-egui/src/localization.rs'
s=dest.read_text('utf8')
pattern=r'    // [^\n]+\n    fn permits_untranslated_sync_label\(source: &str\) -> bool \{\n(.*?)^    \}\n\n'
bodies=list(re.finditer(pattern,s,re.M|re.S)) if False else list(re.finditer(pattern,s,re.M|re.S))
assert len(bodies)==2
keys=sorted(set(lit for b in bodies for lit in re.findall(r'"[^"\n]+"',b.group(1))))
assert len(keys)>=20 and all('Language::PortugueseBrazil.text(source) == source' in b.group() for b in bodies)
h='    // Feature keys fall back to English until the translation catalog is updated.\n    fn permits_untranslated_sync_label(source: &str) -> bool {\n        matches!(\n            source,\n            '+('\n                | '.join(keys))+'\n        ) && Language::PortugueseBrazil.text(source) == source\n    }\n\n'
b1,b2=bodies
s=s[:b1.start()]+h+s[b1.end():b2.start()]+s[b2.end():]
assert s.count('fn permits_untranslated_sync_label')==1
dest.write_text(s,'utf8')

