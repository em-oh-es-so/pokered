from pathlib import Path
import json
import shutil

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/music-cabinet'
def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

manifest=json.loads((HERE/'build/cry-policy/cry-policy-manifest.json').read_text())
assets=json.loads((HERE/'build/audio/audio-assets.json').read_text())
inc=(OUT/'audio.inc').read_text()+'''
SECTION "Cabinet cry state", WRAM0[$c940]
CabinetCryStateStart:
CabinetCryMode: ds 1
CabinetCryActive: ds 1
CabinetCryQueue: ds 8
CabinetCryHead: ds 1
CabinetCryTail: ds 1
CabinetCryCount: ds 1
CabinetCryQueued: ds 2
CabinetCryPlayed: ds 2
CabinetCryCompleted: ds 2
CabinetCryLastSpecies: ds 1
CabinetCryLastPitch: ds 1
CabinetCryLastDuration: ds 1
CabinetCrySelected: ds 1
CabinetCryEligible: ds 1
CabinetCryEncoded: ds 1
CabinetCryOverflow: ds 1
CabinetCrySavedVolume: ds 1
CabinetCryPresenceFault: ds 1
CabinetCryPreviewIndex: ds 1
    ds 3
CabinetCryStateEnd:
'''
for bank,table in enumerate(manifest['tables'],25):
    name=table['filename']
    shutil.copyfile(HERE/'build/cry-policy'/name,OUT/name)
    inc+=f'\nSECTION "Cry decisions {bank}", ROMX[$4000], BANK[{bank}]\n    INCBIN "build/music-cabinet/{name}"\n'
(OUT/'audio.inc').write_text(inc)
path=OUT/'main.asm'
asm=path.read_text()
asm=replace(asm,'    ld a, $a5\n    ld [CabinetAudioInitialized], a\n','    call CabinetCryInit\n    ld a, $a5\n    ld [CabinetAudioInitialized], a\n')
asm=replace(asm,'    call CabinetPayoutEffect\n    ret\n','    call CabinetPayoutEffect\n    call CabinetRequestCry\n    ret\n')
asm=replace(asm,'CabinetEffectService:\n','CabinetEffectService:\n    call CabinetCryService\n    ret nz\n')
asm=replace(asm,'IF DEF(WIN_TESTS)\n    ld a, [WinTestCommand]\n','IF DEF(WIN_TESTS)\n    call CabinetCryTestCommand\n    ld a, [WinTestCommand]\n')
asm=replace(asm,'    call CabinetButtonEffect\n    ld a, b\n','    call CabinetButtonEffect\n    call CabinetCryPreviewInput\n    ld a, b\n')
asm+='\n'+(HERE/'src/cry_runtime.asm').read_text()
asm+='''
CabinetCryPreviewInput:
    push af
    push bc
    push de
    push hl
    ld a, [PressedA]
    bit 2, a
    jr z, .exit
    bit 0, a
    jr nz, .exit
    ld a, [SpinActive]
    and a
    jr nz, .exit
    ld a, [MenuMode]
    and a
    jr nz, .exit
    di
    ld a, [CabinetCryCount]
    and a
    jr nz, .enable
    ld a, [CabinetCryTail]
    ld e, a
    ld d, 0
    ld hl, CabinetCryQueue
    add hl, de
    ld a, [CabinetCryPreviewIndex]
    ld [hl], a
    inc a
    cp 6
    jr c, .nextReady
    xor a
.nextReady
    ld [CabinetCryPreviewIndex], a
    ld a, e
    inc a
    and 7
    ld [CabinetCryTail], a
    ld hl, CabinetCryCount
    inc [hl]
    ld hl, CabinetCryQueued
    inc [hl]
    jr nz, .enable
    inc hl
    inc [hl]
.enable
    ei
.exit
    pop hl
    pop de
    pop bc
    pop af
    ret
'''
asm+='\nCabinetCryPresets:\n'
for base,pitch,duration in assets['cry_presets']:
    asm+=f'    db {assets["sound_ids"][f"cry{base:02x}"]}, {pitch}, {duration}\n'
path.write_text(asm)
(OUT/'cry-candidate-layout.json').write_text(json.dumps({'default_mode':'Big Wins Only','qualification':'Gross payout >= 5 times spin cost or a paying five-of-a-kind','species_selection':manifest['species_selection'],'tie_break':manifest['tie_break'],'cry_queue_capacity':8,'cry_state_range':['0xc940','0xc960'],'decision_rom_banks':list(range(25,31)),'preview_control':'SELECT while idle cycles through six species; ignores menus, spins and already-pending cries','preview_species_order':assets['species'],'audio_settings_menu_implemented':False,'manual_listening_approved':False},indent=2))
(OUT/'README.txt').write_text('EXPERIMENTAL POKESLOT MUSIC, EFFECTS AND QUALIFYING WIN CRIES\nDefault Big Wins Only: gross payout >= 5x total spin cost OR a paying five-of-a-kind. One cry request per qualifying settled spin, selecting the highest total contributing species. Ties use machine symbol order.\nSELECT while idle previews the next species cry, cycling through all six and wrapping. It does not charge credits or change bets, paylines or win qualification. Holding SELECT does not repeat. Preview is disabled during spins and menus. One preview may wait behind an active cry; further presses while a cry is queued are ignored.\nCries wait for pending effects and active payout sound to finish. Effects wait while a cry is active. Original species pitch and duration presets are used.\nAudio settings, track selection and rotation are not implemented. Music/cry updates pause during LCD-off menu loading. No saving is added.\nA spin; Up/Down bet; Left/Right lines; B paytable; START win review; SELECT cry preview.\nKeep the approved music-and-effects ZIP. Automated checks do not replace Delta playtesting and listening.\n')
