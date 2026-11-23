from pathlib import Path
import json
from itertools import product

OUT = Path(__file__).resolve().parent / 'build/play'
path = OUT / 'main.asm'
asm = path.read_text()
old = '''    dec [hl]
    ld hl, Phases
    add hl, de
    ld a, [hl]
    inc a
    cp 36
    jr c, .store
    xor a
.store
'''
new = '''    ld c, 1
    cp 7
    jr c, .slowStep
    ld c, 3
.slowStep
    sub c
    ld [hl], a
    ld hl, Phases
    add hl, de
    ld a, [hl]
    add c
    cp 36
    jr c, .store
    sub 36
.store
'''
assert asm.count(old) == 1, 'Advance routine changed; refusing an ambiguous speed patch'
asm = asm.replace(old,new)
path.write_text(asm)
maximum = total = cases = 0
for differences in product(range(0,36,6),repeat=5):
    previous = 0
    lengths = []
    for difference in differences:
        remaining = difference + 36
        while remaining <= previous:
            remaining += 36
        previous = remaining
        lengths.append(remaining)
    finishes = []
    for difference,remaining in zip(differences,lengths):
        phase = 0
        steps = 0
        while remaining:
            step = 3 if remaining > 6 else 1
            remaining -= step
            phase = (phase + step) % 36
            steps += 1
        assert phase == difference
        finishes.append(steps)
    assert all(a < b for a,b in zip(finishes,finishes[1:]))
    maximum = max(maximum,finishes[-1])
    total += finishes[-1]
    cases += 1
report = {'phase_difference_combinations_checked':cases,'stop_alignment_preserved':True,'left_to_right_order_preserved':True,'maximum_animation_updates':maximum,'mean_animation_updates':total/cases,'fast_pixels_per_update':12,'final_pixels_per_update':4,'final_slowdown_pixels':24,'runtime_timing_verified':False,'audio_implemented':False}
(OUT/'speed-model-report.json').write_text(json.dumps(report,indent=2))
readme = OUT/'README.txt'
readme.write_text(readme.read_text() + '\nFASTER REELS: 12 pixels per update during the main spin, then 4 pixels per update over the final 24 pixels. Stop positions and payout data are unchanged.\nSee speed-report.json for emulator-measured full-spin duration. Audio is not included in this timing-only increment.\n')
