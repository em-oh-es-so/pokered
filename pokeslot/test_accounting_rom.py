from pathlib import Path
from itertools import product
import importlib.metadata
import json
import sys
from pyboy import PyBoy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'rules'))
from engine import MACHINE, settle
OUT = HERE / 'build/accounting'
symbols = {}
for line in (OUT / 'accounting.sym').read_text().splitlines():
    parts = line.split()
    if len(parts) == 2 and ':' in parts[0] and not parts[0].startswith(';'):
        symbols[parts[1]] = int(parts[0].split(':')[1], 16)
for name in ['Ready','Command','Status','Credits','Stops','Bet','LineIndex','ResultCredits','Payout','Cost']:
    assert name in symbols, name
p = PyBoy(str(OUT / 'accounting.gb'), window='null')
p.set_emulation_speed(0)
p.memory[symbols['Ready']] = 0
passed = 0

def write(name, data):
    address = symbols[name]
    p.memory[address:address + len(data)] = list(data)

def read(name, length):
    address = symbols[name]
    return int.from_bytes(bytes(p.memory[address:address + length]), 'little')

def check(credits, stops, bet, line_index):
    global passed
    expected = None
    try:
        if not 0 <= line_index < 6:
            raise ValueError('Invalid line index')
        expected = settle(credits, stops, bet, MACHINE['line_counts'][line_index])
        status = 1
    except OverflowError:
        status = 4
    except ValueError as error:
        status = 3 if 'Insufficient' in str(error) else 2
    write('Credits', credits.to_bytes(4, 'little'))
    write('Stops', bytes(stops))
    write('Bet', bytes([bet]))
    write('LineIndex', bytes([line_index]))
    write('Status', b'\x00')
    write('Command', b'\x01')
    for _ in range(4):
        assert p.tick(1, False), 'Emulator stopped'
        if read('Status', 1):
            break
    actual_status = read('Status', 1)
    actual_balance = read('ResultCredits', 4)
    context = (credits, stops, bet, line_index)
    assert actual_status == status, (context, actual_status, status)
    if status == 1:
        assert actual_balance == expected['after'], (context, actual_balance, expected)
        assert read('Payout', 2) == expected['payout'], (context, 'payout')
        assert read('Cost', 1) == expected['cost'], (context, 'cost')
    else:
        assert actual_balance == credits, (context, 'Rejected transaction changed balance')
    assert read('Credits', 4) == credits, (context, 'Input credits mutated')
    assert bytes(p.memory[symbols['Stops']:symbols['Stops'] + 5]) == bytes(stops)
    passed += 1

try:
    for _ in range(180):
        assert p.tick(1, False)
        if read('Ready', 1) == 0xa5:
            break
    else:
        raise AssertionError('Accounting ROM did not reach ready state')
    for stops in product(range(6), repeat=5):
        check(1000000, stops, 1, 5)
    for bet in MACHINE['bets_per_line']:
        for line_index in range(6):
            for stops in ([0]*5, [5]*5, [0,1,2,3,4], [5,4,3,2,1]):
                check(1000, stops, bet, line_index)
            for credits in (0,1,24,25,224,225,65535,65536,16777215,16777216,4294967295):
                check(credits, [0]*5, bet, line_index)
    for stops, bet, line_index in [([6,0,0,0,0],1,5), ([255,0,0,0,0],1,5), ([0]*5,0,5), ([0]*5,10,5), ([0]*5,1,6), ([0]*5,1,255)]:
        check(1000, stops, bet, line_index)
    report = {'emulated_transactions_passed': passed, 'all_7776_stops_checked_at_bet_1_lines_25': True, 'all_bets_and_line_counts_checked_on_selected_cases': True, 'unsigned_32_bit_carries_and_overflow_checked': True, 'pyboy_version': importlib.metadata.version('pyboy'), 'method': 'Precomputed reference payout tables with assembly indexing, multiplication and balance arithmetic', 'cabinet_integration_verified': False, 'random_stop_generation_verified': False, 'live_display_verified': False}
    (OUT / 'rom-accounting-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
finally:
    p.stop(save=False)
