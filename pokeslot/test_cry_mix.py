from pathlib import Path
import json
import runpy
import music_cabinet_guard

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/music-cabinet'
BaseGuard=music_cabinet_guard.GuardedPyBoy

class CryMixGuard(BaseGuard):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.mix_checks=0
        self.restore_checks=0
        self._p.hook_register(0,self.sym['CabinetCryMix.end'],self.check_mix,None)
        self._p.hook_register(0,self.sym['CabinetCryRestoreWave.done'],self.check_restore,None)

    def check_mix(self,context):
        assert self.read('CabinetCryActive')
        assert self._p.memory[0xff24]&0x77==0x44,'Cry-time master volume incorrect'
        assert not self._p.memory[self.sym['wChannelSoundIDs']+6]
        normal=self._p.memory[self.sym['wChannelVolumes']+2]&0x60
        expected={0x00:0x00,0x20:0x40,0x40:0x60,0x60:0x60}[normal]
        assert self._p.memory[0xff1c]&0x60==expected,'Backing wave not ducked to the intended level'
        self.mix_checks+=1

    def check_restore(self,context):
        assert not self.read('CabinetCryActive')
        assert self._p.memory[0xff24]&0x77==self.read('CabinetCrySavedVolume')&0x77,'Master volume not restored'
        normal=self._p.memory[self.sym['wChannelVolumes']+2]&0x60
        assert self._p.memory[0xff1c]&0x60==normal,'Music wave volume not restored'
        self.restore_checks+=1

    def stop(self,save=False):
        try:
            assert self.mix_checks>0 and self.restore_checks>0,'Mix checks did not exercise cry playback and restoration'
            result={'mix_register_checks_passed':True,'active_cry_mix_checks':self.mix_checks,'post_cry_restore_checks':self.restore_checks,'duck_does_not_accumulate_across_frames':True,'native_pitch_duration_presets_checked_by_cry_suite':True,'perceived_balance_approved':False}
            (OUT/'cry-mix-report.json').write_text(json.dumps(result,indent=2))
        finally:
            super().stop(save=save)

music_cabinet_guard.GuardedPyBoy=CryMixGuard
runpy.run_path(str(HERE/'test_cabinet_cries.py'),run_name='__main__')
