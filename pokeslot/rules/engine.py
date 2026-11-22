from pathlib import Path
from fractions import Fraction
from itertools import product
import json

MACHINE = json.loads(Path(__file__).with_name('machine.json').read_text())
assert len(MACHINE['symbols']) == len(MACHINE['paytable']) == 6
assert len(MACHINE['reels']) == 5
assert all(sorted(reel) == list(range(6)) for reel in MACHINE['reels'])
assert len(MACHINE['paylines']) == len({tuple(line) for line in MACHINE['paylines']}) == 25
assert all(len(line) == 5 and all(row in (0, 1, 2) for row in line) for line in MACHINE['paylines'])
assert all(len(row) == 3 and all(type(p) is int and p > 0 for p in row) for row in MACHINE['paytable'])

def integer(value, name):
    if type(value) is not int:
        raise ValueError(name + ' must be an integer')
    return value

def settings(bet, active_lines):
    integer(bet, 'bet')
    integer(active_lines, 'active_lines')
    if bet not in MACHINE['bets_per_line'] or active_lines not in MACHINE['line_counts']:
        raise ValueError('Unsupported bet or active-line count')
    return bet * active_lines

def grid_from_stops(stops):
    if len(stops) != 5:
        raise ValueError('Exactly five stops required')
    grid = []
    for index, stop in enumerate(stops):
        integer(stop, 'stop')
        reel = MACHINE['reels'][index]
        if not 0 <= stop < len(reel):
            raise ValueError('Stop outside reel')
        grid.append([reel[(stop + row) % len(reel)] for row in range(3)])
    return grid

def evaluate_grid(grid, bet=1, active_lines=25):
    settings(bet, active_lines)
    if len(grid) != 5 or any(len(column) != 3 for column in grid):
        raise ValueError('Expected five columns of three symbols')
    if any(type(symbol) is not int or not 0 <= symbol < 6 for column in grid for symbol in column):
        raise ValueError('Invalid symbol')
    wins = []
    for index, line in enumerate(MACHINE['paylines'][:active_lines], 1):
        symbols = [grid[column][line[column]] for column in range(5)]
        matched = 1
        while matched < 5 and symbols[matched] == symbols[0]:
            matched += 1
        if matched < 3:
            continue
        multiplier = MACHINE['paytable'][symbols[0]][matched - 3]
        wins.append({'line': index, 'symbol': MACHINE['symbols'][symbols[0]], 'matched': matched, 'multiplier': multiplier, 'amount': multiplier * bet})
    return wins

def settle(credits, stops, bet=1, active_lines=25):
    integer(credits, 'credits')
    if not 0 <= credits <= MACHINE['credit_limit']:
        raise ValueError('Credits outside unsigned 32-bit range')
    cost = settings(bet, active_lines)
    if credits < cost:
        raise ValueError('Insufficient credits')
    grid = grid_from_stops(stops)
    wins = evaluate_grid(grid, bet, active_lines)
    payout = sum(win['amount'] for win in wins)
    after = credits - cost + payout
    if after > MACHINE['credit_limit']:
        raise OverflowError('Credit overflow; reject settlement rather than wrap or truncate')
    return {'before': credits, 'cost': cost, 'payout': payout, 'after': after, 'wins': wins, 'grid': grid}

def audit():
    gross = hits = maximum = 0
    for stops in product(range(6), repeat=5):
        payout = sum(win['amount'] for win in evaluate_grid(grid_from_stops(stops)))
        gross += payout
        hits += bool(payout)
        maximum = max(maximum, payout)
    rtp = Fraction(gross, 6 ** 5 * 25)
    independent = sum((Fraction(p[0] * 30 + p[1] * 5 + p[2], 6 ** 5) for p in MACHINE['paytable']), Fraction())
    assert rtp == independent
    return {'outcomes': 6 ** 5, 'rtp_fraction': str(rtp), 'theoretical_return_percent': float(rtp * 100), 'any_payout_percent': hits / 6 ** 5 * 100, 'maximum_payout_bet_1_lines_25': maximum, 'rom_verified': False, 'assumptions': 'Uniform independent stops; six-symbol cyclic strips; no wilds or bonuses'}

if __name__ == '__main__':
    report = audit()
    out = Path(__file__).resolve().parents[1] / 'build/math'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'math-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
