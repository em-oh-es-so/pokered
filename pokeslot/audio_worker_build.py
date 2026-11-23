from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/audio'
path=OUT/'bench.asm'
bench=path.read_text()
def replace(text,old,new):
    assert text.count(old)==1, ('Ambiguous audio worker patch',old)
    return text.replace(old,new)

bench=replace(bench,'ControlEnd:\n','''AudioPending: ds 1
AudioBusy: ds 1
AudioFrameOverrun: ds 1
AudioFrameRequests: ds 2
AudioWorkerStartLY: ds 1
ControlEnd:
''')
bench=replace(bench,'Main:\n    ld a, [Command]\n','''Main:
    ld a, [AudioPending]
    and a
    call nz, AudioWorker
    ld a, [Command]
''')
bench=replace(bench,'.waitForSetupWindow\n    ldh a, [$FF44]\n    cp 16\n    jr nc, .waitForSetupWindow\n','''.waitForSetupWindow
    ldh a, [$FF44]
    cp 16
    jr c, .setupWindowReady
    ld a, [AudioPending]
    and a
    call nz, AudioWorker
    jr .waitForSetupWindow
.setupWindowReady
''')
start=bench.index('AudioIRQ:\n')
end=bench.index('CryPresets:\n',start)
worker=replace(bench[start:end],'AudioIRQ:\n','AudioWorker:\n')
saves='    push af\n    push bc\n    push de\n    push hl\n'
worker=replace(worker,saves,saves+'''    di
    xor a
    ld [AudioPending], a
    ld a, 1
    ld [AudioBusy], a
    ei
''')
entry_start=worker.index('    ldh a, [$FF44]\n    ld [AudioEntryLY], a\n')
entry_end=worker.index('\n.timingEntryReady\n',entry_start)+len('\n.timingEntryReady\n')
worker=worker[:entry_start]+'''    ldh a, [$FF44]
    ld [AudioWorkerStartLY], a
'''+worker[entry_end:]
worker=worker.replace('    ld a, [AudioEntryLY]\n','    ld a, [AudioWorkerStartLY]\n')
worker=replace(worker,'    reti\n','    ret\n')
restores='    pop hl\n    pop de\n    pop bc\n    pop af\n    ret\n'
worker=replace(worker,restores,'    xor a\n    ld [AudioBusy], a\n'+restores)
irq='''AudioIRQ:
    push af
    push hl
    ldh a, [$FF44]
    ld [AudioEntryLY], a
    cp 144
    jr z, .onTime
    ld hl, AudioLateEntries
    inc [hl]
    jr nz, .onTime
    inc hl
    inc [hl]
.onTime
    ld a, [AudioBusy]
    and a
    jr nz, .missed
    ld a, [AudioPending]
    and a
    jr z, .request
.missed
    ld a, 1
    ld [AudioFrameOverrun], a
.request
    ld a, 1
    ld [AudioPending], a
    ld hl, AudioFrameRequests
    inc [hl]
    jr nz, .exit
    inc hl
    inc [hl]
.exit
    pop hl
    pop af
    reti
'''
bench=bench[:start]+worker+'\n'+irq+'\n'+bench[end:]
path.write_text(bench)
report_path=OUT/'audio-compat-report.json'
report=json.loads(report_path.read_text())
report.update({'scheduler':'VBlank requests work; foreground executes native audio','pass_policy':'No missed frame requests, stable cadence and non-silent output','vblank_only_limit_still_measured_but_not_a_playback_pass_requirement':True,'cabinet_graphics_dma_safety_verified':False})
report_path.write_text(json.dumps(report,indent=2))
