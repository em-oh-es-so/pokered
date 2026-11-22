from pathlib import Path
import json
import runpy
from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
shared = runpy.run_path(str(HERE / 'preview_classic.py'))
OUT = HERE / 'build/five'
OUT.mkdir(parents=True, exist_ok=True)
base = Image.open(shared['OUT'] / 'classic-stopped-native.png').convert('L')
strip = shared['strip']

def encode(tile):
    data = bytearray()
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            p = tile.getpixel((x, y))
            assert p in (0, 85, 170, 255)
            v = (255 - p) // 85
            lo = (lo << 1) | (v & 1)
            hi = (hi << 1) | (v >> 1)
        data.extend((lo, hi))
    return bytes(data)

def decode(data):
    return Image.frombytes('L', (8, 8), bytes(255 - 85 * (((data[y * 2] >> bit) & 1) | (((data[y * 2 + 1] >> bit) & 1) << 1)) for y in range(8) for bit in range(7, -1, -1)))

cells = []
for reel in range(5):
    x = 8 + 30 * reel
    cells.append([(col, row) for row in range(5, 15) for col in range(x // 8, (x + 23) // 8 + 1)])
occupied = set()
for region in cells:
    assert not occupied.intersection(region)
    occupied.update(region)
assert [len(region) for region in cells] == [30, 40, 40, 40, 30]
static = []
lookup = {}
background_map = bytearray(1024)
for row in range(18):
    for col in range(20):
        if (col, row) in occupied:
            continue
        data = encode(base.crop((col * 8, row * 8, col * 8 + 8, row * 8 + 8)))
        if data not in lookup:
            lookup[data] = len(static)
            static.append(data)
        assert lookup[data] < 256
        background_map[row * 32 + col] = lookup[data]

plan = [None] * 5
cursor = [len(static), 0]
order = sorted(range(5), key=lambda r: -len(cells[r]))
def allocate(i):
    if i == len(order):
        return True
    reel = order[i]
    count = len(cells[reel])
    for bank in (0, 1):
        start = cursor[bank]
        if start + 2 * count > 256:
            continue
        plan[reel] = (bank, start, start + count)
        cursor[bank] += 2 * count
        if allocate(i + 1):
            return True
        cursor[bank] = start
        plan[reel] = None
    return False
if not allocate(0):
    raise ValueError(f'Cannot fit static cabinet ({len(static)} tiles) and paired reel buffers without changing layout')
used = {(0, tile) for tile in range(len(static))}
for reel, (bank, first, second) in enumerate(plan):
    for start in (first, second):
        for tile in range(start, start + len(cells[reel])):
            assert (bank, tile) not in used
            used.add((bank, tile))
assert all(0 <= tile < 256 for bank, tile in used)
(OUT / 'static.2bpp').write_bytes(b''.join(static))
(OUT / 'background.map').write_bytes(background_map)
all_frames = []
for reel in range(5):
    frames = []
    x = 8 + 30 * reel
    for phase in range(36):
        image = base.copy()
        for y in range(72):
            sy = (phase * 4 + y) % 144
            image.paste(strip.crop((0, sy, 24, sy + 1)), (x, 42 + y))
        data = bytearray()
        rebuilt = base.copy()
        for col, row in cells[reel]:
            tile = image.crop((col * 8, row * 8, col * 8 + 8, row * 8 + 8))
            packed = encode(tile)
            data.extend(packed)
            rebuilt.paste(decode(packed), (col * 8, row * 8))
        assert ImageChops.difference(image, rebuilt).getbbox() is None
        frames.append(bytes(data))
    all_frames.append(frames)
    for half in (0, 1):
        blob = b''.join(frames[half * 18:(half + 1) * 18])
        assert len(blob) <= 16384
        (OUT / f'reel-{reel}-{half}.bin').write_bytes(blob)
initial = base.copy()
for reel in range(5):
    data = all_frames[reel][reel * 6]
    for i, (col, row) in enumerate(cells[reel]):
        initial.paste(decode(data[i * 16:(i + 1) * 16]), (col * 8, row * 8))
assert ImageChops.difference(base, initial).getbbox() is None
inc = 'SECTION "Fixed Cabinet", ROMX[$4000], BANK[1]\nStaticTiles:\n    INCBIN "build/five/static.2bpp"\nStaticTilesEnd:\nBackgroundMap:\n    INCBIN "build/five/background.map"\n'
for reel in range(5):
    for half in (0, 1):
        inc += f'SECTION "Reel {reel} Half {half}", ROMX[$4000], BANK[{2 + reel * 2 + half}]\n    INCBIN "build/five/reel-{reel}-{half}.bin"\n'
inc += 'SECTION "Five Reel Tables", ROM0\nFrameTables:\n    dw ' + ', '.join(f'Sources{r}' for r in range(5)) + '\n'
for reel in range(5):
    inc += f'Sources{reel}:\n'
    for phase in range(36):
        inc += f'    db {2 + reel * 2 + phase // 18}\n    dw ${0x4000 + (phase % 18) * len(cells[reel]) * 16:04x}\n'
for name, values in [('VRAMBanks', [p[0] for p in plan]), ('InitialVisible', [p[1] for p in plan]), ('InitialHidden', [p[2] for p in plan]), ('TileCounts', [len(c) for c in cells]), ('InitialPhases', [0, 6, 12, 18, 24]), ('SpinLengths', [48, 60, 72, 84, 96])]:
    inc += name + ': db ' + ', '.join(map(str, values)) + '\n'
inc += 'FrameSizes: dw ' + ', '.join(str(len(c) * 16) for c in cells) + '\n'
inc += 'SetAttributes:\n'
for reel in range(5):
    inc += f'    ld a, {plan[reel][0] * 8}\n'
    for col, row in cells[reel]:
        inc += f'    ld [${0x9800 + row * 32 + col:04x}], a\n'
inc += '    ret\nPaintTable: dw ' + ', '.join(f'Paint{r}' for r in range(5)) + '\n'
for reel in range(5):
    inc += f'Paint{reel}:\n    ld a, [Visible + {reel}]\n    ld b, a\n'
    for col, row in cells[reel]:
        inc += f'    ld a, b\n    ld [${0x9800 + row * 32 + col:04x}], a\n    inc b\n'
    inc += '    ret\n'
inc += 'Palette: db $ff, $7f, $b5, $56, $4a, $29, $00, $00\n'
(OUT / 'assets.inc').write_text(inc)
report = {'static_tiles': len(static), 'buffer_allocation': [{'reel': r, 'bank': p[0], 'visible_start': p[1], 'hidden_start': p[2], 'tiles_each': len(cells[r])} for r, p in enumerate(plan)], 'overlap_check_passed': True, 'total_allocated_tiles': len(used), 'frame_cases_verified': 180, 'initial_cabinet_exact': True, 'bytes_streamed_per_step': sum(len(c) for c in cells) * 16, 'runtime_tested': False}
(OUT / 'five-report.json').write_text(json.dumps(report, indent=2))
base.resize((1280, 1152), Image.Resampling.NEAREST).save(OUT / 'expected-cabinet-8x.png')
(OUT / 'README.txt').write_text('POKESLOT FIVE-REEL STREAMING DIAGNOSTIC - Game Boy Color only.\nBoots directly into the approved cabinet. Tap A to spin all five reels. They stop left to right; tap A again after all stop to repeat.\nEach reel has a separate position, countdown and two VRAM buffers. Fixed cabinet tiles are deduplicated separately. Build fails if buffer pairs cannot fit without overlap.\nAll five buffers are transferred on every animation step, including unchanged stopped reels, to keep the transfer workload consistent. CPU double-speed is enabled for map updates.\nCredit, payout and bet are static. No title screen, accounting, saving, machine selection, help or sound. This is a rendering diagnostic, not a playable wagering game.\nCheck scrolling speed, left-to-right stops, whole-symbol alignment, repeat spins, unchanged cabinet, and readable text. Timing and emulator behavior remain unverified until tested.\nThe earlier one-reel diagnostic and original ROM build remain unchanged.\n')
print(json.dumps(report, indent=2))
