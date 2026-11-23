OUT := build/audio
.PHONY: all
all: $(OUT)/native-audio.gbc
$(OUT)/bench.asm: native_audio_build.py audio_compat.py rules/machine.json $(wildcard ../audio/*.asm) $(wildcard ../audio/music/*.asm) $(wildcard ../audio/sfx/*.asm) ../data/pokemon/cries.asm ../ram/wram.asm ../.rgbds-version
	python3 native_audio_build.py
	python3 audio_compat.py
$(OUT)/bench.o: $(OUT)/bench.asm
	rgbasm -Wall -I ../ -o $@ $<
$(OUT)/native-audio.gbc: $(OUT)/bench.o
	rgblink -n $(OUT)/native-audio.sym -m $(OUT)/native-audio.map -o $@ $<
	rgbfix -v -C -p 0 -m 0x19 -t NATIVEAUDIO $@
