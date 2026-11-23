"""Capture WinMM short messages and full-frame SysEx from the Model 12's recorder USB port."""
import ctypes as c
import json
import sys
import time
from pathlib import Path
from queue import SimpleQueue, Empty

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tascam-model-12/hui"))
from model12_midi_probe import midi, ports

class Header(c.Structure):
    _fields_ = [('data', c.c_void_p), ('length', c.c_uint32), ('recorded', c.c_uint32),
                ('user', c.c_size_t), ('flags', c.c_uint32), ('next', c.c_void_p),
                ('reserved', c.c_size_t), ('offset', c.c_uint32), ('reserved_array', c.c_size_t * 8)]

def check(code):
    if code:
        raise OSError(f"WinMM error {code}")

root = Path(__file__).resolve().parent
handle = c.c_void_p()
q = SimpleQueue()
buffers = []
cbtype = c.WINFUNCTYPE(None, c.c_void_p, c.c_uint, c.c_size_t, c.c_size_t, c.c_size_t)

@cbtype
def callback(_h, kind, _inst, word, stamp):
    if kind == 0x3c3 and word & 255 in (0xf1, 0xf2, 0xf8, 0xfa, 0xfb, 0xfc):
        length = {0xf1: 2, 0xf2: 3}.get(word & 255, 1)
        q.put((stamp, list(word.to_bytes(4, 'little')[:length]), None))
    elif kind == 0x3c4:
        header = Header.from_address(word)
        q.put((stamp, list(c.string_at(header.data, header.recorded)), word))

device = next(i for i, name in ports('In') if name == 'Model 12 MIDI')
check(midi.midiInOpen(c.byref(handle), device, callback, c.c_size_t(0), 0x30000))
try:
    for _ in range(4):
        data = c.create_string_buffer(1024)
        header = Header(data=c.addressof(data), length=len(data))
        check(midi.midiInPrepareHeader(handle, c.byref(header), c.sizeof(header)))
        buffers.append((data, header))
        check(midi.midiInAddBuffer(handle, c.byref(header), c.sizeof(header)))
    check(midi.midiInStart(handle))
    with (root/'model12-input.jsonl').open('a', encoding='utf8', buffering=1) as log:
        print("READY Model 12 MIDI", flush=True)
        until = time.monotonic() + 1200
        while time.monotonic() < until and not (root/'end-capture').exists():
            try:
                stamp, packet, addr = q.get(timeout=.25)
            except Empty:
                continue
            if packet:
                log.write(json.dumps([stamp, packet])+'\n')
            if addr:
                check(midi.midiInAddBuffer(handle, c.c_void_p(addr), c.sizeof(Header)))
finally:
    midi.midiInStop(handle)
    midi.midiInReset(handle)
    for _, header in buffers:
        midi.midiInUnprepareHeader(handle,c.byref(header),c.sizeof(header))
    midi.midiInClose(handle)

