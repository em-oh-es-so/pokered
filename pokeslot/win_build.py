from pathlib import Path
import json
import runpy

HERE = Path(__file__).resolve().parent
OUT = HERE/'build/play'
def replace(text,old,new):
    assert text.count(old)==1, old
    return text.replace(old,new)
source=(HERE/'play_build.py').read_text()
reserve='''win_glyphs = {}
for char in ' LINEVW0123456789':
    tile = Image.new('L',(8,8),85)
    label(tile,0,0,char)
    data = encode(tile)
    if data not in lookup:
        lookup[data] = len(static)
        static.append(data)
    win_glyphs[char] = lookup[data]
'''
source=replace(source,'plan = [None] * 5""")',reserve+'plan = [None] * 5""")')
scope={'__file__':str(HERE/'play_build.py')}
exec(compile(source,str(HERE/'play_build.py'),'exec'),scope)
runpy.run_path(str(HERE/'speed_build.py'))
glyphs=scope['namespace']['win_glyphs']
machine=scope['machine']
assert machine['reels']==[list(range(6))]*5
counts=[30,40,40,40,30]
negative_inc=''
for reel,count in enumerate(counts):
    x=8+30*reel
    cells=[(col,row) for row in range(5,15) for col in range(x//8,(x+23)//8+1)]
    normal=(OUT/f'reel-{reel}-0.bin').read_bytes()+(OUT/f'reel-{reel}-1.bin').read_bytes()
    frame_size=count*16
    result=bytearray()
    for stop in range(6):
        original=normal[stop*6*frame_size:(stop*6+1)*frame_size]
        assert len(original)==frame_size
        for selected_row in range(3):
            data=bytearray(original)
            top=42+selected_row*24
            for index,(col,row) in enumerate(cells):
                mask=sum(1<<(7-pixel) for pixel in range(8) if x<=col*8+pixel<x+24)
                for y in range(8):
                    if top<=row*8+y<top+24:
                        data[index*16+y*2]^=mask
                        data[index*16+y*2+1]^=mask
            result.extend(data)
    assert len(result)==18*frame_size<=16384
    (OUT/f'negative-{reel}.bin').write_bytes(result)
    negative_inc+=f'SECTION "Negative Reel {reel}", ROMX[$4000], BANK[{19+reel}]\n    INCBIN "build/play/negative-{reel}.bin"\n'
(OUT/'negative.inc').write_text(negative_inc)
assets_path=OUT/'assets.inc'
assets=assets_path.read_text()
assets=replace(assets,'PaintUI:\n','PaintUI:\n    call PaintFooterBase\n')
assert assets.endswith('    ret\n')
assets=assets[:-len('    ret\n')]+'    jp PaintWinFooter\n'
assets+='WinFooterTemplate: db '+','.join(str(glyphs[c]) for c in 'LINE 00 WIN 00000   ')+'\n'
assets+='WinViewWord: db '+','.join(str(glyphs[c]) for c in 'VIEW')+'\n'
assets+='WinPaylines: db '+','.join(str(row) for line in machine['paylines'] for row in line)+'\n'
assets+='WinPaytable: dw '+','.join(str(amount) for row in machine['paytable'] for amount in row)+'\n'
assets_path.write_text(assets)
asm_path=OUT/'main.asm'
asm=asm_path.read_text()
state='''WinCount: ds 1
WinCursor: ds 1
WinPhase: ds 1
WinDirty: ds 1
WinTimer: ds 1
WinReview: ds 1
WinLine: ds 1
WinMatched: ds 1
WinAmount: ds 2
WinRows: ds 5
WinFooter: ds 20
WinList: ds 100
WinBet: ds 1
WinActive: ds 1
WinSymbol: ds 1
WinMatchWork: ds 1
WinColumn: ds 1
WinFrameNumber: ds 1
WinTestCommand: ds 1
'''
asm=replace(asm,'PlayStateEnd:\n',state+'PlayStateEnd:\n')
asm=replace(asm,'    ld [SpinActive], a\n    ret\nRandomStop:','    ld [SpinActive], a\n    call WinCollect\n    ret\nRandomStop:')
asm=replace(asm,'    cp 1\n    ret nz\n    ld a, [Cost]','    cp 1\n    ret nz\n    call WinReset\n    ld a, [Cost]')
asm=replace(asm,'    call nz, FinishSpin\n','    call nz, FinishSpin\n    call WinTick\n')
asm=replace(asm,'    call nz, BeginSpin\n    call PrepareUI\n    call Frame','    call nz, BeginSpin\n    call PrepareUI\n    ld a, [WinDirty]\n    and a\n    call nz, WinRender\n    call Frame')
asm=replace(asm,'SettingsInput:\n','NormalSettingsInput:\n')
asm=replace(asm,'OpenMenu:\n','NormalOpenMenu:\n')
asm=replace(asm,'GetSource:\n','NormalGetSource:\n')
asm=replace(asm,'INCLUDE "build/play/assets.inc"',(HERE/'src/win_runtime.asm').read_text()+'\nINCLUDE "build/play/assets.inc"')
asm+='\nINCLUDE "build/play/negative.inc"\n'
asm_path.write_text(asm)
(OUT/'win-layout.json').write_text(json.dumps({'glyphs':glyphs,'negative_frame_cases':90,'normal_negative_symbol_rectangles':[24,24],'negative_rom_banks':[19,20,21,22,23],'pulse_idle_ticks_per_state':30},indent=2))
test=(HERE/'test_play_rom.py').read_text()
test=replace(test,'HERE = Path(__file__).resolve().parent','HERE = Path(__file__).resolve().parents[2]')
start=test.index('def ui():\n')
end=test.index('def snapshot():\n')
test=test[:start]+'''def ui():
    tick(6)
    config=json.loads((OUT/'ui-layout.json').read_text())
    tiles=config['digit_tiles']
    count=15 if read('WinCount') else 21
    actual=''
    for x,y in config['coordinates'][:count]:
        tile=p.memory[0x9800+y*32+x]
        assert tile in tiles,(x,y,tile)
        actual+='0123456789 '[tiles.index(tile)]
    bet=read('Bet'); lines=MACHINE['line_counts'][read('LineIndex')]
    expected=f'{read("Credits",4):>10}{read("Payout",2):>5}{bet}{lines:>2}{bet*lines:>3}'
    assert actual==expected[:count],(actual,expected)
    if read('WinCount'):
        glyphs=json.loads((OUT/'win-layout.json').read_text())['glyphs']
        reverse={value:key for key,value in glyphs.items()}
        footer=''.join(reverse[p.memory[0x9800+17*32+x]] for x in range(20))
        a=symbols['WinList']+read('WinCursor')*4
        line=p.memory[a]+1
        amount=int.from_bytes(bytes(p.memory[a+2:a+4]),'little')
        prefix='VIEW' if read('WinReview') else 'LINE'
        assert footer==f'{prefix} {line:02} WIN {amount:>5}   ',footer
''' +test[end:]
test=replace(test,"    global menu_checks\n    ui()", "    global menu_checks\n    held = bool(read('WinCount') and not read('WinReview'))\n    if held:\n        press('start')\n    ui()")
test=replace(test,"    menu_checks += 1", "    menu_checks += 1\n    if held:\n        press('start')")
(OUT/'test_play_with_wins.py').write_text(test)
readme=OUT/'README.txt'
readme.write_text(readme.read_text()+'\nWIN DISPLAY: One paying line at a time pulses between normal and negative symbols. Only its actual 3, 4 or 5 matching Pokemon are highlighted. The footer shows LINE number and that line payout; PAYOUT remains the total.\nSTART toggles steady review (VIEW). In VIEW, Left/Right browse winning lines instead of changing the wager. START returns to automatic pulsing. A starts another spin immediately; no highlight delay must finish.\nPaytable visits preserve the result. Highlighting never changes credits. No saving or audio is added by this patch.\n')
