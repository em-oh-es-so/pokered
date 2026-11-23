from pathlib import Path
import json
import wave
import numpy as np
from pyboy import PyBoy

OUT=Path(__file__).resolve().parent/'build/audio'
PREVIEWS=OUT/'previews'
PREVIEWS.mkdir(exist_ok=True)
symbols={}
locations={}
for line in (OUT/'native-audio.sym').read_text().splitlines():
    parts=line.split()
    if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
        bank,address=parts[0].split(':')
        symbols[parts[1]]=int(address,16)
        locations[parts[1]]=(int(bank,16),int(address,16))
assets=json.loads((OUT/'audio-assets.json').read_text())
p=PyBoy(str(OUT/'native-audio.gbc'),window='null',sound_emulated=True,sound_sample_rate=24000)
p.set_emulation_speed(0)
results=[]
last_command=None
current_clip=None
current_update=None
last_update=None
worst_update=None
first_vblank_window_miss=None
registered_hooks=[]

def read(name,n=1):
    a=symbols[name]
    return int.from_bytes(bytes(p.memory[a:a+n]),'little')

def timing():
    return {'irq_entry_scanline':read('AudioEntryLY'),'worker_start_scanline':read('AudioWorkerStartLY'),'core_exit_scanline':read('AudioExitLY'),'maximum_core_scanline_span':read('AudioMaximumSpan'),'late_interrupt_entries':read('AudioLateEntries',2),'frame_requests':read('AudioFrameRequests',2),'updates_completed':read('AudioTicks',2),'update_pending':read('AudioPending'),'worker_busy':read('AudioBusy'),'frame_overrun':read('AudioFrameOverrun'),'legacy_vblank_only_limit_met':read('AudioBudgetExceeded')==0,'vblank_fault_start':read('AudioFaultEntryLY'),'vblank_fault_exit':read('AudioFaultExitLY'),'vblank_fault_check':read('AudioFaultCheckLY')}

def begin_update(context):
    global current_update
    current_update={'divider_start':p.memory[0xff04],'entry_scanline':p.memory[0xff44],'command':last_command,'current_song':read('CurrentSong'),'function_counts':{}}

def count_function(name):
    if current_update is not None:
        key=f'{name}:channel-{p.register_file.C}'
        counts=current_update['function_counts']
        counts[key]=counts.get(key,0)+1

def end_update(context):
    global current_update,last_update,worst_update,first_vblank_window_miss
    if current_update is None:
        return
    current_update['divider_end']=p.memory[0xff04]
    current_update['core_exit_scanline']=read('AudioExitLY')
    delta=(current_update['divider_end']-current_update['divider_start'])&255
    current_update['divider_tick_delta']=delta
    current_update['approximate_cpu_clock_lower_bound']=max(0,(delta-1)*256)
    current_update['approximate_cpu_clock_upper_bound']=(delta+1)*256
    last_update=current_update
    if worst_update is None or delta>worst_update['divider_tick_delta']:
        worst_update=current_update
    if first_vblank_window_miss is None and (current_update['core_exit_scanline']<144 or current_update['core_exit_scanline']>=152):
        first_vblank_window_miss=current_update
    current_update=None

def register_hook(symbol,callback,context):
    bank,address=locations[symbol]
    p.hook_register(bank,address,callback,context)
    registered_hooks.append(symbol)

def profile():
    return {'first_vblank_only_window_miss':first_vblank_window_miss,'worst_update_by_divider':worst_update,'last_update':last_update,'registered_hook_count':len(registered_hooks),'divider_measurements_quantized_and_modulo_65536':True}

def state():
    arrays={}
    for name in ('wChannelSoundIDs','wChannelFlags1','wChannelNoteSpeeds','wChannelNoteDelayCounters'):
        a=symbols[name]
        arrays[name]=list(p.memory[a:a+8])
    a=symbols['wChannelCommandPointers']
    arrays['channel_pointers']=[int.from_bytes(bytes(p.memory[a+i*2:a+i*2+2]),'little') for i in range(8)]
    registers={f'FF{address:02X}':p.memory[0xff00+address] for address in range(0x10,0x27)}
    return {'audio_ticks':read('AudioTicks',2),'current_song':read('CurrentSong'),'registers':registers,'software_channels':arrays,'valid_sample_frames':int(p.sound.ndarray.shape[0]),'timing':timing()}

def tick(n=1):
    assert p.tick(n,False,True)
    assert read('AudioFrameOverrun')==0,('Audio worker missed a frame deadline',timing())

def command(code,**values):
    global last_command
    for name,value in values.items():
        p.memory[symbols[name]]=value
    p.memory[symbols['Status']]=0
    p.memory[symbols['Command']]=code
    chunks=[]
    trace=[]
    last_command={'code':code,'values':values}
    for _ in range(12):
        tick()
        chunks.append(p.sound.ndarray.copy())
        trace.append(state())
        if read('Command')==0:
            assert read('Status')==1,(code,values,read('Status'))
            return chunks,trace
    raise AssertionError(('Audio command timed out',code,values))

