from pathlib import Path
import json
import sys
from audio_ram_probe import prepare as prepare_probe

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/audio'
PLAY=HERE/'build/play'

def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)

def prepare():
    prepare_probe()
    inc=(OUT/'ram-probe.inc').read_text()
    inc=replace(inc,'SECTION "Native Audio RAM", WRAM0\n','SECTION "Native Audio RAM", WRAM0[$c800]\n')
    inc=replace(inc,'AudioRAMProbeEnd:\nENDL\n','''AudioRAMProbeEnd:
    ds $2000-(@-AudioRAMProbeStart), 0
AudioSRAMReservedEnd:
ENDL
''')
    inc+='''
SECTION "Cabinet audio control reservation", WRAM0[$c900]
CabinetAudioControlStart:
NativeSoundId: ds 1
NativeChannelsLeft: ds 1
NativeHeaderPointer: ds 2
    ds 60
CabinetAudioControlEnd:
SECTION "Cabinet stack reservation", WRAMX[$df00], BANK[1]
CabinetStackReservationStart:
    ds $100
CabinetStackReservationEnd:
'''
    (OUT/'cabinet-audio-layout.inc').write_text(inc)
    bench=(OUT/'bench.asm').read_text()
    marker='SECTION "Audio VBlank"'
    assert bench.count(marker)==1
    prelude=bench[:bench.index(marker)]
    cabinet=(PLAY/'main.asm').read_text()
    (OUT/'cabinet-audio-layout.asm').write_text(prelude+cabinet+'\nINCLUDE "build/audio/cabinet-audio-layout.inc"\n')

def symbols(path):
    result={}
    for line in path.read_text().splitlines():
        parts=line.split()
        if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
            bank,address=parts[0].split(':')
            result[parts[1]]=(int(bank,16),int(address,16))
    return result

def report():
    old=symbols(PLAY/'play.sym')
    new=symbols(OUT/'cabinet-audio-layout.sym')
    def address(name):
        return new[name][1]
    assert new['AudioRAMProbeStart']==(0,0xa000)
    assert address('AudioRAMProbeEnd')<=0xc000
    assert address('AudioSRAMReservedEnd')==0xc000
    assert address('NativeRAMStart')==0xc800
    assert address('NativeRAMEnd')<=0xc900
    assert address('CabinetAudioControlStart')==0xc900
    assert address('CabinetAudioControlEnd')==0xc940
    assert new['CabinetStackReservationStart']==(1,0xdf00)
    assert new['CabinetStackReservationEnd']==(1,0xe000)
    unchanged_ram=[]
    for name,location in old.items():
        if 0xc000<=location[1]<0xe000:
            assert new.get(name)==location,('Cabinet RAM symbol moved',name,location,new.get(name))
            unchanged_ram.append(name)
    assert unchanged_ram
    assert address('PlayStateEnd')<=0xc800
    baseline=(PLAY/'pokeslot-play.gbc').read_bytes()
    candidate=(OUT/'cabinet-audio-layout.gbc').read_bytes()
    limit=24*0x4000
    assert len(baseline)>=limit and len(candidate)>=limit
    header_fields={0x147,0x148,0x149,0x14d,0x14e,0x14f}
    changes=[i for i in range(limit) if baseline[i]!=candidate[i] and i not in header_fields]
    assert not changes,('Existing cabinet ROM bytes changed',changes[:20])
    result={'checkpoint':'Audio-disabled cabinet memory reservation and baseline comparison','static_link_and_reservations_passed':True,'module_bytes':address('AudioRAMProbeEnd')-address('AudioRAMProbeStart'),'sram_reserved_bytes':8192,'sram_bank':0,'sram_range':['0xa000','0xc000'],'native_state_range':[hex(address('NativeRAMStart')),hex(address('NativeRAMEnd'))],'audio_control_range':['0xc900','0xc940'],'stack_reservation_bank':1,'stack_reservation_range':['0xdf00','0xe000'],'cabinet_ram_symbols_checked':len(unchanged_ram),'cabinet_ram_symbol_locations_unchanged':True,'existing_rom_banks_compared':24,'existing_rom_bytes_unchanged_except_cartridge_header':True,'cartridge_header_differences':[hex(i) for i in sorted(header_fields) if baseline[i]!=candidate[i]],'audio_playback_enabled':False,'runtime_stack_high_water_verified':False,'saved_data_compatibility_verified':False,'cabinet_graphics_dma_safety_verified':False,'cabinet_audio_integration_complete':False,'normal_playable_build_modified':False}
    (OUT/'cabinet-audio-layout-report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    if sys.argv[1:]==['--report']:
        report()
    else:
        assert not sys.argv[1:]
        prepare()
