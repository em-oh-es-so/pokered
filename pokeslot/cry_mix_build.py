from pathlib import Path
import json

OUT=Path(__file__).resolve().parent/'build/music-cabinet'
def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

path=OUT/'main.asm'
asm=path.read_text()
asm=replace(asm,'    ld a, $33\n    ldh [$FF24], a\n','    ld a, $44\n    ldh [$FF24], a\n')
asm=replace(asm,'    call $a000\n    ldh a, [$FF44]\n','    call $a000\n    call CabinetCryMix\n    ldh a, [$FF44]\n')
asm=replace(asm,'    ld a, [CabinetCrySavedVolume]\n    ldh [$FF24], a\n','    ld a, [CabinetCrySavedVolume]\n    ldh [$FF24], a\n    call CabinetCryRestoreWave\n')
asm+='''
SECTION "Cabinet cry mix adjustment", ROM0
CabinetCryMix:
    ld a, [CabinetCryActive]
    and a
    ret z
    ld a, $44
    ldh [$FF24], a
    ld a, [wChannelSoundIDs+6]
    and a
    ret nz
    ld a, [wChannelVolumes+2]
    and $60
    cp $20
    jr z, .duck
    cp $40
    jr nz, .write
.duck
    add $20
.write
    ldh [$FF1C], a
.end
    ret
CabinetCryRestoreWave:
    ld a, [wChannelSoundIDs+6]
    and a
    ret nz
    ld a, [wChannelVolumes+2]
    and $60
    ldh [$FF1C], a
.done
    ret
'''
path.write_text(asm)
layout={'cry_time_master_volume':'0x44 instead of 0x33','music_wave_duck_codes':{'0x00':'0x00','0x20':'0x40','0x40':'0x60','0x60':'0x60'},'duck_derived_from_native_software_volume_each_frame':True,'sfx_wave_channel_not_ducked':True,'pre_cry_master_volume_restored':True,'current_music_wave_volume_restored':True,'cry_pitch_duration_and_envelopes_modified':False,'normal_music_and_effect_levels_modified':False,'perceived_balance_approved':False}
(OUT/'cry-mix-layout.json').write_text(json.dumps(layout,indent=2))
readme=OUT/'README.txt'
readme.write_text(readme.read_text()+'\nCRY MIX REVISION: Cry-time master output is raised one step, while the remaining music wave voice is reduced one level when possible. Muted and already-quarter-level wave settings are retained. Normal output and music-wave levels return afterward. Cry pitch, duration presets and envelopes are unchanged. Use SELECT to compare the balance.\n')
