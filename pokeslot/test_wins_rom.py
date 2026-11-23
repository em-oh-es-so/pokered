from pathlib import Path
from itertools import product
import json
import sys
import numpy as np
from pyboy import PyBoy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'rules'))
from engine import MACHINE,evaluate_grid,grid_from_stops
OUT=HERE/'build/play'
symbols={}
for line in (OUT/'highlights-test.sym').read_text().splitlines():
    parts=line.split()
    if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
        symbols[parts[1]]=int(parts[0].split(':')[1],16)
p=PyBoy(str(OUT/'highlights-test.gbc'),window='null')
p.set_emulation_speed(0)
def tick(n=1):
    assert p.tick(n,False)
def read(name,n=1):
    a=symbols[name]
    return int.from_bytes(bytes(p.memory[a:a+n]),'little')
def write(name,data):
    a=symbols[name]
    p.memory[a:a+len(data)]=list(data)
def press(key):
    p.button_press(key);tick(6)
    p.button_release(key);tick(6)
def records():
    a=symbols['WinList']
    return [(p.memory[a+i*4],p.memory[a+i*4+1],int.from_bytes(bytes(p.memory[a+i*4+2:a+i*4+4]),'little')) for i in range(read('WinCount'))]
def collect(stops,bet=1,index=5):
    write('Stops',bytes(stops))
    write('Phases',bytes(stop*6 for stop in stops))
    write('Bet',bytes([bet]));write('LineIndex',bytes([index]))
    write('WinTestCommand',b'\x01')
    for _ in range(12):
        tick()
        if read('WinTestCommand')==0:
            break
    else:
        raise AssertionError('Win evaluation timed out')
    expected=[(w['line']-1,w['matched'],w['amount']) for w in evaluate_grid(grid_from_stops(stops),bet,MACHINE['line_counts'][index])]
    assert records()==expected,(stops,bet,index,records(),expected)
    return expected
try:
    for _ in range(240):
        tick()
        if read('GameReady')==0xa5:
            break
    else:
        raise AssertionError('ROM did not boot')
    for stops in product(range(6),repeat=5):
        collect(stops)
    settings_cases=0
    for bet in MACHINE['bets_per_line']:
        for index in range(6):
            for stops in ([0]*5,[5]*5,[0,0,0,1,2],[1,2,3,4,5]):
                collect(stops,bet,index)
                settings_cases+=1
    visual_cases=0
    for stops in ([0]*5,[0,0,0,1,2]):
        expected=collect(stops)
        assert expected
        tick(6)
        press('start')
        assert read('WinReview')==1
        assert p.tick(3,True)
        negative=p.screen.ndarray.copy()
        chosen=expected[read('WinCursor')]
        line,matched,amount=chosen
        assert read('WinAmount',2)==amount
        press('start')
        write('WinTimer',b'\x01')
        tick(6)
        assert read('WinPhase')==0
        assert p.tick(2,True)
        normal=p.screen.ndarray.copy()
        changed=np.any(negative[40:120,:,:3]!=normal[40:120,:,:3],axis=2)
        mask=np.zeros((80,160),dtype=bool)
        for reel,row in enumerate(MACHINE['paylines'][line][:matched]):
            x=8+30*reel;y=42+24*row-40
            mask[y:y+24,x:x+24]=True
        assert np.array_equal(changed,mask),'Inversion touched the wrong pixels'
        credit=read('Credits',4)
        payout=read('Payout',2)
        tick(240)
        assert read('Credits',4)==credit and read('Payout',2)==payout,'Win display changed settlement'
        press('start')
        assert read('WinReview')==1
        previous=read('WinCursor')
        press('right')
        assert read('WinCursor')==(previous+1)%read('WinCount')
        assert read('WinReview')==1
        assert read('Credits',4)==credit
        visual_cases+=1
    report={'all_7776_outcomes_checked':True,'additional_bet_and_line_cases':settings_cases,'negative_pixel_mask_cases':visual_cases,'steady_review_and_browsing_checked':True,'no_duplicate_crediting_checked':True,'audio_implemented':False,'manual_delta_highlight_approval':False}
    (OUT/'win-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
finally:
    p.stop(save=False)
