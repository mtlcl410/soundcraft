exec((d/'r2-pending.py').read_text(encoding='utf-8-sig'))
s=s.replace('(gap <= 1000 || (last >= 2500 && gap > last + last / 2))', 'gap <= 1000')
