OUT := build/five
.PHONY: all
all: $(OUT)/cabinet-five.gbc
$(OUT)/assets.inc: five_assets.py preview_classic.py preview_layout.py $(wildcard ../gfx/pokemon/front/*.png) $(wildcard ../gfx/font/*.png) $(wildcard ../gfx/slots/*)
	mkdir -p $(OUT)
	python3 five_assets.py
$(OUT)/main.o: src/cabinet_five.asm $(OUT)/assets.inc
	rgbasm -Wall -o $@ $<
$(OUT)/cabinet-five.gbc: $(OUT)/main.o
	rgblink -m $(OUT)/cabinet-five.map -n $(OUT)/cabinet-five.sym -o $@ $<
	rgbfix -v -C -p 0 -m 0x19 -t POKESLOTFIVE $@
