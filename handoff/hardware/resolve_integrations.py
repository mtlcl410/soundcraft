from pathlib import Path
import re,subprocess,json
root=Path(__file__).resolve().parent
merges={}
for mode in ('beat','mtc','follow'):
    tree=root/f'integrated-{mode}'
    changed=subprocess.check_output(['git','diff','--name-only','--diff-filter=U'],cwd=tree,text=True).splitlines()
    for name in changed:
        path=tree/name
        def resolve(m):
            a,b=m.groups()
            if path.name=='stream.rs':
                assert '*o = T::from_sample(*x);' in a and '*o = output_sample(*x);' in b
                return a.replace('*o = T::from_sample(*x);','*o = output_sample(*x);')
            if path.name=='record.rs':
                assert not a and 'input_config_accepts_a_twelve_channel_packed_pcm_device' in b
                return b
            if 'let (stream, recovery)' in a:
                assert 'SampleFormat::I24' in b
                return a
            if 'fn reuses_output_device' in b:
                assert 'boundary, compacted' in a
                return a+'}\n\n'+b
            assert 'asio_device:' in b
            return a+b
        s,n=re.subn(r'(?ms)^<<<<<<<[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n',resolve,path.read_text('utf8'))
        assert n and '<<<<<<<' not in s
        if path.name=='stream.rs':
            k='        cpal::SampleFormat::I32 => build_output::<i32>(device, config, graph, fault, shared),'
            assert s.count(k)==1
            s=s.replace(k,k+'\n'+k.replace('::I32','::I24').replace('::<i32>','::<cpal::I24>'))
        path.write_text(s,encoding='utf8')
    subprocess.run(['git','add','--',*changed],check=True,cwd=tree)
    subprocess.run(['git','diff','--cached','--check'],check=True,cwd=tree)
    subprocess.run(['git','commit','--no-edit'],check=True,cwd=tree)
    merges[mode]=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],cwd=tree,text=True).strip().split()
(root/'integrations.json').write_text(json.dumps(merges,indent=2))
