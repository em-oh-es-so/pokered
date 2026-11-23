from pathlib import Path
from itertools import product
import json
import os
import sys
import wave
import numpy as np
from music_cabinet_guard import GuardedPyBoy
from cry_policy import MACHINE,assess_win

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/music-cabinet'
os.environ['MUSIC_SUITE']='cries'
p=GuardedPyBoy(str(OUT/'highlights-test.gbc'),window='null')
p.set_emulation_speed(0)
assets=json.loads((HERE/'build/audio/audio-assets.json').read_text())
cry_start=min(value for name,value in assets['sound_ids'].items() if name.startswith('cry'))
starts=[]
capture=None

def write(name,value,n=1):
    a=p.sym[name]
    data=value.to_bytes(n,'little') if isinstance(value,int) else bytes(value)
    p.memory[a:a+len(data)]=list(data)

def busy():
    a=p.sym['wChannelSoundIDs']
    return any(value>=cry_start for value in p.memory[a+4:a+8])

def start_hook(context):
    assert not p.read('CabinetEffectCount') and not busy(),'Cry cut off an effect'
    assert not p.read('CabinetCryActive')
    starts.append(p.read('CabinetCryPlayed',2))

def effect_hook(context):
    assert not p.read('CabinetCryActive'),'An effect interrupted a cry'

p.hook_register(0,p.sym['CabinetCryService.start'],start_hook,None)
p.hook_register(0,p.sym['CabinetEffectService.confirmed'],effect_hook,None)

def tick(n=1):
    for _ in range(n):
        assert p.tick(1,False,True)
        if p.read('CabinetAudioInitialized')==0xa5:
            for name in ('CabinetCryOverflow','CabinetCryPresenceFault','CabinetEffectOverflow','CabinetEffectPresenceFault'):
                assert p.read(name)==0,name
        if capture is not None:
            capture.append(p.sound.ndarray.copy())

def command(code):
    write('WinTestCommand',code)
    for _ in range(12):
        tick()
        if not p.read('WinTestCommand'):
            return
    raise AssertionError('Cry test command timed out')

def fixture(stops,index,mode):
    write('Stops',stops)
    write('Phases',[s*6 for s in stops])
    write('Bet',1)
    write('LineIndex',index)
    write('CabinetCryMode',mode)
    decision=assess_win(stops,1,MACHINE['line_counts'][index],mode)
    write('Payout',decision['gross_payout'],2)
    write('Cost',decision['cost'])
    return decision

def drain(limit=600):
    for _ in range(limit):
        tick()
        if not (p.read('CabinetEffectCount') or p.read('CabinetCryCount') or p.read('CabinetCryActive') or busy()):
            return
    raise AssertionError('Payout/cry/effect sequence did not finish')

lookup_cases=0
clips=[]
try:
    for _ in range(240):
        tick()
        if p.read('GameReady')==0xa5:
            break
    else:
        raise AssertionError('Cry candidate failed to boot')
    assert p.read('CabinetCryMode')==2
    rom=(OUT/'pokeslot-play.gbc').read_bytes()
    outcomes=list(product(range(6),repeat=5))
    for index,lines in enumerate(MACHINE['line_counts']):
        table=(HERE/f'build/cry-policy/cry-lines-{lines}.bin').read_bytes()
        assert rom[(25+index)*0x4000:(25+index)*0x4000+7776]==table
        for offset in list(range(0,7776,257))+[7775]:
            for mode in (0,1,2):
                decision=fixture(outcomes[offset],index,mode)
                command(2)
                best=decision['highest_contributing_species']
                assert p.read('CabinetCrySelected')==(7 if best is None else best)
                assert p.read('CabinetCryEligible')==decision['eligible']
                lookup_cases+=1
    table=(HERE/'build/cry-policy/cry-lines-25.bin').read_bytes()
    first_win=next(i for i,v in enumerate(table) if v&7<6)
    before=p.read('CabinetCryQueued',2)
    fixture(outcomes[first_win],5,0)
    command(3)
    drain()
    assert p.read('CabinetCryQueued',2)==before
    for species in range(6):
        offset=next(i for i,v in enumerate(table) if v&7==species)
        before=[p.read(name,2) for name in ('CabinetCryQueued','CabinetCryPlayed','CabinetCryCompleted')]
        fixture(outcomes[offset],5,1)
        capture=[]
        command(3)
        for _ in range(360):
            tick()
            if p.read('CabinetCryPlayed',2)==before[1]+1:
                break
        else:
            raise AssertionError('Queued cry did not start')
        assert p.read('CabinetCryLastSpecies')==species
        preset=assets['cry_presets'][species]
        assert p.read('CabinetCryLastPitch')==preset[1]
        assert p.read('CabinetCryLastDuration')==preset[2]
        p.button_press('up')
        tick()
        p.button_release('up')
        drain()
        tick(12)
        after=[p.read(name,2) for name in ('CabinetCryQueued','CabinetCryPlayed','CabinetCryCompleted')]
        assert after==[value+1 for value in before],(species,before,after)
        audio=np.concatenate(capture)
        capture=None
        assert audio.size and np.ptp(audio.astype(np.int16))>0
        with wave.open(str(OUT/f'cry-cabinet-{species}.wav'),'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(p.sound.sample_rate)
            wav.writeframes((audio.astype(np.int16)*256).astype('<i2').tobytes())
        clips.append({'species':MACHINE['symbols'][species],'pitch':preset[1],'duration_modifier':preset[2],'sample_frames':int(len(audio))})
    for eligible in (False,True):
        offset=next(i for i,v in enumerate(table) if v&7<6 and bool(v&8)==eligible)
        before=p.read('CabinetCryQueued',2)
        fixture(outcomes[offset],5,2)
        command(3)
        drain()
        assert p.read('CabinetCryQueued',2)-before==int(eligible)
finally:
    p.stop(save=False)
report_path=OUT/'music-cries-report.json'
report=json.loads(report_path.read_text())
report.update({'suite_passed':True,'runtime_lookup_cases_checked':lookup_cases,'all_46656_packed_bytes_present_in_candidate':True,'species_playback_cases':clips,'cry_start_hooks_checked':len(starts),'off_every_win_and_big_wins_modes_checked':True,'one_request_one_start_one_completion_per_playback_fixture':True,'payout_not_interrupted_by_cry':True,'effects_not_dispatched_during_active_cry':True,'original_pitch_and_duration_presets_checked':True,'fixtures_are_synthetic_settled_wins':True,'audio_settings_menu_implemented':False,'human_listening_approval':False})
report_path.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
