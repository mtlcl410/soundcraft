from common import *
tree=d/'mtc'
removed=git(tree,'diff','5616912','81613837','--','crates/ui-egui/locales/pt-BR/mod.rs')
keys=set(re.findall(r'^\+\s*("[^"\n]+")\s*=>',removed,re.M))
files=(tree/'crates/ui-egui/src').rglob('*.rs')
text=''.join(x.read_text('utf8') for x in files if x.name!='localization.rs')
used=set(re.findall(r'(?:localization::text\(|localized_format!\()("[^"\n]+")',text))
print('\n'.join(sorted(keys&used)))

