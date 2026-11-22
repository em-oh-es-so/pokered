from pathlib import Path
from itertools import product
import json
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'rules'))
from engine import MACHINE, evaluate_grid, grid_from_stops

OUT = HERE / 'build/accounting'
OUT.mkdir(parents=True, exist_ok=True)
inc = ''
maximum = 0
for index, count in enumerate(MACHINE['line_counts']):
    values = []
    for stops in product(range(6), repeat=5):
        value = sum(w['amount'] for w in evaluate_grid(grid_from_stops(stops), 1, count))
        assert 0 <= value <= 65535
        maximum = max(maximum, value * max(MACHINE['bets_per_line']))
        values.append(value)
    blob = struct.pack('<7776H', *values)
    assert len(blob) <= 16384
    (OUT / f'payouts-{index}.bin').write_bytes(blob)
    inc += f'SECTION "Payouts {index}", ROMX[$4000], BANK[{index + 1}]\n    INCBIN "build/accounting/payouts-{index}.bin"\n'
assert maximum <= 65535
inc += 'SECTION "Accounting Constants", ROM0\nLineCounts: db ' + ', '.join(map(str, MACHINE['line_counts'])) + '\n'
(OUT / 'tables.inc').write_text(inc)
(OUT / 'table-manifest.json').write_text(json.dumps({'outcomes_per_line_count': 7776, 'line_counts': MACHINE['line_counts'], 'maximum_supported_gross_payout': maximum, 'format': 'uint16 little endian, lexicographic stops, first stop most significant base-6 digit', 'method': 'Precomputed reference payouts; ROM tests indexing, multiplication and settlement, not an independent assembly line matcher'}, indent=2))
