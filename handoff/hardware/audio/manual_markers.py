"""Independent, reproducible markers. The sequence identifies elapsed time on an SD recording."""
import sys,wave,random,array,hashlib,json
from pathlib import Path

def make(folder,seconds,kind):
    sr=48000
    codes=random.Random(16631662)
    wav=folder/f'{kind}-{seconds}s.wav'
    with wave.open(str(wav),'wb') as out:
        out.setparams((1,2,sr,0,'NONE',''))
        for sec in range(seconds):
            data=array.array('h',[0])*sr
            if kind=='sd':
                marker=[codes.choice((-1200,1200)) for _ in range(511)]
                data[12000:12000+len(marker)]=array.array('h',marker)
            else:
                for pos in (12000,36000):
                    marker=[codes.choice((-1200,1200)) for _ in range(127)]
                    data[pos:pos+len(marker)]=array.array('h',marker)
            if sys.byteorder!='little':data.byteswap()
            out.writeframesraw(data.tobytes())
    with wav.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(file=wav.name,sha256=digest,seconds=seconds,rate=sr,kind=kind)
if __name__=='__main__':
    folder=Path(__file__).resolve().parent/'manual-stimulus';folder.mkdir(exist_ok=True)
    rows=[make(folder,840,'sd'),make(folder,135,'chase')]
    (folder/'manifest.json').write_text(json.dumps(rows,indent=2))
