from pathlib import Path
import json
import wave
import numpy as np
from pyboy import PyBoy

OUT=Path(__file__).resolve().parent/'build/audio'
PREVIEWS=OUT/'sram-previews'
PREVIEWS.mkdir(exist_ok=True)
symbols={}
for line in (OUT/'sram-audio.sym').read_text().splitlines():
    parts=line.split()
    if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
        symbols[parts[1]]=int(parts[0].split(':')[1],16)
assets=json.loads((OUT/'audio-assets.json').read_text())
rom=(OUT/'sram-audio.gbc').read_bytes()
start=symbols['AudioRAMProbeStart']
end=symbols['AudioRAMProbeEnd']
assert start==0xa000 and start<end<=0xc000
expected=rom[24*0x4000:24*0x4000+end-start]
p=PyBoy(str(OUT/'sram-audio.gbc'),window='null',sound_emulated=True,sound_sample_rate=24000)
p.set_emulation_speed(0)
results=[]
stress_ticks=0
last_command=None

def read(name,n=1):
    a=symbols[name]
    return int.from_bytes(bytes(p.memory[a:a+n]),'little')

def timing():
    return {name:read(name,n) for name,n in [('AudioFrameRequests',2),('AudioTicks',2),('AudioFrameOverrun',1),('AudioLateEntries',2),('AudioPending',1),('AudioBusy',1),('AudioMaximumSpan',1),('AudioBudgetExceeded',1)]}

def tick():
    global stress_ticks
    bank=None
    if read('Ready')==0xa5:
        bank=1+stress_ticks%6
        p.memory[0x2000]=bank
        assert bytes(p.memory[0x4000:0x4004])==bytes([bank,0x53,0x52,0x41])
    assert p.tick(1,False,True)
    if bank is not None:
        assert bytes(p.memory[0x4000:0x4004])==bytes([bank,0x53,0x52,0x41]),'Audio changed the ROM bank'
        stress_ticks+=1
    assert read('AudioFrameOverrun')==0,('Missed audio frame',timing())

def command(code,**values):
    global last_command
    last_command={'code':code,'values':values}
    for name,value in values.items():
        p.memory[symbols[name]]=value
    p.memory[symbols['Status']]=0
    p.memory[symbols['Command']]=code
    chunks=[]
    for _ in range(12):
        tick()
        chunks.append(p.sound.ndarray.copy())
        if read('Command')==0:
            assert read('Status')==1,last_command
            return chunks
    raise AssertionError(('Command timeout',last_command))

def capture(name,frames,chunks):
    before=read('AudioTicks',2)
    for _ in range(frames):
        tick()
        chunks.append(p.sound.ndarray.copy())
    elapsed=(read('AudioTicks',2)-before)&65535
    assert frames-1<=elapsed<=frames+1,(name,elapsed,frames)
    audio=np.concatenate(chunks)
    span=int(np.ptp(audio.astype(np.int16))) if audio.size else 0
    assert span>0,('Silent SRAM audio',name)
    with wave.open(str(PREVIEWS/(name+'.wav')),'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(p.sound.sample_rate)
        output.writeframes((audio.astype(np.int16)*256).astype('<i2').tobytes())
    results.append({'name':name,'sample_frames':int(len(audio)),'peak_to_peak':span,'requested_capture_frames':frames,'updates_during_capture':elapsed})

try:
    for _ in range(240):
        tick()
        if read('Ready')==0xa5:
            break
    else:
        raise AssertionError('SRAM test ROM failed to boot')
    assert bytes(p.memory[start:end])==expected,'SRAM copy differs from ROM image'
    capture('music-game-corner',180,command(1,Song=0))
    for name in ('button','spin','stop','reward','denied'):
        command(4)
        capture('effect-'+name,90,command(2,Sound=assets['sound_ids'][name]))
    for species,name in enumerate(assets['species']):
        command(4)
        capture('cry-'+name,240,command(3,Species=species))
        a=symbols['wChannelSoundIDs']
        assert not any(p.memory[a+4:a+8]),('Cry did not finish',name)
    assert len(results)==12
    assert bytes(p.memory[start:end])==expected,'SRAM module changed during playback'
    assert read('AudioLateEntries',2)==0,timing()
    assert ((read('AudioFrameRequests',2)-read('AudioTicks',2))&65535)<=1,timing()
    report={'checkpoint':'Isolated SRAM audio execution with host-driven ROM-bank switching','module_bytes':end-start,'copy_verified_before_and_after_playback':True,'runtime_audio_from_sram_tested':True,'non_silent_assets_checked':len(results),'clips':results,'rom_banks_exercised':[1,2,3,4,5,6],'rom_bank_stress_frames':stress_ticks,'audio_preserved_selected_rom_bank':True,'no_missed_frame_updates':True,'timing':timing(),'vblank_budget_passed':read('AudioBudgetExceeded')==0,'vblank_only_limit_is_diagnostic':True,'cabinet_memory_overlap_checked':False,'cabinet_graphics_dma_safety_verified':False,'cabinet_integration_complete':False,'human_listening_approval':False,'playable_cabinet_build':False}
    (OUT/'sram-audio-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
except Exception as error:
    debug={'error':str(error),'last_command':last_command,'completed_clips':results,'rom_bank_stress_frames':stress_ticks,'timing':timing(),'tests_passed':False}
    (OUT/'sram-audio-debug.json').write_text(json.dumps(debug,indent=2))
    raise
finally:
    p.stop(save=False)
