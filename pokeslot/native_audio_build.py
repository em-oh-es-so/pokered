from pathlib import Path
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/'build/audio'
OUT.mkdir(parents=True,exist_ok=True)
def read(path):
    return (ROOT/path).read_text()
def flatten(text):
    return re.sub(r'(?m)^\s*INCLUDE "([^"]+)"\s*$',lambda m:flatten(read(m[1])),text)
def channels(text):
    result=[(int(number)-1,label) for label,number in re.findall(r'(?m)^([A-Za-z_]\w*_Ch([1-8]))::?',text)]
    assert 1<=len(result)<=4,result
    return result
tracks=[('gamecorner','GAME CORNER'),('celadon','CELADON CITY'),('bikeriding','BICYCLE'),('vermilion','VERMILION CITY'),('ssanne','SS ANNE'),('surfing','SURFING')]
machine=json.loads((HERE/'rules/machine.json').read_text())
cry_rows={name.lower():(int(base,16),int(pitch,16),int(length,16)) for base,pitch,length,name in re.findall(r'mon_cry SFX_CRY_([0-9A-F]+), \$([0-9A-F]+), \$([0-9A-F]+)\s*; ([A-Za-z]+)',read('data/pokemon/cries.asm'))}
presets=[cry_rows[name] for name in machine['symbols']]
assets=[('noise'+str(i),f'audio/sfx/noise_instrument{i:02}_1.asm') for i in range(1,20)]
cry_start=1+len(assets)
for base in sorted({row[0] for row in presets}):
    assets.append((f'cry{base:02x}',f'audio/sfx/cry{base:02x}_1.asm'))
cry_end=1+len(assets)
assets.extend([('button','audio/sfx/press_ab_1.asm'),('spin','audio/sfx/slots_new_spin.asm'),('stop','audio/sfx/slots_stop_wheel.asm'),('reward','audio/sfx/slots_reward.asm'),('denied','audio/sfx/denied_1.asm')])
ids={name:index for index,(name,path) in enumerate(assets,1)}
song_id=len(assets)+1
bodies=[flatten(read(path)) for name,path in assets]
core=flatten(read('audio/engine_1.asm').split('Audio1_PlaySound::')[0])
ram=read('ram/wram.asm').split('SECTION "Sprite State Data"')[0]
ram=ram.replace('SECTION "Audio RAM", WRAM0','SECTION "Native Audio RAM", WRAM0\nNativeRAMStart:')+'\nNativeRAMEnd:\n'
reset_arrays=[name for name in re.findall(r'(?m)^(wChannel\w+)::\s*ds',ram) if name not in ('wChannelCommandPointers','wChannelReturnAddresses')]
reset_code=''
for name in reset_arrays:
    reset_code+=f'    ld hl, {name}\n    add hl, bc\n    ld [hl], 0\n'
for name in ('wChannelNoteDelayCounters','wChannelLoopCounters','wChannelNoteSpeeds'):
    reset_code+=f'    ld hl, {name}\n    add hl, bc\n    ld [hl], 1\n'
