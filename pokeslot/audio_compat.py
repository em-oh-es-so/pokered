from pathlib import Path
import json
import re

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/audio'
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
for name in ('bench.asm','native.inc'):
    path=OUT/name
    before=path.read_text()
    after=normalize_ldh(before)
    changes[name]=sum(a!=b for a,b in zip(before.splitlines(),after.splitlines()))
    path.write_text(after)
version=(HERE.parent/'.rgbds-version').read_text().strip()
(OUT/'audio-compat-report.json').write_text(json.dumps({'rgbds_version':version,'address_forms_checked':512,'unchanged_cases_checked':len(unchanged),'comment_preservation_checked':True,'changed_lines':changes,'full_rom_build_verified':False},indent=2))
