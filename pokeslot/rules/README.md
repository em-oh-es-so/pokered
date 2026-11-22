# First-machine rules and reference accounting

This is a Python reference and machine-data definition, not ROM integration. The approved cabinet and verified renderer are unchanged.

Kanto Classic starts with 1,000 virtual credits. Bet 1-9 per active line; select 1, 5, 10, 15, 20 or 25 lines. Total cost is bet times active lines. The first N line definitions are active, with the middle horizontal line first. Rows are 0=top, 1=middle, 2=bottom. Stops identify the top visible symbol; the next two strip entries fill the middle and bottom rows.

Three, four or five identical symbols starting at the leftmost reel pay. Only the longest match pays on each line. Add all winning active lines, including overlapping lines. Paytable columns are 3/4/5 matches and values multiply the bet per line. Payout is gross; subtract the spin cost only once. Ditto is ordinary in this baseline. No wild substitutions, scatters, free spins, adaptive odds or real-money features.

Paytable: Bulbasaur 10/30/100; Charmander 12/40/150; Squirtle 15/50/200; Pikachu 20/70/300; Eevee 25/90/400; Ditto 30/100/500.

Reels currently contain each of the six species once. Audit enumerates all 7,776 combinations under uniform independent stops and cross-checks the theoretical return with a separate per-line formula. The resulting 88.8631687% is a property of the proposed mathematical model, not a verified property of ROM randomness. An eventual ROM sampler must avoid biased stop selection. The renderer's fixed countdowns are not random-number generation.

Reference balances use unsigned 32-bit bounds and reject overflow. Do not port this to an 8-bit balance or silently truncate payouts. The existing four-digit cabinet counters will need a readable full-value display solution before accounting is integrated. Saving and resets also require explicit game behavior before ROM integration.

Run `python3 -m unittest discover -s pokeslot/rules -p 'test_*.py'` and `python3 pokeslot/rules/engine.py` from the repository root. Reference tests must later be matched against assembled ROM behavior; passing Python tests alone does not verify the game.
