"""Compare absolute wire ordinals and native send order in a single uninterrupted roll."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def decode(path):
    pulses = []
    transport = []
    running = False
    position = 0
    with path.open() as stream:
        for row in csv.DictReader(stream):
            msg = bytes.fromhex(row['hex'])
            if msg == b'\xfa':
                position, running = 0, True
            elif msg == b'\xfb':
                running = True
            elif msg == b'\xfc':
                running = False
            elif len(msg) == 3 and msg[0] == 0xf2:
                position = 6 * (msg[1] | msg[2] << 7)
            elif msg == b'\xf8' and running:
                pulses.append(position)
                position += 1
            if msg in (b'\xfa', b'\xfb', b'\xfc'):
                transport.append(msg.hex())
    return pulses, transport

def main():
    results = []
    for name in ('stop-witness-comparison', 'stop-compensation-abba'):
        for measurement in json.loads((HERE / (name + '.json')).read_text()):
            folder = HERE / measurement['label']
            source, controls = decode(folder/'ingress.csv')
            dest, emitted = decode(folder/'egress.csv')
            assert controls == emitted == ['fa','fc']
            assert dest[:len(source)] == source and source == list(range(576))
            begin = measurement['receipt_to_f8_handoff_ms']
            finish = measurement['receipt_to_f8_handoff_end_ms']
            results.append(dict(trial=folder.name,last_valid=source[-1],last_output=dest[-1],
                handoff_ms=begin,returned_ms=finish,classification='valid' if dest==source else
                'preventable at handoff' if begin>0 else 'already sent' if finish<0 else 'overlapping call'))
    (HERE/'stop-ordinal-replay.json').write_text(json.dumps(results,indent=2))
    for row in results:
        print(*row.values())
if __name__=='__main__':
    main()

