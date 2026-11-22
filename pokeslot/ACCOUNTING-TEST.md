# ROM accounting checkpoint

This adds a separate headless test ROM; it does not change the working cabinet ROM. No manual Delta import is needed. The test ROM intentionally has no user interface.

Payout tables are generated from the accepted machine definition for all 7,776 stop combinations and all six active-line settings. The assembled kernel looks up the unit-bet payout, multiplies by the bet, subtracts the wager, and adds the payout with unsigned 32-bit credit arithmetic. Insufficient-credit, invalid-input and overflow transactions are rejected without changing the returned balance.

This approach tests actual assembled table indexing and accounting against Python, not an independently written assembly line evaluator. The final game can reuse the generated payout tables. Costs are at most 225 and currently reachable gross payouts are checked to fit 16 bits; credits use 32 bits. If future machines exceed these bounds, the generator must fail rather than silently truncate.

The PyBoy harness checks every stop combination at bet 1 / 25 lines, all bet/line combinations on selected outcomes, credit-boundary cases, and rejected transactions. Passing does not verify RNG, animation, saving, live number rendering or full-game integration.

Mailbox symbols are resolved from the linker .sym file. Status 1=success, 2=invalid input, 3=insufficient credits, 4=overflow. Credits and ResultCredits are little-endian 32-bit values; Payout is little-endian 16-bit. Stops are top-row indices. Command 1 requests a transaction; Ready 0xa5 signals initialization.

Build with `make -C pokeslot -f accounting.mk`, then run `python3 pokeslot/test_accounting_rom.py` with PyBoy 2.x installed. The existing ROM targets remain unchanged.
