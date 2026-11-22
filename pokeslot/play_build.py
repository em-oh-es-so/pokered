from pathlib import Path
import json
import runpy
import shutil
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
OUT = HERE / 'build/play'
OUT.mkdir(parents=True, exist_ok=True)
machine = json.loads((HERE / 'rules/machine.json').read_text())
assert machine['bets_per_line'] == list(range(1,10))
assert machine['line_counts'] == [1,5,10,15,20,25]
assert machine['reels'] == [list(range(6))] * 5
assert machine['starting_credits'] == 1000

def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

assets = (HERE / 'five_assets.py').read_text().replace('build/five', 'build/play')
assets = replace(assets, "strip = shared['strip']", """strip = shared['strip']
original_art = base.copy()
draw = ImageDraw.Draw(base)
draw.rectangle((0,0,159,21), fill=85)
draw.rectangle((0,135,159,143), fill=85)
label = shared['label']
label(base,8,0,'CREDIT')
label(base,96,0,'PAYOUT')
label(base,0,136,'B:')
label(base,40,136,'L:')
label(base,96,136,'C:')
assert ImageChops.difference(original_art.crop((0,22,160,135)),base.crop((0,22,160,135))).getbbox() is None
""")
assets = replace(assets, 'plan = [None] * 5', """digit_ids = []
for char in '0123456789 ':
    tile = Image.new('L',(8,8),85)
    label(tile,0,0,char)
    data = encode(tile)
    if data not in lookup:
        lookup[data] = len(static)
        static.append(data)
    digit_ids.append(lookup[data])
plan = [None] * 5""")
namespace = {'__file__': str(HERE / 'five_assets.py'), 'ImageDraw': ImageDraw}
exec(compile(assets, str(HERE / 'five_assets.py'), 'exec'), namespace)
digits = namespace['digit_ids']
inc_path = OUT / 'assets.inc'
inc = inc_path.read_text() + '\nDigitTiles: db ' + ','.join(map(str,digits)) + '\n'
coordinates = [(x,1) for x in range(10)] + [(x,1) for x in range(13,18)] + [(2,17),(7,17),(8,17),(14,17),(15,17),(16,17)]
assert len(coordinates) == 21
inc += 'PaintUI:\n    xor a\n    ldh [$4f], a\n    ld hl, UI\n'
for x,y in coordinates:
    inc += f'    ld a, [hli]\n    push hl\n    ld e, a\n    ld d, 0\n    ld hl, DigitTiles\n    add hl, de\n    ld a, [hl]\n    pop hl\n    ld [${0x9800+y*32+x:04x}], a\n'
inc += '    ret\n'
inc_path.write_text(inc)
runpy.run_path(str(HERE / 'accounting_tables.py'))
payout_inc = ''
for i in range(6):
    shutil.copyfile(HERE / f'build/accounting/payouts-{i}.bin', OUT / f'payouts-{i}.bin')
    payout_inc += f'SECTION "Game Payout {i}", ROMX[$4000], BANK[{12+i}]\n    INCBIN "build/play/payouts-{i}.bin"\n'
payout_inc += 'SECTION "Game Line Counts", ROM0\nLineCounts: db 1,5,10,15,20,25\n'
(OUT / 'payouts.inc').write_text(payout_inc)
chars = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-'
font_data = b''
for char in chars:
    tile = Image.new('L',(8,8),85)
    namespace['shared']['label'](tile,0,0,char)
    font_data += namespace['encode'](tile)
assert len(font_data) <= 1024
(OUT / 'menu-font.bin').write_bytes(font_data)
pages = []
page = {0:'KANTO PAYTABLE',2:'BET 1 - MULTIPLY BY',3:'YOUR BET PER LINE',5:f'{"SYMBOL":10}{"3":>3}{"4":>3}{"5":>4}',13:'LEFT TO RIGHT ONLY',14:'MATCH 3 OR MORE',16:'LEFT RIGHT - PAGE',17:'B - BACK'}
for row,(name,pays) in enumerate(zip(machine['symbols'],machine['paytable']),6):
    page[row] = f'{name.upper():10}{pays[0]:3}{pays[1]:3}{pays[2]:4}'
pages.append(page)
pages.append({0:'CONTROLS',2:'A - SPIN',4:'UP DOWN - BET',6:'LEFT RIGHT - LINES',8:'B - PAYTABLE',10:'B - BET PER LINE',11:'L - ACTIVE LINES',12:'C - TOTAL SPIN COST',14:'LINE WINS ARE SUMMED',16:'LEFT RIGHT - PAGE',17:'B - BACK'})
for first,last in [(0,13),(13,25)]:
    page = {0:'PAYLINE PATTERNS',1:'1 TOP 2 MID 3 LOW',16:'LEFT RIGHT - PAGE',17:'B - BACK'}
    for row,i in enumerate(range(first,last),2):
        page[row] = f'{i+1:02}  ' + ''.join(str(r+1) for r in machine['paylines'][i])
    pages.append(page)
maps = bytearray()
for page in pages:
    tilemap = bytearray(1024)
    for row,text in page.items():
        assert len(text) <= 20, text
        for col,char in enumerate(text):
            tilemap[row*32+col] = chars.index(char)
    maps.extend(tilemap)
