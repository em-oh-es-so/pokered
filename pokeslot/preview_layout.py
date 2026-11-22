from pathlib import Path
import json
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'pokeslot/build/layout-review'
OUT.mkdir(parents=True, exist_ok=True)

def load_tiles(path):
    image = Image.open(ROOT / path).convert('RGBA')
    bg = Image.new('RGBA', image.size, 'white')
    bg.alpha_composite(image)
    image = bg.convert('L')
    assert image.width % 8 == 0 and image.height % 8 == 0
    return [image.crop((x, y, x + 8, y + 8)) for y in range(0, image.height, 8) for x in range(0, image.width, 8)]

font = load_tiles('gfx/font/font.png')
extra = load_tiles('gfx/font/font_extra.png')
slots = load_tiles('gfx/slots/red_slots_1.png')
symbols = load_tiles('gfx/slots/red_slots_2.png')
codes = {chr(65 + i): 0x80 + i for i in range(26)}
codes.update({str(i): 0xf6 + i for i in range(10)})
codes.update({':': 0x9c, '-': 0xe3})

def glyph(char):
    if char == ' ':
        return Image.new('L', (8, 8), 255)
    index = codes[char] - 0x80
    if index >= len(font):
        raise ValueError('Missing native font glyph: ' + char)
    return font[index]

def text(canvas, x, y, value):
    assert x >= 0 and y >= 0 and x + 8 * len(value) <= 160 and y + 8 <= 144
    for i, char in enumerate(value):
        canvas.paste(glyph(char), (x + i * 8, y))

def quantize(image):
    return image.point(lambda p: round(p / 85) * 85)

bank = {i: tile for i, tile in enumerate(slots)}
bank.update({0x25 + i: tile for i, tile in enumerate(symbols)})
bank.update({0x80 + i: tile for i, tile in enumerate(font)})
raw = (ROOT / 'gfx/slots/slots.tilemap').read_bytes()
assert len(raw) >= 360
reference = Image.new('L', (160, 144), 255)
for i, index in enumerate(raw[:360]):
    if index in bank:
        reference.paste(bank[index], ((i % 20) * 8, (i // 20) * 8))
reference = quantize(reference)
reference.save(OUT / 'original-background-native.png')
reference.resize((1280, 1152), Image.Resampling.NEAREST).save(OUT / 'original-background-8x.png')

species = ['bulbasaur', 'charmander', 'squirtle', 'pikachu', 'eevee', 'ditto']
icons = []
for name in species:
    image = Image.open(ROOT / 'gfx/pokemon/front' / (name + '.png')).convert('RGBA')
    bg = Image.new('RGBA', image.size, 'white')
    bg.alpha_composite(image)
    image = bg.convert('L')
    bounds = ImageChops.difference(image, Image.new('L', image.size, 255)).getbbox()
    if bounds is None:
        raise ValueError('Empty sprite: ' + name)
    image = image.crop(bounds)
    image.thumbnail((24, 24), Image.Resampling.NEAREST)
    icon = Image.new('L', (24, 24), 255)
    icon.paste(image, ((24 - image.width) // 2, (24 - image.height) // 2))
    icons.append(quantize(icon))

strip = Image.new('L', (24, 144), 255)
for i, icon in enumerate(icons):
    strip.paste(icon, (0, i * 24))

results = []
for name, offset in [('cabinet-stopped', 0), ('cabinet-mid-scroll', 4)]:
    screen = Image.new('L', (160, 144), 255)
    draw = ImageDraw.Draw(screen)
    draw.rectangle((0, 0, 159, 143), outline=0)
    draw.line((2, 2, 157, 2), fill=170)
    draw.line((2, 141, 157, 141), fill=85)
    draw.rectangle((4, 5, 155, 19), outline=85)
    text(screen, 48, 8, 'POKESLOT')
    text(screen, 8, 25, 'C:0200')
    text(screen, 104, 25, 'BET:1')
    for col in range(5):
        x = 8 + col * 30
        draw.rectangle((x - 2, 37, x + 25, 114), outline=85)
        draw.line((x - 1, 38, x + 24, 38), fill=170)
        draw.line((x + 25, 39, x + 25, 113), fill=0)
        window = Image.new('L', (24, 72), 255)
        phase = (col * 24 + offset) % 144
        for y in range(72):
            window.paste(strip.crop((0, (phase + y) % 144, 24, (phase + y) % 144 + 1)), (0, y))
        screen.paste(window, (x, 40))
    if len(slots) > 0x15:
        for x in (0, 152):
            screen.paste(slots[0x14], (x, 68))
            screen.paste(slots[0x15], (x, 76))
    draw.line((5, 121, 154, 121), fill=170)
    text(screen, 24, 128, 'A SPIN  B HELP')
    screen = quantize(screen)
    assert set(screen.getdata()) <= {0, 85, 170, 255}
    unique = {screen.crop((x, y, x + 8, y + 8)).tobytes() for y in range(0, 144, 8) for x in range(0, 160, 8)}
    results.append({'name': name, 'unique_static_tiles': len(unique)})
    screen.save(OUT / (name + '-native.png'))
    screen.resize((1280, 1152), Image.Resampling.NEAREST).save(OUT / (name + '-8x.png'))

atlas = Image.new('L', (128, ((len(slots) + 15) // 16) * 8), 255)
for i, tile in enumerate(slots):
    atlas.paste(tile, ((i % 16) * 8, (i // 16) * 8))
atlas.resize((atlas.width * 6, atlas.height * 6), Image.Resampling.NEAREST).save(OUT / 'original-cabinet-tiles.png')
(OUT / 'metrics.json').write_text(json.dumps(results, indent=2))
(OUT / 'README.txt').write_text('PREVIEW ONLY: no ROM changes. Open cabinet-stopped-8x.png first.\nNative images are 160x144 with four shades; enlarged images use nearest-neighbor scaling.\nText uses native Pokemon font tiles without glyph resizing.\nThe cabinet is a new adaptation with original slot lamp tiles, not a complete transplant of the original frame.\nOriginal background reconstruction excludes hardware sprites and is supplied only as an art reference.\nA SPIN and B HELP are proposed labels, not a claim that help is implemented.\nThis pixel mockup is not yet wired to a ROM tilemap. Static tile counts do not validate dynamic rendering or timing.\nThe two reel views check whole-symbol and partial-symbol appearance, not animation smoothness.\n')
