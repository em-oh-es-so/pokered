from pathlib import Path
import json
import runpy
import struct
from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
shared = runpy.run_path(str(HERE / 'preview_classic.py'))
OUT = shared['OUT'] / 'integration'
OUT.mkdir(exist_ok=True)
base = Image.open(shared['OUT'] / 'classic-stopped-native.png').convert('L')
strip = shared['strip']
label = shared['label']
assert base.size == (160, 144)

atlas = []
indices = {}
decoded = {}

def encode(raw):
    data = bytearray()
    for y in range(8):
        lo = hi = 0
        for x in range(8):
            pixel = raw[y * 8 + x]
            if pixel not in (0, 85, 170, 255):
                raise ValueError('Pixel is outside the four-shade palette')
            value = (255 - pixel) // 85
            lo = (lo << 1) | (value & 1)
            hi = (hi << 1) | (value >> 1)
        data.extend((lo, hi))
    return bytes(data)

def decode(data):
    pixels = []
    for y in range(8):
        lo, hi = data[y * 2:y * 2 + 2]
        for bit in range(7, -1, -1):
            value = ((lo >> bit) & 1) | (((hi >> bit) & 1) << 1)
            pixels.append(255 - 85 * value)
    return Image.frombytes('L', (8, 8), bytes(pixels))

def tilemap(image):
    result = []
    for y in range(0, 144, 8):
        for x in range(0, 160, 8):
            raw = image.crop((x, y, x + 8, y + 8)).tobytes()
            if raw not in indices:
                index = len(atlas)
                indices[raw] = index
                data = encode(raw)
                atlas.append(data)
                decoded[index] = decode(data)
                assert decoded[index].tobytes() == raw
            result.append(indices[raw])
    return result

def rebuild(mapping):
    result = Image.new('L', (160, 144), 255)
    for i, index in enumerate(mapping):
        result.paste(decoded[index], ((i % 20) * 8, (i // 20) * 8))
    return result

base_map = tilemap(base)
base_tiles = len(atlas)
roundtrip = rebuild(base_map)
assert ImageChops.difference(base, roundtrip).getbbox() is None
roundtrip.resize((1280, 1152), Image.Resampling.NEAREST).save(OUT / 'compiled-cabinet-8x.png')
records = []
all_maps = bytearray()
for reel in range(5):
    x = 8 + reel * 30
    for phase in range(36):
        image = base.copy()
        start = phase * 4
        for y in range(72):
            sy = (start + y) % 144
            image.paste(strip.crop((0, sy, 24, sy + 1)), (x, 42 + y))
        mapping = tilemap(image)
        assert ImageChops.difference(image, rebuild(mapping)).getbbox() is None
        changed = [i for i, pair in enumerate(zip(base_map, mapping)) if pair[0] != pair[1]]
        records.append({'reel': reel, 'phase': phase, 'offset': len(all_maps), 'changed_tile_cells': changed})
        all_maps.extend(struct.pack('<360H', *mapping))
reel_tiles = len(atlas)

counter_records = []
for field, x, y, width in [('credit', 16, 12, 4), ('payout', 104, 12, 4), ('bet', 40, 135, 1)]:
    for position in range(width):
        for digit in range(10):
            image = base.copy()
            dx = x + position * 8
            image.paste(85, (dx, y, dx + 8, y + 8))
            label(image, dx, y, str(digit))
            mapping = tilemap(image)
            assert ImageChops.difference(image, rebuild(mapping)).getbbox() is None
            changes = [[i, index] for i, index in enumerate(mapping) if index != base_map[i]]
            counter_records.append({'field': field, 'position': position, 'digit': digit, 'changes': changes})

(OUT / 'cabinet-atlas.2bpp').write_bytes(b''.join(atlas))
(OUT / 'cabinet-map.u16le').write_bytes(struct.pack('<360H', *base_map))
(OUT / 'reel-maps.u16le').write_bytes(all_maps)
(OUT / 'reel-records.json').write_text(json.dumps(records, indent=2))
(OUT / 'counter-records.json').write_text(json.dumps(counter_records, indent=2))
report = {
    'approved_image_roundtrip_exact': True,
    'reel_cases_roundtripped': len(records),
    'counter_cases_roundtripped': len(counter_records),
    'static_unique_tiles': base_tiles,
    'static_plus_reel_unique_tiles': reel_tiles,
    'total_unique_tiles': len(atlas),
    'atlas_bytes': len(atlas) * 16,
    'fits_256_tile_atlas': len(atlas) <= 256,
    'fits_512_tile_atlas': len(atlas) <= 512,
    'reel_window_pixels': [24, 72],
    'reel_step_pixels': 4,
    'rom_changed': False,
    'status': 'Asset audit only; renderer, banking, timing and emulator tests still required',
    'format': 'Tile references are 16-bit little-endian audit indices, not directly loadable hardware tilemaps'
}
(OUT / 'integration-report.json').write_text(json.dumps(report, indent=2))
(OUT / 'README.txt').write_text('Asset integration checkpoint, not a new ROM.\ncompiled-cabinet-8x.png is reconstructed from encoded 2bpp tiles and must exactly match the approved preview.\nAll 180 single-reel phase cases and 90 numeric-overlay cases are reconstructed and checked.\nThe atlas report guides the next renderer implementation; it does not select or change the target console.\nIndices in .u16le files are little-endian unsigned 16-bit audit references, not Game Boy VRAM tile IDs.\nDo not load the atlas or maps directly into the current ROM. Banking and runtime mapping remain to be implemented.\nBudget counts do not include every future screen or all simultaneous reel/counter boundary combinations.\nNo changes to the approved cabinet pixels or playable ROM.\n')
print(json.dumps(report, indent=2))
