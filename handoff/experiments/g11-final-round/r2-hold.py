exec((d/'r2-pending.py').read_text(encoding='utf-8-sig'))
s=s.replace('let precise = !s.packed_delivery', 'let precise = !s.recovering_tempo_step && !s.packed_delivery')
