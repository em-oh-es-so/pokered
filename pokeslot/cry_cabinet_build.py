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
    ds 4
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
asm+='\n'+(HERE/'src/cry_runtime.asm').read_text()
asm+='\nCabinetCryPresets:\n'
for base,pitch,duration in assets['cry_presets']:
    asm+=f'    db {assets["sound_ids"][f"cry{base:02x}"]}, {pitch}, {duration}\n'
path.write_text(asm)
(OUT/'cry-candidate-layout.json').write_text(json.dumps({'default_mode':'Big Wins Only','qualification':'Gross payout >= 5 times spin cost or a paying five-of-a-kind','species_selection':manifest['species_selection'],'tie_break':manifest['tie_break'],'cry_queue_capacity':8,'cry_state_range':['0xc940','0xc960'],'decision_rom_banks':list(range(25,31)),'audio_settings_menu_implemented':False,'manual_listening_approved':False},indent=2))
(OUT/'README.txt').write_text('EXPERIMENTAL POKESLOT MUSIC, EFFECTS AND QUALIFYING WIN CRIES\nDefault Big Wins Only: gross payout >= 5x total spin cost OR a paying five-of-a-kind. One cry request per qualifying settled spin, selecting the highest total contributing species. Ties use machine symbol order.\nCries wait for pending effects and active payout sound to finish. Effects wait while a cry is active. Original species pitch and duration presets are used.\nAudio settings, track selection and rotation are not implemented. Music/cry updates pause during LCD-off menu loading. No saving is added.\nA spin; Up/Down bet; Left/Right lines; B paytable; START win review.\nKeep the approved music-and-effects ZIP. Automated checks do not replace Delta playtesting and listening.\n')
