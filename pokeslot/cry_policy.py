from pathlib import Path
from itertools import product
import hashlib
import json
from rules.engine import MACHINE, evaluate_grid, grid_from_stops, settings

OFF=0
EVERY_WIN=1
BIG_WINS_ONLY=2
DEFAULT_MODE=BIG_WINS_ONLY
SYMBOLS=MACHINE['symbols']
OUT=Path(__file__).resolve().parent/'build/cry-policy'

def classify(contributions,paying_five,cost,mode=DEFAULT_MODE):
    if mode not in (OFF,EVERY_WIN,BIG_WINS_ONLY):
        raise ValueError('Unsupported cry mode')
    if len(contributions)!=6 or any(type(x) is not int or x<0 for x in contributions):
        raise ValueError('Expected six non-negative integer contributions')
    if type(cost) is not int or cost<=0:
        raise ValueError('Spin cost must be a positive integer')
    payout=sum(contributions)
    species=max(range(6),key=lambda i:contributions[i]) if payout else None
    big=bool(payout and (payout>=5*cost or paying_five))
    eligible=bool(payout and (mode==EVERY_WIN or (mode==BIG_WINS_ONLY and big)))
    return {'cost':cost,'gross_payout':payout,'contributions':list(contributions),'highest_contributing_species':species,'paying_five_of_a_kind':bool(paying_five),'big_win':big,'eligible':eligible,'cry_species':species if eligible else None}

def assess_win(stops,bet=1,active_lines=25,mode=DEFAULT_MODE):
    cost=settings(bet,active_lines)
    wins=evaluate_grid(grid_from_stops(stops),bet,active_lines)
    contributions=[0]*6
    for win in wins:
        contributions[SYMBOLS.index(win['symbol'])]+=win['amount']
    return classify(contributions,any(win['matched']==5 for win in wins),cost,mode)

def pack(result):
    species=result['highest_contributing_species']
    return (7 if species is None else species)|(8 if result['big_win'] else 0)

def build_tables():
    assert MACHINE['reels']==[list(range(6))]*5
    OUT.mkdir(parents=True,exist_ok=True)
    tables=[]
    for index,lines in enumerate(MACHINE['line_counts']):
        data=bytes(pack(assess_win(stops,1,lines)) for stops in product(range(6),repeat=5))
        assert len(data)==7776
        name=f'cry-lines-{lines}.bin'
        (OUT/name).write_bytes(data)
        tables.append({'line_index':index,'active_lines':lines,'filename':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    manifest={'checkpoint':'Cry decision data only; not wired into cabinet playback','default_mode':DEFAULT_MODE,'modes':{'off':OFF,'every_win':EVERY_WIN,'big_wins_only':BIG_WINS_ONLY},'big_win_gross_cost_multiplier':5,'paying_five_of_a_kind_also_qualifies':True,'species_selection':'Largest sum of paying-line amounts for that species','tie_break':'First species in the existing machine symbol order','species_order':SYMBOLS,'table_index':'Five stop indices interpreted as a base-six number, left reel first','encoding':'Bits 0-2: species 0-5, or 7 for no paying species. Bit 3: qualifies for Big Wins Only. Other bits zero.','bet_independence':'Positive bet multiplies all contributions and spin cost equally','tables':tables,'cabinet_modified':False,'runtime_cry_trigger_verified':False,'audible_cries_enabled':False}
    (OUT/'cry-policy-manifest.json').write_text(json.dumps(manifest,indent=2))
    return manifest

if __name__=='__main__':
    print(json.dumps(build_tables(),indent=2))
