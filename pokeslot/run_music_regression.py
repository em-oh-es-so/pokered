from pathlib import Path
import json
import os
import re
import sys

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/music-cabinet'
suite=sys.argv[1]
paths={'play':HERE/'build/play/test_play_with_wins.py','speed':HERE/'test_speed_rom.py','wins':HERE/'test_wins_rom.py'}
path=paths[suite]
os.environ['MUSIC_SUITE']=suite
source=path.read_text()
old='from pyboy import PyBoy'
assert source.count(old)==1
source=source.replace(old,'from music_cabinet_guard import GuardedPyBoy as PyBoy')
source=source.replace('build/play','build/music-cabinet')
source=re.sub(r"('audio_implemented'\s*:\s*)False",r'\g<1>True',source)
try:
    exec(compile(source,str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
    report_path=OUT/f'music-{suite}-report.json'
    report=json.loads(report_path.read_text())
    if suite in ('play','speed'):
        assert report['moving_frames_with_exact_music_cadence']>0
    report['suite_passed']=True
    report_path.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
except Exception as error:
    (OUT/f'music-{suite}-failure.json').write_text(json.dumps({'suite':suite,'suite_passed':False,'error':str(error)},indent=2))
    raise
