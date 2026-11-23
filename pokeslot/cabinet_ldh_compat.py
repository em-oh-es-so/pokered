from pathlib import Path
import json
import re

OUT=Path(__file__).resolve().parent/'build/play'

def normalize_ldh(text):
    result=[]
    for line in text.splitlines(keepends=True):
        if re.match(r'^\s*ldh\b',line,re.I):
            code,separator,comment=line.partition(';')
            code=re.sub(r'\[\s*\$([0-9a-f]{1,2})\s*\]',lambda m:f'[${0xff00+int(m[1],16):04X}]',code,flags=re.I)
            line=code+separator+comment
        result.append(line)
    return ''.join(result)

def main():
    checked=0
    for address in range(256):
        for line in (f'    ldh [${address:02x}], a\n',f'    LDH a, [${address:02X}]\n'):
            converted=normalize_ldh(line)
            assert f'[${0xff00+address:04X}]' in converted
            assert normalize_ldh(converted)==converted
            checked+=1
    unchanged=['    ldh [$FF44], a\n','    ldh a, [rAUDVOL]\n','    ldh [c], a\n','    ld a, [$44]\n','; ldh [$44], a\n','    db $44\n','    ldh [$100], a\n']
    assert all(normalize_ldh(line)==line for line in unchanged)
    assert normalize_ldh('ldh [$26], a ; [$44]\n')=='ldh [$FF26], a ; [$44]\n'
    assert (OUT/'main.asm').is_file()
    changes={}
    for path in sorted(OUT.rglob('*')):
        if path.suffix not in ('.asm','.inc'):
            continue
        before=path.read_text()
        after=normalize_ldh(before)
        assert normalize_ldh(after)==after
        count=sum(a!=b for a,b in zip(before.splitlines(),after.splitlines()))
        if count:
            path.write_text(after)
        changes[str(path.relative_to(OUT))]=count
    report={'scope':'Generated build/play assembly only; invoked by memory-check workflow','address_forms_checked':checked,'unchanged_cases_checked':len(unchanged),'idempotence_checked':True,'comment_preservation_checked':True,'changed_lines_by_file':changes,'gameplay_sources_modified':False,'normal_playable_build_recipe_modified':False}
    (OUT/'cabinet-ldh-compat-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
