from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path('build')
OUT.mkdir(exist_ok=True)
MACHINES = [{'name': 'KANTO DEMO', 'species': ['bulbasaur', 'charmander', 'squirtle', 'pikachu', 'eevee', 'ditto']}]
machine = MACHINES[0]
chars = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-'
lookup = {c: i for i, c in enumerate(chars)}
tiles = bytearray()
def encode(im):
    im = im.convert('L')
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            p = (255 - im.getpixel((x, y))) * 3 // 255
            lo = (lo << 1) | (p & 1)
            hi = (hi << 1) | (p >> 1)
        tiles.extend([lo, hi])
for char in chars:
    im = Image.new('L', (8, 8), 255)
    ImageDraw.Draw(im).text((0, -2), char, font=ImageFont.load_default(), fill=0)
    encode(im)
base = len(chars)
for species in machine['species']:
    src = Image.open(Path('../gfx/pokemon/front') / (species + '.png')).convert('RGBA')
    bg = Image.new('RGBA', src.size, 'white')
    bg.alpha_composite(src)
    icon = bg.convert('L').resize((16, 16), Image.Resampling.NEAREST)
    for y in (0, 8):
        for x in (0, 8):
            encode(icon.crop((x, y, x + 8, y + 8)))
assert len(tiles) // 16 < 128
(OUT / 'tiles.bin').write_bytes(tiles)
canvas = bytearray(1024)
def text(x, y, value):
    for i, c in enumerate(value):
        canvas[y * 32 + x + i] = lookup[c]
text(6, 0, 'POKESLOT')
text(5, 2, machine['name'])
text(1, 4, 'COINS:200 BET:1')
text(1, 13, 'A:SPIN UP-DN:BET')
text(1, 15, 'SELECT:RESET')
text(1, 17, 'DEMO - NO PAYOUTS')
for col in range(5):
    for row in range(3):
        t = base + ((col + row) % 6) * 4
        pos = (6 + row * 2) * 32 + 3 + col * 3
        canvas[pos:pos + 2] = bytes([t, t + 1])
        canvas[pos + 32:pos + 34] = bytes([t + 2, t + 3])
(OUT / 'map.bin').write_bytes(canvas)
source = '''SECTION "Entry", ROM0[$100]
    nop
    jp Boot
    ds $150 - @, 0
SECTION "State", WRAM0
Coins: ds 1
Bet: ds 1
Keys: ds 1
OldKeys: ds 1
Pressed: ds 1
Timer: ds 1
Column: ds 1
Seed: ds 1
SECTION "Code", ROM0[$150]
Boot:
    di
    ld sp, $dfff
    xor a
    ldh [$ff], a
.wait
    ldh a, [$44]
    cp 144
    jr c, .wait
    xor a
    ldh [$40], a
    ldh [$42], a
    ldh [$43], a
    ldh [$26], a
    ld hl, Tiles
    ld de, $8000
    ld bc, TilesEnd-Tiles
    call Copy
    ld hl, Map
    ld de, $9800
    ld bc, 1024
    call Copy
    xor a
    ld [OldKeys], a
    ld [Timer], a
    ld [Column], a
    ld a, 73
    ld [Seed], a
    call Reset
    ld a, $e4
    ldh [$47], a
    ld a, $91
    ldh [$40], a
Main:
    call Frame
    call Input
    ld a, [Timer]
    and a
    jr z, Idle
    dec a
    ld [Timer], a
    and 3
    jp nz, Main
    ld a, [Column]
    inc a
    cp 5
    jr c, .store
    xor a
.store
    ld [Column], a
    ld e, a
    ld d, 0
    ld hl, Stops
    add hl, de
    ld a, [Timer]
    cp [hl]
    jp c, Main
    ld a, e
    add a
    ld e, a
    ld hl, DrawTable
    add hl, de
    ld a, [hli]
    ld h, [hl]
    ld l, a
    ld de, Main
    push de
    jp hl
Idle:
    ld a, [Pressed]
    bit 2, a
    jr z, .betUp
    call Reset
.betUp
    ld a, [Pressed]
    bit 6, a
    jr z, .betDown
    ld a, [Bet]
    cp 9
    jr nc, .betDown
    inc a
    ld [Bet], a
.betDown
    ld a, [Pressed]
    bit 7, a
    jr z, .spin
    ld a, [Bet]
    cp 1
    jr z, .spin
    dec a
    ld [Bet], a
.spin
    ld a, [Pressed]
    bit 0, a
    jr z, .display
    ld a, [Bet]
    ld b, a
    ld a, [Coins]
    cp b
    jr c, .display
    sub b
    ld [Coins], a
    ld a, 120
    ld [Timer], a
.display
    call Display
    jp Main
Reset:
    ld a, 200
    ld [Coins], a
    ld a, 1
    ld [Bet], a
    ret
Frame:
.out
    ldh a, [$44]
    cp 144
    jr nc, .out
.in
    ldh a, [$44]
    cp 144
    jr c, .in
    ret
Input:
    ld a, $20
    ldh [$00], a
    ldh a, [$00]
    ldh a, [$00]
    cpl
    and $0f
    ld b, a
    ld a, $10
    ldh [$00], a
    ldh a, [$00]
    ldh a, [$00]
    cpl
    and $0f
    swap a
    or b
    ld [Keys], a
    ld b, a
    ld a, [OldKeys]
    cpl
    and b
    ld [Pressed], a
    ld a, b
    ld [OldKeys], a
    ld a, $30
    ldh [$00], a
    ret
Copy:
    ld a, [hli]
    ld [de], a
    inc de
    dec bc
    ld a, b
    or c
    jr nz, Copy
    ret
Display:
    ld a, [Coins]
    ld b, DIGIT_ZERO
.hundreds
    cp 100
    jr c, .hDone
    sub 100
    inc b
    jr .hundreds
.hDone
    ld hl, $9887
    ld [hl], b
    inc hl
    ld b, DIGIT_ZERO
.tens
    cp 10
    jr c, .tDone
    sub 10
    inc b
    jr .tens
.tDone
    ld [hl], b
    inc hl
    add DIGIT_ZERO
    ld [hl], a
    ld a, [Bet]
    add DIGIT_ZERO
    ld [$988e], a
    ret
RandomSymbol:
    ld a, [Seed]
    ld b, a
    add a
    add a
    add b
    add 1
    ld [Seed], a
    ldh a, [$04]
    xor b
.mod
    cp 6
    jr c, .done
    sub 6
    jr .mod
.done
    add a
    add a
    add SYMBOL_BASE
    ret
Stops:
    db 64, 48, 32, 16, 0
DrawTable:
    dw Draw0, Draw1, Draw2, Draw3, Draw4
'''
source = 'DEF DIGIT_ZERO EQU ' + str(lookup['0']) + '\nDEF SYMBOL_BASE EQU ' + str(base) + '\n' + source
for col in range(5):
    source += f'\nDraw{col}:\n'
    for row in range(3):
        addr = 0x9800 + (6 + row * 2) * 32 + 3 + col * 3
        source += f'    call RandomSymbol\n    ld hl, ${addr:04x}\n    ld [hli], a\n    inc a\n    ld [hl], a\n    inc a\n    ld hl, ${addr + 32:04x}\n    ld [hli], a\n    inc a\n    ld [hl], a\n'
    source += '    ret\n'
source += '\nTiles:\n    INCBIN "build/tiles.bin"\nTilesEnd:\nMap:\n    INCBIN "build/map.bin"\n'
(OUT / 'generated.asm').write_text(source)
