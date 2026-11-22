# Pokeslot interactive demo

Build: install RGBDS 0.9.1 and Python Pillow, then run `make -C pokeslot`. The workflow installs these dependencies and packages the ROM.

This milestone adds five reels with three visible symbols each, compact source-derived Pokemon artwork, A-button spins, staggered stops, and a temporary coin counter. Up/Down selects bets from 1 to 9. Select resets coins to 200 and bet to 1 while idle. Spins deduct the displayed bet. No paylines, payouts, bonus rules, saving, or audio are implemented. The bet is a demo spin cost, not a per-line wager. Randomness is a visual prototype, not a verified payout RNG.

The machine definition in generate.py selects a name and roster. Only the first definition is used at present; runtime machine selection, reel strips, symbol weights, and payout data will be added later. The starter roster is Bulbasaur, Charmander, Squirtle, Pikachu, Eevee, and Ditto.

All original assets remain intact. The compact 16x16 symbols are generated automatically and require visual review in Delta. The original boot-only src/main.asm is retained as a reference but is no longer the Makefile entry point.

Test checklist: build succeeds; title and six species are recognizable; each A press starts one spin; five reels stop in order; holding A does not repeatedly spin; Up/Down respects 1-9; a spin subtracts the chosen bet; insufficient coins blocks a spin; Select restores 200 while idle. Saving and 25-payline accounting are later milestones.

Unofficial fan project. Pokemon and original assets belong to their respective rights holders. Upstream: https://github.com/pret/pokered.
