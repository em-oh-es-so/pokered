from pathlib import Path
import json
import sys
from pyboy import PyBoy

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'rules'))
from engine import MACHINE, settle
OUT = HERE/'build/play'
symbols = {}
for line in (OUT/'play.sym').read_text().splitlines():
    parts = line.split()
    if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
        symbols[parts[1]] = int(parts[0].split(':')[1],16)
p = PyBoy(str(OUT/'pokeslot-play.gbc'),window='null')
p.set_emulation_speed(0)

def read(name,n=1):
    address=symbols[name]
    return int.from_bytes(bytes(p.memory[address:address+n]),'little')

def array(name,n):
    address=symbols[name]
    return list(p.memory[address:address+n])

def tick(n=1):
    assert p.tick(n,False), 'Emulator stopped'

frames = []
stop_frames = []
try:
    for _ in range(240):
        tick()
        if read('GameReady')==0xa5:
            break
    else:
        raise AssertionError('ROM did not boot')
    tick(4)
    for trial in range(16):
        credits=read('Credits',4)
        bet=read('Bet')
        lines=MACHINE['line_counts'][read('LineIndex')]
        p.button_press('a')
        for start_delay in range(1,21):
            tick()
            if read('SpinActive'):
                break
        else:
            raise AssertionError(('Spin did not start',trial))
        p.button_release('a')
        stops=array('Stops',5)
        expected=settle(credits,stops,bet,lines)
        assert read('Credits',4)==credits-expected['cost']
        stopped=[None]*5
        for elapsed in range(1,181):
            tick()
            for reel,remaining in enumerate(array('Remaining',5)):
                if remaining==0 and stopped[reel] is None:
                    stopped[reel]=elapsed
            if read('SpinActive')==0:
                break
        else:
            raise AssertionError(('Spin exceeded 180 emulated frames after acceptance',trial))
        assert all(value is not None for value in stopped), stopped
        assert all(a < b for a,b in zip(stopped,stopped[1:])), stopped
        assert array('Phases',5)==[stop*6 for stop in stops]
        assert read('Credits',4)==expected['after']
        assert read('Payout',2)==expected['payout']
        frames.append(start_delay+elapsed)
        stop_frames.append(stopped)
        tick(4)
    assert max(frames)<=180, frames
    report={'spins_measured':len(frames),'frames_from_button_press':frames,'first_to_last_stop_frames':stop_frames,'minimum_frames':min(frames),'mean_frames':sum(frames)/len(frames),'maximum_frames':max(frames),'approximate_minimum_seconds_at_60fps':min(frames)/60,'approximate_mean_seconds_at_60fps':sum(frames)/len(frames)/60,'approximate_maximum_seconds_at_60fps':max(frames)/60,'all_spins_within_180_frames':True,'alignment_and_accounting_passed':True,'manual_delta_speed_approval':False,'audio_implemented':False}
    (OUT/'speed-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
finally:
    p.stop(save=False)
