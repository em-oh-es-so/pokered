from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/music-cabinet'
assets=json.loads((HERE/'build/audio/audio-assets.json').read_text())
names=['button','spin','stop','reward','denied']
def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

inc=(OUT/'audio.inc').read_text()
inc=replace(inc,'    ds 52\n','''CabinetEffectQueue: ds 8
CabinetEffectHead: ds 1
CabinetEffectTail: ds 1
CabinetEffectCount: ds 1
CabinetEffectCooldown: ds 1
CabinetEffectOverflow: ds 1
CabinetEffectPlayed: ds 10
CabinetEffectQueued: ds 10
CabinetEffectLastNative: ds 1
CabinetEffectPresenceFault: ds 1
    ds 17
''')
(OUT/'audio.inc').write_text(inc)
path=OUT/'main.asm'
asm=path.read_text()
asm=replace(asm,'    ld [PressedA], a\n    ld a, b\n','    ld [PressedA], a\n    call CabinetButtonEffect\n    ld a, b\n')
asm=replace(asm,'    ld [Status], a\n    cp 1\n    ret nz\n    call WinReset\n','''    ld [Status], a
    cp 1
    jr z, .effectsAccepted
    call CabinetDeniedEffect
    ret
.effectsAccepted
    call WinReset
''')
asm=replace(asm,'    ld a, 1\n    ld [SpinActive], a\n    ret\nFinishSpin:\n','    ld a, 1\n    ld [SpinActive], a\n    call CabinetSpinEffect\n    ret\nFinishSpin:\n')
asm=replace(asm,'    sub c\n    ld [hl], a\n    ld hl, Phases\n','''    sub c
    ld [hl], a
    push af
    and a
    call z, CabinetStopEffect
    pop af
    ld hl, Phases
''')
asm=replace(asm,'    ld [SpinActive], a\n    call WinCollect\n    ret\n','    ld [SpinActive], a\n    call WinCollect\n    call CabinetPayoutEffect\n    ret\n')
asm=replace(asm,'.onTime\n    call $a000\n','.onTime\n    call CabinetEffectService\n    call $a000\n')
asm+='''
SECTION "Cabinet effect dispatcher", ROM0
CabinetButtonEffect:
    push af
    ld a, [SpinActive]
    and a
    jr nz, .exit
    ld a, [PressedA]
    and $fe
    jr z, .exit
    ld a, 1
    call CabinetQueueEffect
.exit
    pop af
    ret
CabinetSpinEffect:
    push af
    ld a, 2
    call CabinetQueueEffect
    pop af
    ret
CabinetStopEffect:
    push af
    ld a, 3
    call CabinetQueueEffect
    pop af
    ret
CabinetPayoutEffect:
    push af
    ld a, [Payout]
    ld b, a
    ld a, [Payout+1]
    or b
    jr z, .exit
    ld a, 4
    call CabinetQueueEffect
.exit
    pop af
    ret
CabinetDeniedEffect:
    push af
    ld a, 5
    call CabinetQueueEffect
    pop af
    ret
CabinetQueueEffect:
    push af
    push bc
    push de
    push hl
    di
    ld c, a
    dec a
    cp 5
    jr nc, .exit
    ld a, c
    cp 1
    jr nz, .space
    ld a, [CabinetEffectCount]
    and a
    jr nz, .exit
.space
    ld a, [CabinetEffectCount]
    cp 8
    jr nc, .overflow
    ld a, [CabinetEffectTail]
    ld e, a
    ld d, 0
    ld hl, CabinetEffectQueue
    add hl, de
    ld [hl], c
    inc e
    ld a, e
    and 7
    ld [CabinetEffectTail], a
    ld hl, CabinetEffectCount
    inc [hl]
    ld a, c
    dec a
    add a
    ld e, a
    ld hl, CabinetEffectQueued
    add hl, de
    inc [hl]
    jr nz, .exit
    inc hl
    inc [hl]
    jr .exit
.overflow
    ld a, 1
    ld [CabinetEffectOverflow], a
.exit
    ei
    pop hl
    pop de
    pop bc
    pop af
    ret
CabinetEffectService:
    ld a, [CabinetEffectCooldown]
    and a
    jr z, .ready
    dec a
    ld [CabinetEffectCooldown], a
    ret
.ready
    ld a, [CabinetEffectCount]
    and a
    ret z
    dec a
    ld [CabinetEffectCount], a
    ld a, [CabinetEffectHead]
    ld e, a
    ld d, 0
    ld hl, CabinetEffectQueue
    add hl, de
    ld c, [hl]
    inc e
    ld a, e
    and 7
    ld [CabinetEffectHead], a
    ld a, c
    push af
    dec a
    ld e, a
    ld hl, CabinetEffectNativeIDs
    add hl, de
    ld a, [hl]
    ld [CabinetEffectLastNative], a
    push af
    call $a003
    pop af
    call $a00c
    ld a, [CabinetEffectLastNative]
    ld c, a
    ld hl, wChannelSoundIDs+4
    ld b, 4
.checkChannel
    ld a, [hli]
    cp c
    jr z, .confirmed
    dec b
    jr nz, .checkChannel
    ld a, 1
    ld [CabinetEffectPresenceFault], a
.confirmed
    pop af
    dec a
    add a
    ld e, a
    ld d, 0
    ld hl, CabinetEffectPlayed
    add hl, de
    inc [hl]
    jr nz, .cooldown
    inc hl
    inc [hl]
.cooldown
    ld a, 2
    ld [CabinetEffectCooldown], a
    ret
CabinetEffectNativeIDs:
'''+ '    db '+','.join(str(assets['sound_ids'][name]) for name in names)+'\n'
path.write_text(asm)
(OUT/'effects-layout.json').write_text(json.dumps({'logical_events':names,'native_ids':[assets['sound_ids'][name] for name in names],'queue_capacity':8,'minimum_dispatch_spacing_frames':3,'button_requests_coalesced_while_queue_nonempty':True,'pokemon_cries_enabled':False},indent=2))
(OUT/'README.txt').write_text('EXPERIMENTAL POKESLOT MUSIC AND CABINET EFFECTS CHECKPOINT\nGame Corner music; button, accepted spin, each reel stop, paying-spin payout and rejected-spin effects. Effects use a bounded FIFO; button requests coalesce while events are pending.\nPokemon cries, music selection, audio settings and track rotation are NOT enabled.\nA spin; Up/Down bet; Left/Right lines; B paytable; START win review. Music scheduling pauses during LCD-off menu/graphics loading.\nSeparate candidate: keep the approved cabinet and music-only ZIPs. Automated dispatch checks do not replace listening or a Delta playtest. No saving is added.\n')
