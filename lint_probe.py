from pathlib import Path
import ctypes,subprocess,sys
root=Path.cwd()
args=(root.parent/'r4-timing-rustc-args.txt').read_text(encoding='utf-8-sig').strip()
parse=ctypes.windll.shell32.CommandLineToArgvW
parse.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_int)]
parse.restype=ctypes.POINTER(ctypes.c_wchar_p)
count=ctypes.c_int()
argv=parse(args,ctypes.byref(count))[:count.value]
out=root/'target-mutation'
out.mkdir(exist_ok=True)
argv[argv.index('--out-dir')+1]=str(out)
argv=[arg.replace(arg,'incremental='+str(out/'incremental')) if arg.startswith('incremental=') else arg for arg in argv]
argv[argv.index('--error-format=json')]='--error-format=human'
argv=[arg for arg in argv if not arg.startswith('--json=')]
argv.extend(['-C','debuginfo=0'])
argv[0]=str(Path(argv[0]).with_name('clippy-driver.exe'))
argv.append('-Dwarnings')
argv[argv.index('--emit=dep-info,link')]='--emit=metadata'
print('compiling the modified checkout against the exact locked artifacts',flush=True)
subprocess.run(argv,check=True)
