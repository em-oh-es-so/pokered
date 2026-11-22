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
menu_checks = 0
def read(name,n=1):
    a=symbols[name]
    return int.from_bytes(bytes(p.memory[a:a+n]),'little')
def tick(n=1):
    assert p.tick(n,False)
def press(button):
    p.button_press(button)
    tick(3)
    p.button_release(button)
    tick(3)
def wait(predicate,limit):
    for _ in range(limit):
        tick()
        if predicate():
            return
    raise AssertionError('Timed out')
def ui():
    tick(3)
    config=json.loads((OUT/'ui-layout.json').read_text())
    tiles=config['digit_tiles']
    actual=''
    for x,y in config['coordinates']:
        tile=p.memory[0x9800+y*32+x]
        assert tile in tiles,(x,y,tile)
        actual += '0123456789 '[tiles.index(tile)]
    bet=read('Bet'); lines=MACHINE['line_counts'][read('LineIndex')]
    expected=f'{read("Credits",4):>10}{read("Payout",2):>5}{bet}{lines:>2}{bet*lines:>3}'
    assert actual==expected,(actual,expected)
def snapshot():
    assert p.tick(3,True)
    return p.screen.ndarray.tobytes()
def menu_roundtrip():
    global menu_checks
    ui()
    before=(read('Credits',4),read('Payout',2),read('Bet'),read('LineIndex'))
    a=symbols['Phases']
    phases=bytes(p.memory[a:a+5])
    image=snapshot()
    press('b')
    assert read('MenuMode')==1
    for page in (1,2,3,0):
        press('right')
        assert read('MenuPage')==page
    press('left')
    assert read('MenuPage')==3
    press('b')
    tick(12)
    assert read('MenuMode')==0
    assert before==(read('Credits',4),read('Payout',2),read('Bet'),read('LineIndex'))
    assert phases==bytes(p.memory[a:a+5]), 'Paytable changed reel positions'
    ui()
    assert image==snapshot(), 'Cabinet pixels changed after paytable return'
    menu_checks += 1
try:
    wait(lambda:read('GameReady')==0xa5,240)
    assert read('Credits',4)==1000
    ui()
    for key,bet,index in [('up',2,5),('down',1,5),('left',1,4),('right',1,5)]:
        press(key)
        assert (read('Bet'),read('LineIndex'))==(bet,index)
        ui()
    for _ in range(3):
        menu_roundtrip()
    outcomes=set()
    for spin in range(12):
        credits=read('Credits',4); bet=read('Bet'); index=read('LineIndex')
        press('a')
        assert read('SpinActive')==1
        address=symbols['Stops']
        stops=tuple(p.memory[address:address+5])
        expected=settle(credits,stops,bet,MACHINE['line_counts'][index])
        assert read('Credits',4)==credits-expected['cost']
        assert read('Payout',2)==0
        press('up')
        assert read('Bet')==bet
        wait(lambda:read('SpinActive')==0,900)
        assert read('Credits',4)==expected['after']
        assert read('Payout',2)==expected['payout']
        a=symbols['Phases']
        assert list(p.memory[a:a+5])==[s*6 for s in stops]
        outcomes.add(stops)
        ui()
        if spin in (0,5,11):
            menu_roundtrip()
    assert len(outcomes)>1
    a=symbols['Credits']
    p.memory[a:a+4]=[0,0,0,0]
    press('a')
    assert read('SpinActive')==0 and read('Status')==3
    assert read('Credits',4)==0
    ui()
    report={'integrated_spins_checked':12,'stop_alignment_passed':True,'credit_and_payout_parity_passed':True,'displayed_numbers_checked':True,'controls_and_menu_return_passed':True,'full_screen_menu_roundtrips_checked':menu_checks,'insufficient_credit_rejection_passed':True,'rng_independence_proven':False,'manual_delta_playtest_complete':False,'audio_implemented':False}
    (OUT/'integration-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
finally:
    p.stop(save=False)
