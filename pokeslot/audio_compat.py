from pathlib import Path
import json
import re

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/audio'
def replace(text,old,new):
    assert text.count(old)==1, ('Ambiguous audio timing patch',old)
    return text.replace(old,new)

def normalize_ldh(text):
    result=[]
    for line in text.splitlines(keepends=True):
        if re.match(r'^\s*ldh\b',line,re.I):
            code,separator,comment=line.partition(';')
            code=re.sub(r'\[\s*\$([0-9a-f]{1,2})\s*\]',lambda m:f'[${0xff00+int(m[1],16):04X}]',code,flags=re.I)
            line=code+separator+comment
        result.append(line)
    return ''.join(result)

for address in range(256):
    for instruction in (f'    ldh [${address:02x}], a\n',f'    LDH a, [${address:02X}]\n'):
        converted=normalize_ldh(instruction)
        assert f'[${0xff00+address:04X}]' in converted
        assert normalize_ldh(converted)==converted
unchanged=['    ldh [$FF44], a\n','    ldh a, [rAUDVOL]\n','    ldh [c], a\n','    ld a, [$44]\n','; ldh [$44], a\n','    db $44\n']
for text in unchanged:
    assert normalize_ldh(text)==text
assert normalize_ldh('ldh [$26], a ; [$44]\n')=='ldh [$FF26], a ; [$44]\n'
changes={}
sweep_sites=0
for name in ('bench.asm','native.inc'):
    path=OUT/name
    before=path.read_text()
    after=normalize_ldh(before)
    changes[name]=sum(a!=b for a,b in zip(before.splitlines(),after.splitlines()))
    if name=='native.inc':
        old='    xor a\n    ldh [$FF25], a\n    ldh [$FF12], a\n'
        new='    xor a\n    ldh [$FF10], a\n    ldh [$FF25], a\n    ldh [$FF12], a\n'
        sweep_sites=after.count(old)
        assert sweep_sites==6, ('Expected exactly six native reset routines',sweep_sites)
        after=after.replace(old,new)
        assert after.count(new)==6
    else:
        after=replace(after,'ControlEnd:\n','''AudioEntryLY: ds 1
AudioExitLY: ds 1
AudioMaximumSpan: ds 1
AudioLateEntries: ds 2
AudioFaultEntryLY: ds 1
AudioFaultExitLY: ds 1
AudioFaultCheckLY: ds 1
ControlEnd:
''')
        after=replace(after,'    jr z, Main\n    di\n    ld b, a\n','''    jr z, Main
.waitForSetupWindow
    ldh a, [$FF44]
    cp 16
    jr nc, .waitForSetupWindow
    di
    ld a, [Command]
    ld b, a
''')
        after=replace(after,'    push hl\n    call $4000\n','''    push hl
    ldh a, [$FF44]
    ld [AudioEntryLY], a
    cp 144
    jr z, .timingEntryReady
    ld hl, AudioLateEntries
    inc [hl]
    jr nz, .timingEntryReady
    inc hl
    inc [hl]
.timingEntryReady
    call $4000
''')
        after=replace(after,'    call $4000\n    ld hl, AudioTicks\n','''    call $4000
    ldh a, [$FF44]
    ld [AudioExitLY], a
    ld b, a
    ld a, [AudioEntryLY]
    ld c, a
    ld a, b
    sub c
    jr nc, .timingSpanReady
    add 154
.timingSpanReady
    ld b, a
    ld a, [AudioMaximumSpan]
    cp b
    jr nc, .timingSpanDone
    ld a, b
    ld [AudioMaximumSpan], a
.timingSpanDone
    ld hl, AudioTicks
''')
        after=replace(after,'.late\n    ld a, 1\n    ld [AudioBudgetExceeded], a\n','''.late
    ld [AudioFaultCheckLY], a
    ld a, [AudioEntryLY]
    ld [AudioFaultEntryLY], a
    ld a, [AudioExitLY]
    ld [AudioFaultExitLY], a
    ld a, 1
    ld [AudioBudgetExceeded], a
''')
        assert '    cp 152\n    jr c, .exit\n' in after
    path.write_text(after)
version=(HERE.parent/'.rgbds-version').read_text().strip()
(OUT/'audio-compat-report.json').write_text(json.dumps({'rgbds_version':version,'address_forms_checked':512,'unchanged_cases_checked':len(unchanged),'comment_preservation_checked':True,'changed_lines':changes,'native_reset_sweep_clears_inserted':sweep_sites,'command_setup_window_scanlines':[0,15],'audio_exit_deadline_unchanged':152,'irq_entry_exit_instrumented':True,'full_rom_build_verified':False},indent=2))
