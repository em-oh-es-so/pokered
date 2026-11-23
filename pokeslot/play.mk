OUT := build/play
.PHONY: all highlight-test
all: $(OUT)/pokeslot-play.gbc
highlight-test: $(OUT)/highlights-test.gbc
$(OUT)/main.asm: play_build.py speed_build.py win_build.py src/win_runtime.asm src/play_runtime.asm src/cabinet_five.asm src/accounting_test.asm five_assets.py accounting_tables.py preview_classic.py preview_layout.py rules/engine.py rules/machine.json test_play_rom.py
	python3 win_build.py
$(OUT)/main.o: $(OUT)/main.asm
	rgbasm -Wall -o $@ $<
$(OUT)/pokeslot-play.gbc: $(OUT)/main.o
	rgblink -m $(OUT)/play.map -n $(OUT)/play.sym -o $@ $<
	rgbfix -v -C -p 0 -m 0x19 -t POKESLOTPLAY $@
$(OUT)/highlight-test.o: $(OUT)/main.asm
	rgbasm -Wall -D WIN_TESTS=1 -o $@ $<
$(OUT)/highlights-test.gbc: $(OUT)/highlight-test.o
	rgblink -n $(OUT)/highlights-test.sym -o $@ $<
	rgbfix -v -C -p 0 -m 0x19 -t WINTEST $@
