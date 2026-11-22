from pathlib import Path
import json
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'pokeslot/build/layout-review'
OUT.mkdir(parents=True, exist_ok=True)

def load_tiles(path):
    source = Image.open(ROOT / path).convert('RGBA')
    image = Image.new('RGBA', source.size, 'white')
    image.alpha_composite(source)
    image = image.convert('L')
    if image.width % 8 or image.height % 8:
        raise ValueError('Non-tiled image: ' + path)
    return [image.crop((x, y, x + 8, y + 8)) for y in range(0, image.height, 8) for x in range(0, image.width, 8)]

font = load_tiles('gfx/font/font.png')
slots = load_tiles('gfx/slots/red_slots_1.png')
codes = {chr(65 + i): 0x80 + i for i in range(26)}
codes.update({str(i): 0xf6 + i for i in range(10)})
codes.update({':': 0x9c, '-': 0xe3})

def text(canvas, x, y, value):
    assert 0 <= x and x + 8 * len(value) <= 160 and 0 <= y <= 136
    for i, char in enumerate(value):
        if char == ' ':
            tile = Image.new('L', (8, 8), 255)
        else:
            index = codes[char] - 0x80
            if not 0 <= index < len(font):
                raise ValueError(f'Missing native glyph {char!r}: index {index}, font tiles {len(font)}')
            tile = font[index]
        canvas.paste(tile, (x + i * 8, y))

def quantize(image):
    return image.point(lambda p: round(p / 85) * 85)

def save_views(image, name):
    image = quantize(image)
    image.save(OUT / (name + '-native.png'))
    image.resize((image.width * 8, image.height * 8), Image.Resampling.NEAREST).save(OUT / (name + '-8x.png'))

species = ['bulbasaur', 'charmander', 'squirtle', 'pikachu', 'eevee', 'ditto']
strip = Image.new('L', (24, 144), 255)
for i, name in enumerate(species):
    source = Image.open(ROOT / 'gfx/pokemon/front' / (name + '.png')).convert('RGBA')
    image = Image.new('RGBA', source.size, 'white')
    image.alpha_composite(source)
    image = image.convert('L')
    bounds = ImageChops.difference(image, Image.new('L', image.size, 255)).getbbox()
    if bounds is None:
        raise ValueError('Empty sprite: ' + name)
    image = image.crop(bounds)
    image.thumbnail((24, 24), Image.Resampling.NEAREST)
    strip.paste(quantize(image), ((24 - image.width) // 2, i * 24 + (24 - image.height) // 2))

metrics = []
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
        phase = (col * 24 + offset) % 144
        for y in range(72):
            sy = (phase + y) % 144
            screen.paste(strip.crop((0, sy, 24, sy + 1)), (x, 40 + y))
    if len(slots) > 0x15:
        for x in (0, 152):
            screen.paste(slots[0x14], (x, 68))
            screen.paste(slots[0x15], (x, 76))
    draw.line((5, 121, 154, 121), fill=170)
    text(screen, 24, 128, 'A SPIN  B HELP')
    screen = quantize(screen)
    assert set(screen.getdata()) <= {0, 85, 170, 255}
    unique = {screen.crop((x, y, x + 8, y + 8)).tobytes() for y in range(0, 144, 8) for x in range(0, 160, 8)}
    metrics.append({'name': name, 'unique_static_tiles': len(unique)})
    save_views(screen, name)

(OUT / 'metrics.json').write_text(json.dumps(metrics, indent=2))
(OUT / 'README.txt').write_text('PREVIEW ONLY. ROM unchanged. Open cabinet-stopped-8x.png first.\nNative previews are 160x144 with four shades. Enlargements use nearest-neighbor scaling.\nOriginal font tiles are not resized. Cropped 24px Pokemon are automatic conversions.\nThe new cabinet incorporates original lamp tiles; it is not a full transplant of the original cabinet.\nB HELP is a proposed label, not implemented gameplay.\nStatic previews and tile counts do not validate dynamic ROM rendering.\nOptional original background shows only the supplied map rows, without sprites or runtime text.\n')

try:
    symbols = load_tiles('gfx/slots/red_slots_2.png')
    raw = (ROOT / 'gfx/slots/slots.tilemap').read_bytes()
    if not raw or len(raw) % 20 or len(raw) > 360:
        raise ValueError(f'Unexpected reference tilemap size: {len(raw)}')
    bank = dict(enumerate(slots))
    bank.update({0x25 + i: tile for i, tile in enumerate(symbols)})
    bank.update({0x80 + i: tile for i, tile in enumerate(font)})
    reference = Image.new('L', (160, len(raw) // 20 * 8), 255)
    for i, index in enumerate(raw):
        if index in bank:
            reference.paste(bank[index], ((i % 20) * 8, (i // 20) * 8))
    save_views(reference, 'original-background')
    (OUT / 'reference-info.json').write_text(json.dumps({'bytes': len(raw), 'width_tiles': 20, 'rows': len(raw) // 20}, indent=2))
except Exception as error:
    (OUT / 'reference-warning.txt').write_text(f'Optional reference skipped: {type(error).__name__}: {error}\nMain cabinet previews were generated independently.\n')