def capture(name,frames,onset):
    global current_clip
    onset_chunks,onset_trace=onset
    chunks=list(onset_chunks)
    current_clip={'name':name,'command':last_command,'frames':list(onset_trace)}
    for _ in range(frames):
        tick()
        chunks.append(p.sound.ndarray.copy())
        current_clip['frames'].append(state())
    audio=np.concatenate(chunks)
    span=int(np.ptp(audio.astype(np.int16))) if audio.size else 0
    pcm=(audio.astype(np.int16)*256).astype('<i2')
    with wave.open(str(PREVIEWS/(name+'.wav')),'wb') as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(p.sound.sample_rate)
        output.writeframes(pcm.tobytes())
    current_clip['sample_frames']=int(len(audio))
    current_clip['peak_to_peak']=span
    assert audio.size and span>0,('Silent output including command frames',name)
    return {'name':name,'sample_frames':len(audio),'seconds':len(audio)/p.sound.sample_rate,'peak_to_peak':span,'command_frames_captured':len(onset_chunks)}

try:
    register_hook('AudioWorker',begin_update,None)
    register_hook('AudioWorker.timingSpanReady',end_update,None)
    functions=('PlayNextNote','GetNextMusicByte','PlaySound','MultiplyAdd','CalculateFrequency','InitPitchSlideVars')
    for bank in range(24,30):
        for function in functions:
            register_hook(f'Bank{bank}_Audio1_{function}',count_function,function)
        register_hook(f'Bank{bank}_Audio1_InitPitchSlideVars.divideLoop',count_function,'pitch-slide-subtraction-iteration')
    for _ in range(240):
        tick()
        if read('Ready')==0xa5:
            break
    else:
        raise AssertionError('Audio bench did not boot')
    for song,title in enumerate(assets['tracks']):
        onset=command(1,Song=song)
        assert read('CurrentSong')==song
        before=read('AudioTicks',2)
        results.append(capture('music-'+title.lower().replace(' ','-'),180,onset))
        elapsed=(read('AudioTicks',2)-before)&65535
        assert 175<=elapsed<=185,('Audio update cadence',title,elapsed)
    for name in ('button','spin','stop','reward','denied'):
        command(4)
        onset=command(2,Sound=assets['sound_ids'][name])
        results.append(capture('effect-'+name,90,onset))
    for species,name in enumerate(assets['species']):
        command(4)
        onset=command(3,Species=species)
        results.append(capture('cry-'+name,240,onset))
        a=symbols['wChannelSoundIDs']
        assert not any(p.memory[a+4:a+8]),('Cry did not finish',name)
    assert read('AudioFrameOverrun')==0,('Audio worker missed a frame deadline',timing())
    assert read('AudioLateEntries',2)==0,('Scheduling interrupt started late',timing())
    outstanding=(read('AudioFrameRequests',2)-read('AudioTicks',2))&65535
    assert outstanding<=1,('Audio updates fell behind frame requests',timing())
    report={'non_silent_assets_checked':len(results),'clips':results,'command_frame_sampling_enabled':True,'update_cadence_checked':True,'no_missed_frame_updates':True,'vblank_budget_passed':read('AudioBudgetExceeded')==0,'vblank_only_limit_is_diagnostic_not_playback_pass_criterion':True,'timing':timing(),'update_profile':profile(),'cabinet_integration_complete':False,'cabinet_graphics_dma_safety_verified':False,'human_listening_approval':False}
    (OUT/'native-audio-report.json').write_text(json.dumps(report,indent=2))
    (PREVIEWS/'README.txt').write_text('NATIVE AUDIO PREVIEWS - NOT A PLAYABLE CABINET UPDATE\nThese clips are recorded from a standalone audio ROM. VBlank requests one update per frame; a foreground worker runs the native interpreter.\nPassing verifies non-silent output, update cadence and no missed frame updates. The former VBlank-only fit measurement remains in the report and may be false.\nPassing DOES NOT verify cabinet graphics/DMA compatibility, the music selector, automatic playlist or payout-triggered cries. Those require a separate integrated build.\nMusic clips are excerpts. Six tracks, five effects and six species cries are included. Listening approval remains outstanding.\n')
    print(json.dumps(report,indent=2))
except Exception as error:
    debug={'error_type':type(error).__name__,'error':str(error),'last_command':last_command,'completed_clips':results,'update_profile':profile(),'current_clip':current_clip,'final_state':state(),'tests_passed':False}
    (OUT/'audio-debug.json').write_text(json.dumps(debug,indent=2))
    print('AUDIO FAILURE SUMMARY:\n'+json.dumps({'error':str(error),'timing':timing(),'update_profile':profile(),'last_command':last_command},indent=2))
    raise
finally:
    p.stop(save=False)