player='''Audio1_PlaySound::
    ld [NativeSoundId], a
    add a
    ld e, a
    ld d, 0
    ld hl, NativeHeaderPointers
    add hl, de
    ld a, [hli]
    ld h, [hl]
    ld l, a
    ld a, [hli]
    and a
    ret z
    ld [NativeChannelsLeft], a
.each
    ld a, [hli]
    ld c, a
    ld a, [hli]
    ld e, a
    ld a, [hli]
    ld d, a
    ld a, l
    ld [NativeHeaderPointer], a
    ld a, h
    ld [NativeHeaderPointer+1], a
    push de
    ld b, 0
'''+reset_code+'''    ld a, c
    cp 3
    jr c, .melody
    ld hl, wChannelFlags1
    add hl, bc
    ld [hl], 1 << BIT_NOISE_OR_SFX
.melody
    ld hl, wChannelSoundIDs
    add hl, bc
    ld a, [NativeSoundId]
    ld [hl], a
    pop de
    ld hl, wChannelCommandPointers
    ld a, c
    add a
    add l
    ld l, a
    jr nc, .pointer
    inc h
.pointer
    ld [hl], e
    inc hl
    ld [hl], d
    ld hl, NativeHeaderPointer
    ld a, [hli]
    ld h, [hl]
    ld l, a
    ld a, [NativeChannelsLeft]
    dec a
    ld [NativeChannelsLeft], a
    jp nz, .each
    ret
NativeStartMusic:
    call NativeReset
    ld a, NATIVE_SONG_ID
    jp Audio1_PlaySound
NativeReset:
    ld hl, NativeRAMStart
    ld bc, NativeRAMEnd-NativeRAMStart
.clear
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .clear
    ld a, 1
    ld [wMusicTempo], a
    ld [wSfxTempo], a
    ld a, $ff
    ld [wStereoPanning], a
    xor a
    ldh [$25], a
    ldh [$12], a
    ldh [$17], a
    ldh [$21], a
    ldh [$1a], a
    ld a, $80
    ldh [$1a], a
    ld a, $77
    ldh [$24], a
    ret
'''
tables=''
for name,values in [('HWChannelBaseAddresses',['HW_CH1_BASE','HW_CH2_BASE','HW_CH3_BASE','HW_CH4_BASE']),('HWChannelEnableMasks',['HW_CH1_ENABLE_MASK','HW_CH2_ENABLE_MASK','HW_CH3_ENABLE_MASK','HW_CH4_ENABLE_MASK']),('HWChannelDisableMasks',['HW_CH1_DISABLE_MASK','HW_CH2_DISABLE_MASK','HW_CH3_DISABLE_MASK','HW_CH4_DISABLE_MASK'])]:
    if not re.search(r'(?m)^Audio1_'+name+r':',core):
        tables+='Audio1_'+name+': db '+','.join(values*2)+'\n'
if not re.search(r'(?m)^Audio1_Pitches:',core):
    tables+='Audio1_Pitches:\n'+flatten(read('audio/notes.asm'))+'\n'
tables+='Audio1_WavePointers:\n'+flatten(read('audio/wave_samples.asm'))+'\n'
inc=''
for bank,(filename,title) in enumerate(tracks,24):
    song=flatten(read(f'audio/music/{filename}.asm'))
    groups=[[]]+[channels(body) for body in bodies]+[channels(song)]
    headers='NativeHeaderPointers: dw '+','.join('NativeHeader'+str(i) for i in range(len(groups)))+'\n'
    for index,group in enumerate(groups):
        headers+=f'NativeHeader{index}: db {len(group)}\n'
        for channel,label in group:
            headers+=f'    db {channel}\n    dw {label}\n'
    body=core+'\n'+player+'\n'+tables+'\n'+'\n'.join(bodies)+'\n'+song+'\n'+headers
    labels=set(re.findall(r'(?m)^([A-Za-z_]\w*)::?',body))
    body=re.sub(r'\b[A-Za-z_]\w*\b',lambda m:f'Bank{bank}_'+m[0] if m[0] in labels else m[0],body)
    entries=''.join(f'    jp Bank{bank}_{label}\n' for label in ('Audio1_UpdateMusic','Audio1_PlaySound','NativeStartMusic','NativeReset'))
    inc+=f'SECTION "Native Track {bank}", ROMX[$4000], BANK[{bank}]\n'+entries+body+'\n'
