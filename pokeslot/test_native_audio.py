from pathlib import Path
import json
import wave
import numpy as np
from pyboy import PyBoy

OUT=Path(__file__).resolve().parent/'build/audio'
PREVIEWS=OUT/'previews'
PREVIEWS.mkdir(exist_ok=True)
symbols={}
for line in (OUT/'native-audio.sym').read_text().splitlines():
    parts=line.split()
    if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
        symbols[parts[1]]=int(parts[0].split(':')[1],16)
assets=json.loads((OUT/'audio-assets.json').read_text())
p=PyBoy(str(OUT/'native-audio.gbc'),window='null',sound_emulated=True,sound_sample_rate=24000)
p.set_emulation_speed(0)
results=[]
last_command=None
current_clip=None

def read(name,n=1):
    a=symbols[name]
    return int.from_bytes(bytes(p.memory[a:a+n]),'little')

def state():
    arrays={}
    for name in ('wChannelSoundIDs','wChannelFlags1','wChannelNoteSpeeds','wChannelNoteDelayCounters'):
        a=symbols[name]
        arrays[name]=list(p.memory[a:a+8])
    a=symbols['wChannelCommandPointers']
    arrays['channel_pointers']=[int.from_bytes(bytes(p.memory[a+i*2:a+i*2+2]),'little') for i in range(8)]
    registers={f'FF{address:02X}':p.memory[0xff00+address] for address in range(0x10,0x27)}
    return {'audio_ticks':read('AudioTicks',2),'current_song':read('CurrentSong'),'registers':registers,'software_channels':arrays,'valid_sample_frames':int(p.sound.ndarray.shape[0])}

def tick(n=1):
    assert p.tick(n,False,True)

def command(code,**values):
    global last_command
    for name,value in values.items():
        p.memory[symbols[name]]=value
    p.memory[symbols['Status']]=0
    p.memory[symbols['Command']]=code
    chunks=[]
    trace=[]
    last_command={'code':code,'values':values}
    for _ in range(12):
        tick()
        chunks.append(p.sound.ndarray.copy())
        trace.append(state())
        if read('Command')==0:
            assert read('Status')==1,(code,values,read('Status'))
            return chunks,trace
    raise AssertionError(('Audio command timed out',code,values))

def capture(name,frames,onset):
    global current_clip
    onset_chunks,onset_trace=onset
    chunks=list(onset_chunks)
    current_clip={'name':name,'command':last_command,'frames':list(onset_trace)}
    for _ in range(frames):
        tick()
        chunks.append(p.sound.ndarray.copy())
        current_clip['frames'].append(state())
    audio=np.concatenate(chunks)
    span=int(np.ptp(audio.astype(np.int16))) if audio.size else 0
    pcm=(audio.astype(np.int16)*256).astype('<i2')
    with wave.open(str(PREVIEWS/(name+'.wav')),'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(p.sound.sample_rate)
        output.writeframes(pcm.tobytes())
    current_clip['sample_frames']=int(len(audio))
    current_clip['peak_to_peak']=span
    assert audio.size and span>0,('Silent output including command frames',name)
    return {'name':name,'sample_frames':len(audio),'seconds':len(audio)/p.sound.sample_rate,'peak_to_peak':span,'command_frames_captured':len(onset_chunks)}

try:
    for _ in range(240):
        tick()
        if read('Ready')==0xa5:
            break
    else:
        raise AssertionError('Audio bench did not boot')
    for song,title in enumerate(assets['tracks']):
        onset=command(1,Song=song)
        assert read('CurrentSong')==song
        before=read('AudioTicks',2)
        results.append(capture('music-'+title.lower().replace(' ','-'),180,onset))
        elapsed=(read('AudioTicks',2)-before)&65535
        assert 175<=elapsed<=185,('Audio update cadence',title,elapsed)
    for name in ('button','spin','stop','reward','denied'):
        command(4)
        onset=command(2,Sound=assets['sound_ids'][name])
        results.append(capture('effect-'+name,90,onset))
    for species,name in enumerate(assets['species']):
        command(4)
        onset=command(3,Species=species)
        results.append(capture('cry-'+name,240,onset))
        a=symbols['wChannelSoundIDs']
        assert not any(p.memory[a+4:a+8]),('Cry did not finish',name)
    assert read('AudioBudgetExceeded')==0,('Native audio exceeded VBlank safety budget',read('AudioMaximumLY'))
    report={'non_silent_assets_checked':len(results),'clips':results,'command_frame_sampling_enabled':True,'update_cadence_checked':True,'vblank_budget_passed':True,'maximum_update_end_scanline':read('AudioMaximumLY'),'cabinet_integration_complete':False,'human_listening_approval':False}
    (OUT/'native-audio-report.json').write_text(json.dumps(report,indent=2))
    (PREVIEWS/'README.txt').write_text('NATIVE AUDIO PREVIEWS - NOT A PLAYABLE CABINET UPDATE\nThese WAV files were recorded from the standalone native-audio test ROM in PyBoy, including the frames that accept playback commands. Music clips are short excerpts, not complete tracks.\nSix soundtrack selections, five original interface/slot effects and six species cries are included. Cries retain the original pitch and duration modifiers.\nAutomated non-silence and update-budget tests do not replace listening checks or prove integration with reel DMA, menus, win thresholds or the playlist. Those cabinet features are not implemented by this commit.\n')
    print(json.dumps(report,indent=2))
except Exception as error:
    debug={'error_type':type(error).__name__,'error':str(error),'last_command':last_command,'completed_clips':results,'current_clip':current_clip,'final_state':state(),'tests_passed':False}
    (OUT/'audio-debug.json').write_text(json.dumps(debug,indent=2))
    summary={'error':str(error),'last_command':last_command,'first_frame_states':current_clip['frames'][:4] if current_clip else [],'final_state':debug['final_state']}
    print(json.dumps(summary,indent=2))
    raise
finally:
    p.stop(save=False)
