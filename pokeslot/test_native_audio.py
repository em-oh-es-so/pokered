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
def read(name,n=1):
    a=symbols[name]
    return int.from_bytes(bytes(p.memory[a:a+n]),'little')
def tick(n=1):
    assert p.tick(n,False,False)
def command(code,**values):
    for name,value in values.items():
        p.memory[symbols[name]]=value
    p.memory[symbols['Status']]=0
    p.memory[symbols['Command']]=code
    for _ in range(12):
        tick()
        if read('Command')==0:
            assert read('Status')==1,(code,values,read('Status'))
            return
    raise AssertionError(('Audio command timed out',code,values))
def capture(name,frames):
    chunks=[]
    for _ in range(frames):
        assert p.tick(1,False,True)
        chunks.append(p.sound.ndarray.copy())
    audio=np.concatenate(chunks)
    assert audio.size and np.ptp(audio.astype(np.int16))>0,('Silent output',name)
    pcm=(audio.astype(np.int16)*256).astype('<i2')
    with wave.open(str(PREVIEWS/(name+'.wav')),'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(p.sound.sample_rate)
        output.writeframes(pcm.tobytes())
    return {'name':name,'sample_frames':len(audio),'seconds':len(audio)/p.sound.sample_rate,'peak_to_peak':int(np.ptp(audio.astype(np.int16)))}
results=[]
try:
    for _ in range(240):
        tick()
        if read('Ready')==0xa5:
            break
    else:
        raise AssertionError('Audio bench did not boot')
    for song,title in enumerate(assets['tracks']):
        command(1,Song=song)
        assert read('CurrentSong')==song
        before=read('AudioTicks',2)
        results.append(capture('music-'+title.lower().replace(' ','-'),180))
        elapsed=(read('AudioTicks',2)-before)&65535
        assert 175<=elapsed<=185,('Audio update cadence',title,elapsed)
    for name in ('button','spin','stop','reward','denied'):
        command(4)
        command(2,Sound=assets['sound_ids'][name])
        results.append(capture('effect-'+name,90))
    for species,name in enumerate(assets['species']):
        command(4)
        command(3,Species=species)
        results.append(capture('cry-'+name,240))
        a=symbols['wChannelSoundIDs']
        assert not any(p.memory[a+4:a+8]),('Cry did not finish',name)
    assert read('AudioBudgetExceeded')==0,('Native audio exceeded VBlank safety budget',read('AudioMaximumLY'))
    report={'non_silent_assets_checked':len(results),'clips':results,'update_cadence_checked':True,'vblank_budget_passed':True,'maximum_update_end_scanline':read('AudioMaximumLY'),'cabinet_integration_complete':False,'human_listening_approval':False}
    (OUT/'native-audio-report.json').write_text(json.dumps(report,indent=2))
    (PREVIEWS/'README.txt').write_text('NATIVE AUDIO PREVIEWS - NOT A PLAYABLE CABINET UPDATE\nThese WAV files were recorded from the standalone native-audio test ROM in PyBoy. Music clips are short excerpts, not complete tracks.\nSix soundtrack selections, five original interface/slot effects and six species cries are included. Cries retain the original pitch and duration modifiers.\nAutomated non-silence and update-budget tests do not replace listening checks or prove integration with reel DMA, menus, win thresholds or the playlist. Those cabinet features are not implemented by this commit.\n')
    print(json.dumps(report,indent=2))
finally:
    p.stop(save=False)
