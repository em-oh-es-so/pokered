from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'build' / 'art-review'
OUT.mkdir(parents=True, exist_ok=True)
SPECIES = ['bulbasaur', 'charmander', 'squirtle', 'pikachu', 'eevee', 'ditto']
FONT = ImageFont.load_default()
SCALE = 5
sheet = Image.new('RGB', (690, 1100), '#dedede')
draw = ImageDraw.Draw(sheet)
draw.text((12, 12), 'POKESLOT - SYMBOL CANDIDATES (NOT FINAL)', font=FONT, fill='black')
HEADINGS = ['CURRENT 16PX', 'DIRECT 24PX', 'CROPPED 24PX']
for col, heading in enumerate(HEADINGS):
    draw.text((12 + col * 230, 38), heading, font=FONT, fill='black')

def fit(source, size):
    image = source.copy()
    image.thumbnail((size, size), Image.Resampling.NEAREST)
    result = Image.new('L', (size, size), 255)
    result.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    return result

def four_shades(image):
    return image.point(lambda p: (p * 3 // 255) * 85)

def encode(image):
    output = bytearray()
    for ty in range(0, 24, 8):
        for tx in range(0, 24, 8):
            for y in range(8):
                lo = hi = 0
                for x in range(8):
                    value = (255 - image.getpixel((tx + x, ty + y))) // 85
                    lo = (lo << 1) | (value & 1)
                    hi = (hi << 1) | (value >> 1)
                output.extend((lo, hi))
    assert len(output) == 144
    return output

combined = bytearray()
for row, name in enumerate(SPECIES):
    path = ROOT.parent / 'gfx' / 'pokemon' / 'front' / (name + '.png')
    source = Image.open(path).convert('RGBA')
    background = Image.new('RGBA', source.size, 'white')
    background.alpha_composite(source)
    source = background.convert('L')
    bounds = ImageChops.difference(source, Image.new('L', source.size, 255)).getbbox()
    if bounds is None:
        raise ValueError('Empty sprite: ' + name)
    current = four_shades(source.resize((16, 16), Image.Resampling.NEAREST))
    direct = four_shades(fit(source, 24))
    cropped = four_shades(fit(source.crop(bounds), 24))
    for col, image in enumerate((current, direct, cropped)):
        x = 12 + col * 230
        y = 64 + row * 170
        draw.text((x, y), name.upper(), font=FONT, fill='black')
        sheet.paste(image.resize((image.width * SCALE, image.height * SCALE), Image.Resampling.NEAREST).convert('RGB'), (x, y + 18))
    direct.save(OUT / (name + '-direct24.png'))
    cropped.save(OUT / (name + '-cropped24.png'))
    combined.extend(encode(cropped))
assert len(combined) == len(SPECIES) * 9 * 16
(OUT / 'symbols24-candidates.2bpp').write_bytes(combined)
sheet.save(OUT / 'comparison.png')
(OUT / 'README.txt').write_text('Artwork review only. The ROM still uses the previous renderer and controls.\nComparison columns: current 16px, direct fit 24px, cropped fit 24px.\nImages use the same four shades encoded into the candidate tile data.\nEach candidate uses nine 8x8 tiles in row-major order (144 bytes).\nSpecies order: ' + ', '.join(SPECIES) + '.\nCandidates are automatic conversions, not hand-retouched final artwork.\n')
