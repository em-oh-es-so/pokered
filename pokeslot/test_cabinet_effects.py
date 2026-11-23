from pathlib import Path
import json
import os
import sys
from music_cabinet_guard import GuardedPyBoy

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/music-cabinet'
sys.path.insert(0,str(HERE/'rules'))
from engine import MACHINE,settle
os.environ['MUSIC_SUITE']='effects'
p=GuardedPyBoy(str(OUT/'pokeslot-play.gbc'),window='null')
p.set_emulation_speed(0)
names=['button','spin','stop','reward','denied']

def tick(n=1):
    for _ in range(n):
        assert p.tick(1,False,True)
        assert p.read('CabinetEffectOverflow')==0,'Effect queue overflow'
        assert p.read('CabinetEffectPresenceFault')==0,'Requested effect did not initialize an SFX channel'

def counts(label):
    a=p.sym[label]
    return [int.from_bytes(bytes(p.memory[a+i*2:a+i*2+2]),'little') for i in range(5)]

def press(key):
    p.button_press(key)
    tick(3)
    p.button_release(key)
    tick(6)

spins=0
paying_spins=0
try:
    for _ in range(240):
        tick()
        if p.read('GameReady')==0xa5:
            break
    else:
        raise AssertionError('Effects candidate did not boot')
    press('up')
    press('down')
    tick(12)
    assert counts('CabinetEffectPlayed')[0]>=2,'Button events missing'
    a=p.sym['Credits']
    p.memory[a:a+4]=list((100000).to_bytes(4,'little'))
    for trial in range(64):
        before=counts('CabinetEffectPlayed')
        credits=p.read('Credits',4)
        bet=p.read('Bet')
        lines=MACHINE['line_counts'][p.read('LineIndex')]
        p.button_press('a')
        for _ in range(20):
            tick()
            if p.read('SpinActive'):
                break
        else:
            raise AssertionError('Spin was not accepted')
        p.button_release('a')
        a=p.sym['Stops']
        stops=list(p.memory[a:a+5])
        expected=settle(credits,stops,bet,lines)
        for _ in range(180):
            tick()
            if not p.read('SpinActive'):
                break
        else:
            raise AssertionError('Spin exceeded 180 frames after acceptance')
        tick(18)
        assert p.read('Credits',4)==expected['after']
        assert p.read('Payout',2)==expected['payout']
        after=counts('CabinetEffectPlayed')
        assert after[1]-before[1]==1,('Spin effect count',before,after)
        assert after[2]-before[2]==5,('Individual stop effect count',before,after)
        assert after[3]-before[3]==int(expected['payout']>0),('Payout effect count',before,after)
        spins+=1
        paying_spins+=int(expected['payout']>0)
        if paying_spins:
            break
    assert paying_spins,'No paying spin encountered in bounded event test'
    a=p.sym['Credits']
    p.memory[a:a+4]=[0]*4
    before=counts('CabinetEffectPlayed')
    press('a')
    tick(12)
    assert not p.read('SpinActive') and p.read('Status')==3
    assert p.read('Credits',4)==0
    after=counts('CabinetEffectPlayed')
    assert after[4]-before[4]==1,'Denied effect missing'
    assert after[1]==before[1],'Rejected spin played accepted-spin sound'
    queued=counts('CabinetEffectQueued')
    assert queued==after,('Unserviced effect events',queued,after)
    assert all(value>0 for value in after)
finally:
    p.stop(save=False)
report_path=OUT/'music-effects-report.json'
report=json.loads(report_path.read_text())
report.update({'suite_passed':True,'effects_dispatched_to_sfx_channels':dict(zip(names,after)),'effect_events_queued':dict(zip(names,queued)),'spins_checked':spins,'paying_spins_checked':paying_spins,'five_individual_stops_per_spin_checked':True,'rejected_spin_did_not_start_spin_sound':True,'event_test_accounting_passed':True,'pokemon_cries_enabled':False,'human_effect_listening_approval':False})
report_path.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