(OUT / 'menu-maps.bin').write_bytes(maps)
menu_inc = 'SECTION "Menu Font", ROMX[$4000], BANK[18]\nMenuFont:\n    INCBIN "build/play/menu-font.bin"\nMenuFontEnd:\nSECTION "Menu Maps", ROMX[$4400], BANK[18]\n    INCBIN "build/play/menu-maps.bin"\n'
(OUT / 'menus.inc').write_text(menu_inc)
asm = (HERE / 'src/cabinet_five.asm').read_text()
state = '''Credits: ds 4
Stops: ds 5
Bet: ds 1
LineIndex: ds 1
ResultCredits: ds 4
Payout: ds 2
Cost: ds 1
Status: ds 1
SpinActive: ds 1
PreviousLength: ds 1
RNG: ds 4
RandomWork: ds 4
GameReady: ds 1
MenuMode: ds 1
MenuPage: ds 1
NumberWork: ds 4
NumberText: ds 10
UI: ds 21
'''
asm = replace(asm, 'StateEnd:\n', 'StateEnd:\nPlayStateStart:\n' + state + 'PlayStateEnd:\n')
asm = replace(asm, '    stop\n', '    stop\nRestoreCabinet:\n')
asm = replace(asm, '    ld a, $30\n    ldh [$00], a\n    ld a, 1\n', '    ld a, $30\n    ldh [$00], a\n    call InitPlay\n    ld a, 1\n')
asm = replace(asm, '    ld hl, InitialPhases\n', '    ld a, [GameReady]\n    and a\n    jr nz, .keepPhases\n    ld hl, InitialPhases\n')
asm = replace(asm, '    ld bc, 5\n    call Copy\n    xor a\n    ld [Index], a\n.initialReel', '    ld bc, 5\n    call Copy\n.keepPhases\n    xor a\n    ld [Index], a\n.initialReel')
start = asm.index('Main:\n')
end = asm.index('AnyMoving:\n')
asm = asm[:start] + '''    call PrepareUI
    call Frame
    call PaintUI
    ld a, $a5
    ld [GameReady], a
Main:
    call Input
    call AnyMoving
    jr nz, .animate
    ld a, [SpinActive]
    and a
    call nz, FinishSpin
    ldh a, [$04]
    ld hl, RNG
    xor [hl]
    ld [hl], a
    call RandomByte
    ld a, [PressedA]
    bit 1, a
    jp nz, OpenMenu
    call SettingsInput
    ld a, [PressedA]
    and 1
    call nz, BeginSpin
    call PrepareUI
    call Frame
    call PaintUI
    jp Main
.animate
    call Advance
    call TransferAll
    xor a
    ldh [$4f], a
    call Frame
    call SwapAll
    call PaintAll
    jp Main
''' + asm[end:]
start = asm.index('Input:\n')
end = asm.index('Frame:\n')
asm = asm[:start] + '''Input:
    ld a, $10
    ldh [$00], a
    ldh a, [$00]
    ldh a, [$00]
    ldh a, [$00]
    cpl
    and $0f
    ld b, a
    ld a, $20
    ldh [$00], a
    ldh a, [$00]
    ldh a, [$00]
    ldh a, [$00]
    cpl
    and $0f
    swap a
    or b
    ld b, a
    ld a, [OldA]
    cpl
    and b
    ld [PressedA], a
    ld a, b
    ld [OldA], a
    ld a, $30
    ldh [$00], a
    ret
''' + asm[end:]
kernel = (HERE / 'src/accounting_test.asm').read_text()
kernel = kernel[kernel.index('Evaluate:\n'):kernel.index('Copy:\n')]
kernel = replace(kernel, '    ld a, [LineIndex]\n    inc a\n    ld [$2000], a', '    ld a, [LineIndex]\n    add 12\n    ld [$2000], a')
formatter = 'FormatNumber:\n'
for position,power in enumerate(10**i for i in range(9,-1,-1)):
    formatter += f'    ld b, 0\n.digit{position}\n'
    for byte in range(3,-1,-1):
        formatter += f'    ld a, [NumberWork + {byte}]\n    cp {(power >> (byte*8)) & 255}\n    jp c, .done{position}\n    jp nz, .subtract{position}\n'
    formatter += f'.subtract{position}\n'
    for byte in range(4):
        op = 'sub' if byte == 0 else 'sbc'
        formatter += f'    ld a, [NumberWork + {byte}]\n    {op} {(power >> (byte*8)) & 255}\n    ld [NumberWork + {byte}], a\n'
    formatter += f'    inc b\n    jp .digit{position}\n.done{position}\n    ld a, b\n    ld [NumberText + {position}], a\n'
formatter += '''    ld hl, NumberText
    ld b, 9
.blank
    ld a, [hl]
    and a
    ret nz
    ld [hl], 10
    inc hl
    dec b
    jr nz, .blank
    ret
'''
asm = replace(asm, 'INCLUDE "build/five/assets.inc"', (HERE / 'src/play_runtime.asm').read_text() + '\n' + kernel + '\n' + formatter + '\nINCLUDE "build/play/assets.inc"\nINCLUDE "build/play/payouts.inc"\nINCLUDE "build/play/menus.inc"')
(OUT / 'main.asm').write_text(asm)
(OUT / 'ui-layout.json').write_text(json.dumps({'digit_tiles':digits,'coordinates':coordinates,'fields':[10,5,1,2,3],'header_footer_only_changed':True},indent=2))
(OUT / 'README.txt').write_text('POKESLOT PLAYABLE CHECKPOINT - GAME BOY COLOR\nA spin; Up/Down bet; Left/Right active lines; B paytable. Paytable Left/Right pages, B return.\nB is bet per line, L active lines, C total cost. Credits start at 1000. No saving or audio yet.\nWager deducted at spin start; payout added only after the last reel stops. Rejected transactions do not change credits.\nPseudorandom stops use xorshift32 and byte rejection sampling; this is not a cryptographic RNG or a proof of independent outcomes.\nCabinet art is retained outside the header and footer text bands. Existing diagnostic builds are untouched.\nBuild success alone does not verify runtime behavior. See integration-report.json and manually check scrolling in Delta.\n')
