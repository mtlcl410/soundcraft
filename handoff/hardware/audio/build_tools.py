"""Build a private copy of asio-sys and the independent player. No device access."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parent
AUDIT=ROOT.parent.parent
SOURCE=AUDIT.parent/'tools/cargo/registry/src/-1a9ddb161ac86ee7/asio-sys-0.4.0'
VENDOR=ROOT/'build/asio-sys'
def subst(s,old,new):
    assert s.count(old)==1,old
    return s.replace(old,new)
def build(which,source=None):
    dst=ROOT/'build';dst.mkdir(exist_ok=True)
    if not VENDOR.exists():shutil.copytree(SOURCE,VENDOR)
    file=Path('src/bindings/mod.rs'); s=(SOURCE/file).read_text()
    s=subst(s,'pub mod errors;','pub mod errors;\nmod witness;')
    s=subst(s,'        *state = DriverState::Prepared;\n\n        Ok(buffer_size)','        *state = DriverState::Prepared;\n        drop(state);\n        witness::setup(self,buffer_infos,buffer_size);\n\n        Ok(buffer_size)')
    s=subst(s,'    if CALL_OUTPUT_READY.load(Ordering::Acquire) {','    let pos=asio_time.time_info.sample_position;\n    witness::capture(double_buffer_index as usize, (pos.hi as u64)<<32 | pos.lo as u64,callback_info.system_time,asio_time.time_info.flags);\n    if CALL_OUTPUT_READY.load(Ordering::Acquire) {')
    s=subst(s,'asio_result!(ai::ASIODisposeBuffers())?;', 'witness::clear();\n            asio_result!(ai::ASIODisposeBuffers())?;')
    for dest,content in ((VENDOR/file,s),(VENDOR/'src/bindings/witness.rs',(ROOT/'witness.rs').read_text())):
        if not dest.is_file() or dest.read_text()!=content:dest.write_text(content)
    sdk=Path(os.environ['TEMP'])/'soundcraft-review-sdk'
    env=os.environ|{'CPAL_ASIO_DIR':str(sdk/'ASIOSDK'),'LIBCLANG_PATH':str(sdk/'clang-wheel/clang/native'),'CARGO_TARGET_DIR':str(dst/'target')}
    run=str(AUDIT/'g11-a10-recovery/run.cmd')
    if which=='independent':
        local=dst/'independent';(local/'src').mkdir(exist_ok=True,parents=True)
        (local/'Cargo.toml').write_text('[package]\nname="independent"\nversion="0.1.0"\nedition="2021"\n[dependencies]\nasio-sys={path="../asio-sys"}\n')
        shutil.copyfile(AUDIT/'g11-final-round/follow/Cargo.lock',local/'Cargo.lock')
        shutil.copyfile(ROOT/'independent.rs',local/'src/main.rs');args=[]
    else:
        env['CARGO_TARGET_DIR']=str(AUDIT/'g11-follow-r3-target')
        local=Path(source).resolve()
        if subprocess.check_output(['git','-C',local,'status','--porcelain']).strip():raise ValueError('Use a clean checkout')
        sha=subprocess.check_output(['git','-C',local,'rev-parse','HEAD'],text=True).strip()
        work=dst/f'soundcraft-{sha[:8]}'
        if not work.exists():subprocess.run(['git','-C',local,'worktree','add','--detach',work,sha],check=True)
        if subprocess.check_output(['git','-C',work,'rev-parse','HEAD'],text=True).strip()!=sha:raise ValueError('wrong worktree')
        local=work;args=['-p','soundcraft','--bin','soundcraft','--features','asio','--config',f'patch.crates-io.asio-sys.path="{VENDOR.as_posix()}"']
    subprocess.run(['cmd','/c',run,'build','--offline','-j','2',*args],cwd=local,env=env,check=True)
    exe=Path(env['CARGO_TARGET_DIR'])/'debug'/('independent.exe' if which=='independent' else 'soundcraft.exe')
    dest=dst/('independent.exe' if which=='independent' else f'soundcraft-{sha[:8]}.exe')
    shutil.copy2(exe,dest)
    if which!='independent':
        import hashlib
        (dst/f'{sha[:8]}-build.json').write_text(json.dumps(dict(head=sha,exe=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),overlay='asio-sys witness only'),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['independent','soundcraft']);p.add_argument('--tree');a=p.parse_args();build(a.kind,a.tree)

