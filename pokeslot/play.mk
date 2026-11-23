OUT := build/play
.PHONY: all
all: $(OUT)/pokeslot-play.gbc
$(OUT)/main.asm: play_build.py speed_build.py src/play_runtime.asm src/cabinet_five.asm src/accounting_test.asm five_assets.py accounting_tables.py preview_classic.py preview_layout.py rules/engine.py rules/machine.json
	python3 play_build.py
	python3 speed_build.py
$(OUT)/main.o: $(OUT)/main.asm
	rgbasm -Wall -o $@ $<
$(OUT)/pokeslot-play.gbc: $(OUT)/main.o
	rgblink -m $(OUT)/play.map -n $(OUT)/play.sym -o $@ $<
	rgbfix -v -C -p 0 -m 0x19 -t POKESLOTPLAY $@
