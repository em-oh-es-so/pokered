from pathlib import Path
import runpy
from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
shared = runpy.run_path(str(HERE / 'preview_layout.py'))
OUT = shared['OUT']
font = shared['font']
codes = shared['codes']
strip = shared['strip']
quantize = shared['quantize']
save_views = shared['save_views']
reference_path = OUT / 'original-background-native.png'
if not reference_path.exists():
    raise RuntimeError('Original cabinet reference is required for the classic preview. Check reference-warning.txt.')
original = Image.open(reference_path).convert('L')
if original.size != (160, 96):
    raise ValueError(f'Expected original 160x96 cabinet region, got {original.size}')

def label(image, x, y, value):
    assert x >= 0 and y >= 0 and x + len(value) * 8 <= 160 and y + 8 <= 144
    for i, char in enumerate(value):
        if char == ' ':
            continue
        tile = font[codes[char] - 0x80]
        mask = ImageOps.invert(tile).point(lambda p: 255 if p >= 128 else 0)
        image.paste(255, (x + i * 8, y), mask)

def extend_frame(source, width, height, edge=3):
    sw, sh = source.size
    result = Image.new('L', (width, height), 255)
    def coordinate(p, target, native):
        if p < edge:
            return p
        if p >= target - edge:
            return native - (target - p)
        return edge + (p - edge) % (native - 2 * edge)
    for y in range(height):
        sy = coordinate(y, height, sh)
        for x in range(width):
            result.putpixel((x, y), source.getpixel((coordinate(x, width, sw), sy)))
    return result

frame_source = original.crop((38, 30, 58, 82))
frame = extend_frame(frame_source, 28, 76)
meowth = original.crop((40, 16, 56, 30))
button = original.crop((42, 82, 54, 94))
checker = original.crop((0, 7, 160, 11))

for name, shift in [('classic-stopped', 0), ('classic-mid-scroll', 4)]:
    screen = Image.new('L', (160, 144), 85)
    draw = ImageDraw.Draw(screen)
    draw.line((0, 0, 159, 0), fill=170)
    draw.line((0, 143, 159, 143), fill=0)
    label(screen, 8, 2, 'CREDIT')
    label(screen, 96, 2, 'PAYOUT')
    label(screen, 16, 12, '0200')
    label(screen, 104, 12, '0000')
    screen.paste(checker, (0, 22))
    for col in range(5):
        x = 8 + col * 30
        screen.paste(meowth, (x + 4, 26))
        screen.paste(frame, (x - 2, 40))
        phase = (col * 24 + shift) % 144
        for y in range(72):
            sy = (phase + y) % 144
            screen.paste(strip.crop((0, sy, 24, sy + 1)), (x, 42 + y))
        screen.paste(button, (x + 6, 120))
    for x in (0, 152):
        for y in (52, 76, 100):
            draw.ellipse((x + 1, y + 1, x + 6, y + 6), fill=0, outline=170)
            draw.point((x + 3, y + 3), fill=85)
    label(screen, 8, 135, 'BET:1')
    label(screen, 112, 135, 'DEMO')
    screen = quantize(screen)
    assert screen.size == (160, 144)
    assert set(screen.getdata()) <= {0, 85, 170, 255}
    save_views(screen, name)

(OUT / 'OPEN-FIRST.txt').write_text('Open classic-stopped-8x.png first.\nThen compare classic-mid-scroll-8x.png and original-background-8x.png.\nOlder cabinet-stopped images are retained for before/after comparison.\nThis is a static preview only. The ROM has not changed.\nDark cabinet, checker strip, Meowth crops, frame edges and button crops come from the original cabinet reference.\nFrame edges are tiled, not smoothly rescaled. Tiny side indicators are newly drawn; the original numbered panels do not fit unchanged.\nCredit, payout and bet are illustrative. This does not implement payout accounting.\nAsset crop placement still needs visual review. This preview is not a guarantee of the final ROM layout or animation performance.\n')
