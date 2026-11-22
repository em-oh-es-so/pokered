OUT := build/stream
.PHONY: all
all: $(OUT)/cabinet-test.gbc
$(OUT)/assets.inc: stream_assets.py preview_classic.py preview_layout.py $(wildcard ../gfx/pokemon/front/*.png) $(wildcard ../gfx/font/*.png) $(wildcard ../gfx/slots/*)
	mkdir -p $(OUT)
	python3 stream_assets.py
$(OUT)/main.o: src/cabinet_test.asm $(OUT)/assets.inc
	rgbasm -Wall -o $@ $<
$(OUT)/cabinet-test.gbc: $(OUT)/main.o
	rgblink -m $(OUT)/cabinet-test.map -n $(OUT)/cabinet-test.sym -o $@ $<
	rgbfix -v -C -p 0 -m 0x19 -t POKESLOTTEST $@
