from pathlib import Path
import subprocess,re,sys
d=Path(__file__).resolve().parent
def run(*args):return subprocess.check_output(['git','-C',str(d/'follow'),*args]).decode('utf8')
tree=sys.argv[1]
for f in sys.argv[2:]:
 try: text=run('show',tree+':'+f); 
 except subprocess.CalledProcessError:continue
 for i,m in enumerate(re.finditer(r'^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*',text,re.M|re.S)):
  print(f,i+1, m.start(), '\n'+m.group(1)[:850]+'====\n'+m.group(2)[:880]+'\n')

