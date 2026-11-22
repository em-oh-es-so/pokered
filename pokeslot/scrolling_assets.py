from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

OUT = Path('build')
OUT.mkdir(exist_ok=True)
MACHINE = {'name': 'KANTO DEMO', 'species': ['bulbasaur', 'charmander', 'squirtle', 'pikachu', 'eevee', 'ditto']}
chars = ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-'
lookup = {c: i for i, c in enumerate(chars)}
tiles = bytearray()
def encode(image):
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            value = (255 - image.getpixel((x, y))) * 3 // 255
            lo = (lo << 1) | (value & 1)
            hi = (hi << 1) | (value >> 1)
        tiles.extend((lo, hi))
font = ImageFont.load_default()
for char in chars:
    image = Image.new('L', (8, 8), 255)
    if char != ' ':
        box = font.getbbox(char)
        glyph = Image.new('L', (max(1, box[2] - box[0]), max(1, box[3] - box[1])), 255)
        ImageDraw.Draw(glyph).text((-box[0], -box[1]), char, font=font, fill=0)
        glyph.thumbnail((7, 7), Image.Resampling.NEAREST)
        image.paste(glyph, (0, 7 - glyph.height))
    encode(image)
border = len(tiles) // 16
encode(Image.new('L', (8, 8), 0))
base = len(tiles) // 16
strip = Image.new('L', (24, 144), 255)
for index, species in enumerate(MACHINE['species']):
    source = Image.open(Path('../gfx/pokemon/front') / (species + '.png')).convert('RGBA')
    background = Image.new('RGBA', source.size, 'white')
    background.alpha_composite(source)
    source = background.convert('L')
    bounds = ImageChops.difference(source, Image.new('L', source.size, 255)).getbbox()
    if bounds is None:
        raise ValueError('Empty sprite: ' + species)
    source = source.crop(bounds)
    source.thumbnail((24, 24), Image.Resampling.NEAREST)
    strip.paste(source, ((24 - source.width) // 2, index * 24 + (24 - source.height) // 2))
for shift in (0, 4):
    for tile_row in range(18):
        for tile_col in range(3):
            image = Image.new('L', (8, 8), 255)
            for y in range(8):
                for x in range(8):
                    image.putpixel((x, y), strip.getpixel((tile_col * 8 + x, (tile_row * 8 + shift + y) % 144)))
            encode(image)
assert len(tiles) // 16 <= 256
(OUT / 'scroll-tiles.bin').write_bytes(tiles)
frames = bytearray()
for phase in range(36):
    for row in range(9):
        for col in range(3):
            frames.append(base + (phase % 2) * 54 + ((phase // 2 + row) % 18) * 3 + col)
assert len(frames) == 36 * 27
(OUT / 'scroll-frames.bin').write_bytes(frames)
def text(canvas, x, y, value):
    assert 0 <= x and x + len(value) <= 20 and 0 <= y < 18
    for index, char in enumerate(value):
        canvas[y * 32 + x + index] = lookup[char]
title = bytearray(1024)
text(title, 6, 5, 'POKESLOT')
text(title, 4, 9, 'PRESS START')
text(title, 3, 13, 'REEL TEST V2')
(OUT / 'title-map.bin').write_bytes(title)
canvas = bytearray(1024)
text(canvas, 6, 0, 'POKESLOT')
text(canvas, 5, 1, MACHINE['name'])
text(canvas, 1, 3, 'COINS:200 BET:1')
text(canvas, 0, 15, 'A:SPIN UP-DN:BET')
text(canvas, 0, 16, 'SELECT:RESET')
text(canvas, 0, 17, 'DEMO - NO PAYOUTS')
for x in range(20):
    canvas[4 * 32 + x] = border
    canvas[14 * 32 + x] = border
for y in range(5, 14):
    for x in (3, 7, 11, 15, 19):
        canvas[y * 32 + x] = border
for col in range(5):
    phase = col * 6
    for row in range(9):
        for x in range(3):
            canvas[(5 + row) * 32 + col * 4 + x] = frames[phase * 27 + row * 3 + x]
(OUT / 'machine-map.bin').write_bytes(canvas)
inc = f'DEF DIGIT_ZERO EQU {lookup["0"]}\n'
inc += 'SECTION "Artwork", ROM0\nTiles:\n    INCBIN "build/scroll-tiles.bin"\nTilesEnd:\nTitleMap:\n    INCBIN "build/title-map.bin"\nMachineMap:\n    INCBIN "build/machine-map.bin"\nFrames:\n    INCBIN "build/scroll-frames.bin"\nFramePointers:\n'
inc += ''.join(f'    dw Frames + {phase * 27}\n' for phase in range(36))
inc += 'Destinations:\n' + ''.join(f'    dw ${0x98a0 + col * 4:04x}\n' for col in range(5))
inc += 'InitialPhases: db 0, 6, 12, 18, 24\nStops: db 64, 48, 32, 16, 0\n'
(OUT / 'assets.inc').write_text(inc)
