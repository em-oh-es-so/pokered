from pathlib import Path
import json
import runpy
from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
shared = runpy.run_path(str(HERE / 'preview_classic.py'))
OUT = HERE / 'build/stream'
OUT.mkdir(parents=True, exist_ok=True)
base = Image.open(shared['OUT'] / 'classic-stopped-native.png').convert('L')
strip = shared['strip']
assert base.size == (160, 144)

def encode(image):
    result = bytearray()
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            pixel = image.getpixel((x, y))
            assert pixel in (0, 85, 170, 255)
            value = (255 - pixel) // 85
            lo = (lo << 1) | (value & 1)
            hi = (hi << 1) | (value >> 1)
        result.extend((lo, hi))
    return bytes(result)

def decode(data):
    pixels = []
    for y in range(8):
        lo, hi = data[y * 2:y * 2 + 2]
        for bit in range(7, -1, -1):
            value = ((lo >> bit) & 1) | (((hi >> bit) & 1) << 1)
            pixels.append(255 - 85 * value)
    return Image.frombytes('L', (8, 8), bytes(pixels))

tiles = []
lookup = {}
background_map = bytearray(1024)
for row in range(18):
    for col in range(20):
        tile = base.crop((col * 8, row * 8, col * 8 + 8, row * 8 + 8))
        data = encode(tile)
        if data not in lookup:
            lookup[data] = len(tiles)
            tiles.append(data)
        background_map[row * 32 + col] = lookup[data]
assert len(tiles) <= 256
(OUT / 'static.2bpp').write_bytes(b''.join(tiles))
(OUT / 'background.map').write_bytes(background_map)
cells = [(col, row) for row in range(5, 15) for col in range(1, 4)]
assert len(cells) == 30
frames = []
for phase in range(36):
    expected = base.copy()
    for y in range(72):
        sy = (phase * 4 + y) % 144
        expected.paste(strip.crop((0, sy, 24, sy + 1)), (8, 42 + y))
    data = bytearray()
    reconstructed = base.copy()
    for col, row in cells:
        tile = expected.crop((col * 8, row * 8, col * 8 + 8, row * 8 + 8))
        encoded = encode(tile)
        data.extend(encoded)
        reconstructed.paste(decode(encoded), (col * 8, row * 8))
    assert len(data) == 480
    assert ImageChops.difference(expected, reconstructed).getbbox() is None
    frames.append(bytes(data))
(OUT / 'frames-a.bin').write_bytes(b''.join(frames[:18]))
(OUT / 'frames-b.bin').write_bytes(b''.join(frames[18:]))
base.resize((1280, 1152), Image.Resampling.NEAREST).save(OUT / 'expected-cabinet-8x.png')
inc = 'SECTION "Static Cabinet", ROMX[$4000], BANK[1]\nStaticTiles:\n    INCBIN "build/stream/static.2bpp"\nStaticTilesEnd:\nBackgroundMap:\n    INCBIN "build/stream/background.map"\n'
inc += 'SECTION "Reel Frames A", ROMX[$4000], BANK[2]\nFramesA:\n    INCBIN "build/stream/frames-a.bin"\n'
inc += 'SECTION "Reel Frames B", ROMX[$4000], BANK[3]\nFramesB:\n    INCBIN "build/stream/frames-b.bin"\n'
inc += 'SECTION "Streaming Tables", ROM0\nFrameSources:\n'
for phase in range(36):
    inc += f'    db {2 + phase // 18}\n    dw ${0x4000 + (phase % 18) * 480:04x}\n'
inc += 'SetReelAttributes:\n    ld a, 8\n'
for col, row in cells:
    inc += f'    ld [${0x9800 + row * 32 + col:04x}], a\n'
inc += '    ret\nUpdateReelMap:\n    ld a, [Buffer]\n    ld b, a\n'
for col, row in cells:
    inc += f'    ld a, b\n    ld [${0x9800 + row * 32 + col:04x}], a\n    inc b\n'
inc += '    ret\nPalette:\n    db $ff, $7f, $b5, $56, $4a, $29, $00, $00\n'
(OUT / 'assets.inc').write_text(inc)
report = {'static_tiles_bank_0': len(tiles), 'dynamic_tiles_bank_1': 60, 'tiles_per_buffer': 30, 'transfer_bytes_per_step': 480, 'hblank_blocks_per_step': 30, 'phases_verified': len(frames), 'approved_pixels_preserved': True, 'target': 'Game Boy Color only', 'runtime_tested': False}
(OUT / 'streaming-report.json').write_text(json.dumps(report, indent=2))
(OUT / 'README.txt').write_text('POKESLOT CABINET STREAMING TEST - Game Boy Color only.\nThis is a separate diagnostic, not a replacement for the existing game ROM.\nBoots directly into the approved cabinet. Tap A to scroll the FIRST reel through one full strip cycle. Tap A again after it stops to repeat.\nThe other four reels, credits, payout and bet are static. No title screen, accounting, saving, help or sound in this diagnostic.\nThe first reel uses two 30-tile buffers in VRAM bank 1. The cabinet remains in bank 0.\nEach step transfers 480 bytes to the hidden buffer using HBlank DMA, then swaps tile references in VBlank.\nExpected behavior: no flashing, no cabinet/text damage, partial symbols during scrolling, clean whole-symbol stop.\nPixel reconstruction checks are not emulator or hardware tests. Build and Delta checks are still required.\nThe existing Makefile and main ROM workflow are unchanged.\n')
print(json.dumps(report, indent=2))