(OUT/'native.inc').write_text(inc+'\n'+ram)
prelude=''.join(f'INCLUDE "{path}"\n' for path in ['macros/asserts.asm','macros/const.asm','macros/data.asm','macros/scripts/audio.asm','constants/hardware.inc','constants/audio_constants.asm'])
prelude+=f'DEF CRY_SFX_START EQU {cry_start}\nDEF CRY_SFX_END EQU {cry_end}\nDEF NATIVE_SONG_ID EQU {song_id}\n'
bench='''SECTION "Audio VBlank", ROM0[$40]
    jp AudioIRQ
SECTION "Audio Entry", ROM0[$100]
    nop
    jp Boot
    ds $150-@, 0
SECTION "Audio Control", WRAM0
ControlStart:
Command: ds 1
Status: ds 1
Song: ds 1
Sound: ds 1
Species: ds 1
CurrentSong: ds 1
AudioTicks: ds 2
AudioBudgetExceeded: ds 1
AudioMaximumLY: ds 1
NativeSoundId: ds 1
NativeChannelsLeft: ds 1
NativeHeaderPointer: ds 2
ControlEnd:
SECTION "Audio Ready", WRAM0[$cfff]
Ready: ds 1
SECTION "Audio Bench", ROM0[$150]
Boot:
    di
    ld sp, $dfff
    xor a
    ldh [$ff], a
.wait
    ldh a, [$44]
    cp 144
    jr c, .wait
    xor a
    ldh [$40], a
    ld [Ready], a
    ld hl, ControlStart
    ld bc, ControlEnd-ControlStart
.clear
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .clear
    ld a, $30
    ldh [$00], a
    ld a, 1
    ldh [$4d], a
    stop
    ld a, $80
    ldh [$26], a
    ld a, 24
    ld [$2000], a
    xor a
    ld [$3000], a
    call $4009
    xor a
    ldh [$42], a
    ldh [$43], a
    ldh [$4f], a
    ld hl, $8000
    ld bc, $2000
.vram
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .vram
    xor a
    ldh [$0f], a
    ld a, $91
    ldh [$40], a
    ld a, 1
    ldh [$ff], a
    ld a, $a5
    ld [Ready], a
    ei
Main:
    ld a, [Command]
    and a
    jr z, Main
    di
    ld b, a
    xor a
    ld [Status], a
    ld a, b
    cp 1
    jr z, .song
    cp 2
    jr z, .sound
    cp 3
    jr z, .cry
    cp 4
    jr z, .stop
    jr .invalid
.song
    ld a, [Song]
    cp 6
    jr nc, .invalid
    ld [CurrentSong], a
    add 24
    ld [$2000], a
    call $4006
    jr .done
.sound
    ld a, [Sound]
    and a
    jr z, .invalid
    cp NATIVE_SONG_ID
    jr nc, .invalid
    call $4003
    jr .done
.cry
    ld a, [Species]
    cp 6
    jr nc, .invalid
    ld b, a
    add a
    add b
    ld e, a
    ld d, 0
    ld hl, CryPresets
    add hl, de
    ld a, [hli]
    ld b, a
    ld a, [hli]
    ld [wFrequencyModifier], a
    ld a, [hl]
    ld [wTempoModifier], a
    ldh a, [$24]
    ld [wSavedVolume], a
    ld a, $33
    ldh [$24], a
    ld a, b
    call $4003
    jr .done
.stop
    call $4009
.done
    ld a, 1
    jr .status
.invalid
    ld a, 2
.status
    ld [Status], a
    xor a
    ld [Command], a
    ei
    jp Main
AudioIRQ:
    push af
    push bc
    push de
    push hl
    call $4000
    ld hl, AudioTicks
    inc [hl]
    jr nz, .ly
    inc hl
    inc [hl]
.ly
    ldh a, [$44]
    ld b, a
    ld a, [AudioMaximumLY]
    cp b
    jr nc, .budget
    ld a, b
    ld [AudioMaximumLY], a
.budget
    ld a, b
    cp 144
    jr c, .late
    cp 152
    jr c, .exit
.late
    ld a, 1
    ld [AudioBudgetExceeded], a
.exit
    pop hl
    pop de
    pop bc
    pop af
    reti
CryPresets:
'''
for base,pitch,length in presets:
    bench+=f'    db {ids[f"cry{base:02x}"]}, {pitch}, {length}\n'
(OUT/'bench.asm').write_text(prelude+bench+'\nINCLUDE "build/audio/native.inc"\n')
(OUT/'audio-assets.json').write_text(json.dumps({'tracks':[title for path,title in tracks],'sound_ids':ids,'species':machine['symbols'],'cry_presets':presets,'method':'Original native command interpreter with standalone channel initialization','cabinet_integration_complete':False},indent=2))
