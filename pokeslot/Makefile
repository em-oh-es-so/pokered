BUILD := build
.PHONY: all clean
all: $(BUILD)/pokeslot.gb
$(BUILD)/generated.asm: generate.py $(wildcard ../gfx/pokemon/front/*.png)
	mkdir -p $(BUILD)
	python3 generate.py
$(BUILD)/main.o: $(BUILD)/generated.asm
	rgbasm -Wall -o $@ $<
$(BUILD)/pokeslot.gb: $(BUILD)/main.o
	rgblink -m $(BUILD)/pokeslot.map -n $(BUILD)/pokeslot.sym -o $@ $<
	rgbfix -v -p 0 -t POKESLOT $@
clean:
	rm -rf $(BUILD)
