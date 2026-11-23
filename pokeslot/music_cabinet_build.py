from pathlib import Path
import shutil
from audio_cabinet_layout import prepare

HERE=Path(__file__).resolve().parent
PLAY=HERE/'build/play'
OUT=HERE/'build/music-cabinet'
def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

prepare()
shutil.copytree(PLAY,OUT,dirs_exist_ok=True)
for path in OUT.rglob('*'):
    if path.suffix in ('.asm','.inc'):
        path.write_text(path.read_text().replace('build/play/','build/music-cabinet/'))
inc=(HERE/'build/audio/cabinet-audio-layout.inc').read_text()
inc=replace(inc,'    ds 60\n','''CabinetAudioInitialized: ds 1
CabinetAudioTicks: ds 2
CabinetAudioLate: ds 1
CabinetAudioDeadlineMiss: ds 1
CabinetAudioEntryLY: ds 1
CabinetAudioExitLY: ds 1
CabinetAudioMaximumSpan: ds 1
    ds 52
''')
(OUT/'audio.inc').write_text(inc)
asm=(HERE/'build/audio/cabinet-audio-layout.asm').read_text()
asm=asm.replace('build/play/','build/music-cabinet/')
asm=replace(asm,'INCLUDE "build/audio/cabinet-audio-layout.inc"','INCLUDE "build/music-cabinet/audio.inc"')
asm=replace(asm,'Boot:\n    di\n    ld sp, $dfff\n','Boot:\n    di\n    ld sp, $dfff\n    xor a\n    ld [CabinetAudioInitialized], a\n')
enable='    ld a, $91\n    ldh [$FF40], a\n'
assert asm.count(enable)==2
asm=asm.replace(enable,'    call CabinetAudioInit\n'+enable,1)
critical='''.notHBlank
    ldh a, [$FF41]
    and 3
    jr z, .notHBlank
    ld a, [Length]
    ldh [$FF55], a
'''
asm=replace(asm,critical,'''.notHBlank
    di
    ldh a, [$FF41]
    and 3
    jr nz, .dmaStartReady
    ei
    jr .notHBlank
.dmaStartReady
    ld a, [Length]
    ldh [$FF55], a
    ei
''')
asm+='''
SECTION "Music STAT vector", ROM0[$48]
    jp CabinetAudioIRQ
SECTION "Cabinet music driver", ROM0
CabinetAudioInit:
    ld a, [CabinetAudioInitialized]
    cp $a5
    ret z
    ld hl, CabinetAudioControlStart
    ld bc, CabinetAudioControlEnd-CabinetAudioControlStart
.clear
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .clear
    ld a, $0a
    ld [$0000], a
    xor a
    ld [$4000], a
    ld [$3000], a
    ld a, 24
    ld [$2000], a
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
    ld a, $80
    ldh [$FF26], a
    call $a006
    ld a, NATIVE_SONG_ID
    call $a00c
    ld a, $a5
    ld [CabinetAudioInitialized], a
    ld a, 80
    ldh [$FF45], a
    ld a, $40
    ldh [$FF41], a
    xor a
    ldh [$FF0F], a
    ld a, 2
    ldh [$FFFF], a
    ei
    ret
CabinetAudioIRQ:
    push af
    push bc
    push de
    push hl
    ldh a, [$FF44]
    ld [CabinetAudioEntryLY], a
    cp 80
    jr z, .onTime
    ld a, 1
    ld [CabinetAudioLate], a
.onTime
    call $a000
    ldh a, [$FF44]
    ld [CabinetAudioExitLY], a
    cp 144
    jr nc, .deadline
    cp 80
    jr nc, .span
.deadline
    ld a, 1
    ld [CabinetAudioDeadlineMiss], a
.span
    ld a, [CabinetAudioExitLY]
    ld b, a
    ld a, [CabinetAudioEntryLY]
    ld c, a
    ld a, b
    sub c
    jr nc, .spanReady
    add 154
.spanReady
    ld b, a
    ld a, [CabinetAudioMaximumSpan]
    cp b
    jr nc, .tick
    ld a, b
    ld [CabinetAudioMaximumSpan], a
.tick
    ld hl, CabinetAudioTicks
    inc [hl]
    jr nz, .checkEnd
    inc hl
    inc [hl]
.checkEnd
    ldh a, [$FF44]
    cp 144
    jr c, .exit
    ld a, 1
    ld [CabinetAudioDeadlineMiss], a
.exit
    pop hl
    pop de
    pop bc
    pop af
    reti
'''
(OUT/'main.asm').write_text(asm)
(OUT/'README.txt').write_text('EXPERIMENTAL POKESLOT MUSIC-ONLY CABINET CHECKPOINT\nGame Corner music only. Gameplay effects, payout cries, music selection and rotation are NOT enabled.\nA spin; Up/Down bet; Left/Right active lines; B paytable; START win review.\nThis candidate is separate from the approved silent cabinet. Automated checks do not replace a Delta playtest or listening approval. Music scheduling pauses while the LCD is disabled for menu/graphics loading.\nNo save feature is added. Keep your approved cabinet ZIP as the baseline.\n')
