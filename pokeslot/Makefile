BUILD := build
.PHONY: all clean
all: $(BUILD)/pokeslot.gb
$(BUILD)/assets.inc: scrolling_assets.py $(wildcard ../gfx/pokemon/front/*.png)
	mkdir -p $(BUILD)
	python3 scrolling_assets.py
$(BUILD)/main.o: src/scrolling.asm $(BUILD)/assets.inc
	rgbasm -Wall -o $@ $<
$(BUILD)/pokeslot.gb: $(BUILD)/main.o
	rgblink -m $(BUILD)/pokeslot.map -n $(BUILD)/pokeslot.sym -o $@ $<
	rgbfix -v -p 0 -t POKESLOT $@
clean:
	rm -rf $(BUILD)
