OUT := build/accounting
.PHONY: all
all: $(OUT)/accounting.gb
$(OUT)/tables.inc: accounting_tables.py rules/engine.py rules/machine.json
	mkdir -p $(OUT)
	python3 accounting_tables.py
$(OUT)/main.o: src/accounting_test.asm $(OUT)/tables.inc
	rgbasm -Wall -o $@ $<
$(OUT)/accounting.gb: $(OUT)/main.o
	rgblink -m $(OUT)/accounting.map -n $(OUT)/accounting.sym -o $@ $<
	rgbfix -v -p 0 -m 0x19 -t POKESLOTMATH $@
