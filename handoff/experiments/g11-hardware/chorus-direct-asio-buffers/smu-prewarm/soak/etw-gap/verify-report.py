from pathlib import Path
import json,re
p=Path(__file__).resolve().parent
for md in [p/'REPORT.zh-TW.md',p.parent/'dip486'/'REPORT.zh-TW.md',p.parent/'REPORT.zh-TW.md',p.parents[3]/'ROUND4-ACCEPTANCE.zh-TW.md']:
    assert md.is_file(),md
    text=md.read_text(encoding='utf-8-sig')
    links=re.findall(r'\]\(([^)]+)\)',text)
    if md.parent==p:
        for link in links:
            if link.startswith(('https://','http://','#')):continue
            assert (md.parent/link).is_file(),(md,link)
    else:assert any((md.parent/link).resolve()==p/'REPORT.zh-TW.md' for link in links if not link.startswith(('https://','http://','#')))
for tag in ['usb64r','usb128']:
    read=lambda pref:json.loads((p/f'{pref}-{tag}.json').read_text())
    cov=read('coverage');assert cov['stopped'] and cov['clocks']==25920 and cov['transport_other']==[[242,64,0],[251],[252]]
    assert cov['cymbals']==[34,34],cov['cymbals']
    s=read('stages')[0];assert abs(s['ms']-sum(s['stages'].values()))<.001
    data=read('usb-evidence');assert data['port_path']==[3,4,3] and data['details'][0]['pipes']
    assert (p/f'decoded-{tag}'/'summary.json').is_file()
print('Report links, transport, cymbals, stage totals, USB device routing and both capture summaries verified.')
