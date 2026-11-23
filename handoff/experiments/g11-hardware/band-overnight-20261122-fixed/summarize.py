import json
from pathlib import Path
from statistics import median
from PIL import Image, ImageDraw, ImageFont

folder = Path(__file__).resolve().parent
baseline = folder.with_name(folder.name.removesuffix("-fixed"))
repo = folder.parent.parent / "g11-storage-clock-follow"
def load(path):
    return json.loads(path.read_bytes())

def take(path):
    j = load(path)
    lag = j["lag_ms"]
    steady = median(lag[4:14])
    assert len(j["drums"]) == 32 and len(j["keys"]) == 64
    return {"step":lag[17]-steady, "end":median(lag[-4:])-steady, "start":lag[0],
            "bpm":j["bpm"], "checks":j["checks"], "file":path.name}

results = {}
for direction in ["120-100", "100-120"]:
    pattern = f"calibrated-{direction}-top-results.json"
    old = take(baseline / pattern)
    new = [take(folder / (prefix+pattern)) for prefix in ("fixed-", "repeat2-", "repeat3-")]
    results[direction] = {"old":old,"new":new}

(folder / "tempo-step-summary.json").write_text(json.dumps(results, indent=2))
img = Image.new("RGB", (1280,535), "white")
draw = ImageDraw.Draw(img)
def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/" + ("segoeuib.ttf" if bold else "segoeui.ttf"), size)
def label(x,y,msg,size=21,anchor="lm",bold=False,color="#222d3b"):
    draw.text((x,y),msg,anchor=anchor,font=font(size,bold),fill=color)
label(40,45,"Chorus tempo change: timing of the next beat",36,bold=True)
label(40,92,"Follower minus leader, after subtracting their steady verse offset (ms)",24)
left,right=275,1195
def pos(ms):
    return left+(ms+110)*(right-left)/190
for ms in range(-100,81,20):
    x=pos(ms)
    draw.line((x,160,x,372),fill="#718096" if ms == 0 else "#d8e1e8",width=2 if ms==0 else 1)
    label(x,392,str(ms),19,anchor="mt")
for (direction,v),y in zip(results.items(),(216,316)):
    label(40,y,direction.replace("-"," → ")+" BPM",23,bold=True)
    old=pos(v["old"]["step"])
    draw.rectangle((old-6,y-6,old+6,y+6),fill="#9c4934")
    for n,rr in enumerate(v["new"]):
        x=pos(rr["step"]);h=y+(n-1)*15
        draw.ellipse((x-6,h-6,x+6,h+6),fill="#18716a")
draw.rectangle((45,477,57,489),fill="#9c4934")
label(70,483,"Before (one take per direction)",20)
draw.ellipse((463,477,475,489),fill="#18716a")
label(488,483,"After (three takes per direction)",20)
label(1195,438,"Earlier ←     0     → Later",18,anchor="rm")
img.save(repo / "docs/images/midi-clock-chorus-tempo-step.png")
for direction,v in results.items():
    print(direction, v)
