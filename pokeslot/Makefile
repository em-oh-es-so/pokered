BUILD := build
.PHONY: all clean
all: $(BUILD)/pokeslot.gb
$(BUILD):
	mkdir -p $@
$(BUILD)/main.o: src/main.asm | $(BUILD)
	rgbasm -Wall -o $@ $<
$(BUILD)/pokeslot.gb: $(BUILD)/main.o
	rgblink -m $(BUILD)/pokeslot.map -n $(BUILD)/pokeslot.sym -o $@ $<
	rgbfix -v -p 0 -t POKESLOT $@
clean:
	rm -rf $(BUILD)
