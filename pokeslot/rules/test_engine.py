import unittest
from fractions import Fraction
from engine import MACHINE, audit, evaluate_grid, grid_from_stops, settle, settings

class AccountingTests(unittest.TestCase):
    def test_unique_lines(self):
        self.assertEqual(len({tuple(line) for line in MACHINE['paylines']}), 25)

    def test_longest_prefix_for_every_symbol(self):
        for symbol in range(6):
            for length in (3, 4, 5):
                with self.subTest(symbol=symbol, length=length):
                    grid = [[5, symbol if col < length else (symbol + 1) % 6, 5] for col in range(5)]
                    wins = evaluate_grid(grid, 2, 1)
                    self.assertEqual(len(wins), 1)
                    self.assertEqual(wins[0]['matched'], length)
                    self.assertEqual(wins[0]['amount'], MACHINE['paytable'][symbol][length - 3] * 2)

    def test_no_right_only_win(self):
        grid = [[0, value, 0] for value in [0, 1, 2, 2, 2]]
        self.assertEqual(evaluate_grid(grid, 1, 1), [])

    def test_two_matches_do_not_pay(self):
        grid = [[0, value, 0] for value in [2, 2, 3, 4, 5]]
        self.assertEqual(evaluate_grid(grid, 1, 1), [])

    def test_all_active_wins_are_added(self):
        grid = [[5, 5, 5] for _ in range(5)]
        for count in MACHINE['line_counts']:
            wins = evaluate_grid(grid, 9, count)
            self.assertEqual(len(wins), count)
            self.assertEqual(sum(w['amount'] for w in wins), 500 * 9 * count)

    def test_line_count_activates_prefix(self):
        grid = grid_from_stops([0] * 5)
        self.assertEqual([w['line'] for w in evaluate_grid(grid, 1, 1)], [1])
        self.assertEqual([w['line'] for w in evaluate_grid(grid, 1, 5)], [1, 2, 3])

    def test_cost_and_balance(self):
        for bet in MACHINE['bets_per_line']:
            for count in MACHINE['line_counts']:
                result = settle(1000, [0] * 5, bet, count)
                self.assertEqual(result['cost'], bet * count)
                self.assertEqual(result['after'], 1000 - bet * count + result['payout'])
                self.assertEqual(result['payout'], sum(w['amount'] for w in result['wins']))

    def test_insufficient_credits(self):
        with self.assertRaisesRegex(ValueError, 'Insufficient'):
            settle(24, [0] * 5)

    def test_exact_credits_accepted(self):
        self.assertEqual(settle(25, [0] * 5)['cost'], 25)

    def test_invalid_settings(self):
        for bet, count in [(0,25),(10,25),(1,0),(1,26),(1,2),(True,25),(1,1.0)]:
            with self.subTest(bet=bet, count=count), self.assertRaises(ValueError):
                settings(bet, count)

    def test_invalid_stops(self):
        for stops in [[0]*4, [-1,0,0,0,0], [6,0,0,0,0], [True,0,0,0,0]]:
            with self.subTest(stops=stops), self.assertRaises(ValueError):
                grid_from_stops(stops)

    def test_overflow_rejected(self):
        with self.assertRaises(OverflowError):
            settle(MACHINE['credit_limit'], [0]*5)

    def test_input_not_mutated(self):
        stops = [0,1,2,3,4]
        settle(1000, stops)
        self.assertEqual(stops, [0,1,2,3,4])

    def test_exhaustive_math(self):
        result = audit()
        self.assertEqual(result['outcomes'], 7776)
        self.assertEqual(Fraction(result['rtp_fraction']), Fraction(3455,3888))
        self.assertEqual(result['maximum_payout_bet_1_lines_25'], 1250)

if __name__ == '__main__':
    unittest.main()
