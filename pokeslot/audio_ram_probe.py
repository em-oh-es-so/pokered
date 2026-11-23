from pathlib import Path
import json
import sys

OUT=Path(__file__).resolve().parent/'build/audio'

def prepare():
    native=(OUT/'native.inc').read_text()
    first='SECTION \"Native Track 24\", ROMX[$4000], BANK[24]\n'.replace('\"','"').replace('\n','\n')
    first='SECTION "Native Track 24", ROMX[$4000], BANK[24]\n'
    following='SECTION "Native Track 25", ROMX[$4000], BANK[25]\n'
    assert native.startswith(first) and native.count(following)==1
    module=native[len(first):native.index(following)]
    state=native[native.index('SECTION "Native Audio RAM"'):]
    image='SECTION "RAM probe image", ROMX[$4000], BANK[24]\n'
    image+='LOAD "RAM probe destination", SRAM[$a000], BANK[0]\nAudioRAMProbeStart:\n'
    image+=module+'\nAudioRAMProbeEnd:\nENDL\n'+state
    (OUT/'ram-probe.inc').write_text(image)
    bench=(OUT/'bench.asm').read_text()
    include='INCLUDE "build/audio/native.inc"'
    assert bench.count(include)==1
    (OUT/'ram-probe.asm').write_text(bench.replace(include,'INCLUDE "build/audio/ram-probe.inc"'))

def report():
    symbols={}
    for line in (OUT/'ram-probe.sym').read_text().splitlines():
        parts=line.split()
        if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
            symbols[parts[1]]=int(parts[0].split(':')[1],16)
    start=symbols['AudioRAMProbeStart']
    end=symbols['AudioRAMProbeEnd']
    assert 0xa000<=start<=end<=0xc000,(start,end)
    size=end-start
    result={'checkpoint':'Static Game Corner audio SRAM placement only','module_bytes':size,'bank_capacity_bytes':8192,'bank_free_bytes':8192-size,'native_state_bytes':symbols['NativeRAMEnd']-symbols['NativeRAMStart'],'module_start':hex(start),'module_end_exclusive':hex(end),'includes_native_engine_effects_cries_drums_and_game_corner':True,'static_assembly_and_link_passed':True,'runtime_copy_and_execution_tested':False,'cabinet_memory_overlap_checked':False,'cabinet_graphics_dma_safety_verified':False,'cabinet_integration_complete':False,'playable_build':False}
    (OUT/'audio-ram-probe-report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    if sys.argv[1:]==['--report']:
        report()
    else:
        assert not sys.argv[1:]
        prepare()
