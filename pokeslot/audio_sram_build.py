from pathlib import Path
from audio_ram_probe import prepare

OUT=Path(__file__).resolve().parent/'build/audio'
def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

prepare()
inc=(OUT/'ram-probe.inc').read_text()
for bank in range(1,7):
    inc+=f'\nSECTION "Bank tag {bank}", ROMX[$4000], BANK[{bank}]\n    db {bank}, $53, $52, $41\n'
(OUT/'sram-audio.inc').write_text(inc)
bench=(OUT/'ram-probe.asm').read_text()
bench=replace(bench,'INCLUDE "build/audio/ram-probe.inc"','INCLUDE "build/audio/sram-audio.inc"')
for offset in (0,3,6,9,12):
    old=f'    call ${0x4000+offset:04x}\n'
    assert old in bench,old
    bench=bench.replace(old,f'    call ${0xa000+offset:04x}\n')
bench=replace(bench,'    ld [$3000], a\n','    ld [$3000], a\n    call CopyAudioToSRAM\n')
bench=replace(bench,'    ld a, [Song]\n    cp 6\n','    ld a, [Song]\n    cp 1\n')
bench=replace(bench,'    add 24\n    ld [$2000], a\n','')
loader='''CopyAudioToSRAM:
    ld a, $0a
    ld [$0000], a
    xor a
    ld [$4000], a
    ld hl, $4000
    ld de, $a000
    ld bc, AudioRAMProbeEnd-AudioRAMProbeStart
.copy
    ld a, [hli]
    ld [de], a
    inc de
    dec bc
    ld a, b
    or c
    jr nz, .copy
    ld a, 1
    ld [$2000], a
    ret
'''
bench=replace(bench,'CryPresets:\n',loader+'CryPresets:\n')
(OUT/'sram-audio.asm').write_text(bench)
