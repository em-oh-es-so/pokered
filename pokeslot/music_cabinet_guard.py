from pathlib import Path
import json
import os
import numpy as np
from pyboy import PyBoy

OUT=Path(__file__).resolve().parent/'build/music-cabinet'

class GuardedPyBoy:
    def __init__(self,rom,**kwargs):
        kwargs.update(sound_emulated=True,sound_sample_rate=24000)
        self._p=PyBoy(rom,**kwargs)
        self.sym={}
        symbol_name='play.sym' if Path(rom).name=='pokeslot-play.gbc' else Path(rom).with_suffix('.sym').name
        for line in (Path(rom).parent/symbol_name).read_text().splitlines():
            parts=line.split()
            if len(parts)==2 and ':' in parts[0] and not parts[0].startswith(';'):
                self.sym[parts[1]]=int(parts[0].split(':')[1],16)
        self.frames=0
        self.moving_cadence_frames=0
        self.verified_reels=0
        self.peak=0
        self.armed=False
        self.deltas={}
        self.normal=[(OUT/f'reel-{r}-0.bin').read_bytes()+(OUT/f'reel-{r}-1.bin').read_bytes() for r in range(5)]
        self.negative=[(OUT/f'negative-{r}.bin').read_bytes() for r in range(5)]
        self._p.hook_register(0,self.sym['PaintAll'],self.check_reels,None)

    def __getattr__(self,name):
        return getattr(self._p,name)

    def read(self,name,n=1):
        a=self.sym[name]
        return int.from_bytes(bytes(self._p.memory[a:a+n]),'little')

    def check_reels(self,context):
        if self.read('CabinetAudioInitialized')!=0xa5:
            return
        for reel in range(5):
            size=self._p.memory[self.sym['TileCounts']+reel]*16
            bank=self._p.memory[self.sym['VRAMBanks']+reel]
            tile=self._p.memory[self.sym['Visible']+reel]
            phase=self._p.memory[self.sym['Phases']+reel]
            if self.read('WinPhase') and reel<self.read('WinMatched'):
                row=self._p.memory[self.sym['WinRows']+reel]
                frame=(phase//6)*3+row
                expected=self.negative[reel][frame*size:(frame+1)*size]
            else:
                expected=self.normal[reel][phase*size:(phase+1)*size]
            address=0x8000+tile*16
            actual=bytes(self._p.memory[bank,address:address+size])
            assert len(expected)==size and actual==expected,('Reel DMA data mismatch',reel,phase,bank,tile)
            self.verified_reels+=1

    def tick(self,n=1,render=True,sound=True):
        for _ in range(n):
            ready=self.read('GameReady')==0xa5
            moving=bool(self.read('SpinActive'))
            before=self.read('CabinetAudioTicks',2)
            assert self._p.tick(1,render,True)
            self.frames+=1
            if self.read('GameReady')!=0xa5:
                continue
            assert self.read('CabinetAudioInitialized')==0xa5
            assert self.read('CabinetAudioLate')==0,'Audio interrupt entered late'
            assert self.read('CabinetAudioDeadlineMiss')==0,'Audio crossed into VBlank drawing time'
            if not self.armed:
                self._p.memory[1,0xdf00:0xdf40]=[0xa5]*64
                self.armed=True
                rom=Path(self._p_ignored_rom).read_bytes() if False else None
            assert bytes(self._p.memory[1,0xdf00:0xdf40])==bytes([0xa5]*64),'Stack crossed guard region'
            delta=(self.read('CabinetAudioTicks',2)-before)&65535
            if ready:
                self.deltas[str(delta)]=self.deltas.get(str(delta),0)+1
            if ready and moving and self.read('SpinActive'):
                assert delta==1,('Music cadence changed while reels moved',delta)
                self.moving_cadence_frames+=1
            audio=self._p.sound.ndarray
            if audio.size:
                self.peak=max(self.peak,int(np.ptp(audio.astype(np.int16))))
        return True

    def stop(self,save=False):
        try:
            assert self.armed and self.peak>0,'No non-silent cabinet music recorded'
            assert self.verified_reels>0,'No rendered reel buffers checked'
            suite=os.environ['MUSIC_SUITE']
            result={'suite':suite,'suite_passed':False,'guard_checks_reached_end':True,'emulated_frames':self.frames,'reel_buffers_byte_checked':self.verified_reels,'moving_frames_with_exact_music_cadence':self.moving_cadence_frames,'audio_peak_to_peak':self.peak,'audio_ticks':self.read('CabinetAudioTicks',2),'maximum_audio_scanline_span':self.read('CabinetAudioMaximumSpan'),'late_audio_interrupt':self.read('CabinetAudioLate'),'audio_deadline_miss':self.read('CabinetAudioDeadlineMiss'),'stack_guard_preserved':True,'frame_update_delta_histogram_including_lcd_transitions':self.deltas,'manual_delta_playtest_complete':False,'human_listening_approval':False}
            (OUT/f'music-{suite}-report.json').write_text(json.dumps(result,indent=2))
        finally:
            self._p.stop(save=save)
