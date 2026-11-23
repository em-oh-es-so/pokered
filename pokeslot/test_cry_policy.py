from itertools import product
import json
from cry_policy import MACHINE,OUT,OFF,EVERY_WIN,BIG_WINS_ONLY,DEFAULT_MODE,classify,assess_win,pack,build_tables

def reference(stops,bet,lines):
    totals=[0]*6
    five=False
    grid=[[MACHINE['reels'][r][(stops[r]+row)%6] for row in range(3)] for r in range(5)]
    for line in MACHINE['paylines'][:lines]:
        species=grid[0][line[0]]
        matched=1
        for reel in range(1,5):
            if grid[reel][line[reel]]!=species:
                break
            matched+=1
        if matched>=3:
            totals[species]+=MACHINE['paytable'][species][matched-3]*bet
            five|=matched==5
    payout=sum(totals)
    best=next((i for i,v in enumerate(totals) if v==max(totals)),None) if payout else None
    return totals,five,best,bool(payout and (payout>=5*bet*lines or five))

assert DEFAULT_MODE==BIG_WINS_ONLY
assert not classify([124,0,0,0,0,0],False,25)['eligible']
assert classify([125,0,0,0,0,0],False,25)['eligible']
assert classify([126,0,0,0,0,0],False,25)['eligible']
assert classify([1,0,0,0,0,0],True,25)['eligible']
assert not classify([0]*6,False,25,EVERY_WIN)['eligible']
assert not classify([125,0,0,0,0,0],True,25,OFF)['eligible']
assert classify([0,10,10,0,0,0],False,25,EVERY_WIN)['cry_species']==1
assert classify([60,50,0,0,0,0],False,25,EVERY_WIN)['cry_species']==0
manifest=build_tables()
checked=0
mode_cases=0
scaling_cases=0
settings_cases=0
qualifying=0
ties=0
for table in manifest['tables']:
    lines=table['active_lines']
    data=(OUT/table['filename']).read_bytes()
    for index,stops in enumerate(product(range(6),repeat=5)):
        totals,five,best,big=reference(stops,1,lines)
        actual=assess_win(stops,1,lines)
        assert actual['contributions']==totals,(stops,lines)
        assert actual['highest_contributing_species']==best
        assert actual['paying_five_of_a_kind']==five
        assert actual['big_win']==big
        expected=(7 if best is None else best)|(8 if big else 0)
        assert data[index]==expected==pack(actual)
        assert data[index]&0xf0==0
        qualifying+=big
        ties+=bool(best is not None and totals.count(max(totals))>1)
        for mode in (OFF,EVERY_WIN,BIG_WINS_ONLY):
            decision=classify(totals,five,lines,mode)
            eligible=bool(sum(totals) and (mode==EVERY_WIN or (mode==BIG_WINS_ONLY and big)))
            assert decision['eligible']==eligible
            assert decision['cry_species']==(best if eligible else None)
            mode_cases+=1
        for bet in MACHINE['bets_per_line']:
            scaled=classify([value*bet for value in totals],five,bet*lines)
            assert scaled['highest_contributing_species']==best and scaled['big_win']==big
            scaling_cases+=1
        if index%127==0 or index==7775:
            for bet in MACHINE['bets_per_line']:
                rt,rf,rb,rq=reference(stops,bet,lines)
                full=assess_win(stops,bet,lines)
                assert full['contributions']==rt and full['paying_five_of_a_kind']==rf
                assert full['highest_contributing_species']==rb and full['big_win']==rq
                settings_cases+=1
        checked+=1
report={'checkpoint':'Offline cry qualification and selection audit','policy_tests_passed':True,'outcome_and_line_setting_records_checked':checked,'mode_classification_cases_checked':mode_cases,'positive_bet_scaling_cases_checked':scaling_cases,'additional_full_engine_bet_cases_checked':settings_cases,'big_win_records':qualifying,'highest_contribution_tie_records':ties,'boundary_and_five_of_a_kind_tests_passed':True,'packed_table_bytes_checked':checked,'all_tables_fit_individually_in_one_rom_bank':all(t['bytes']<=16384 for t in manifest['tables']),'cabinet_modified':False,'runtime_cry_trigger_verified':False,'payout_cry_sequencing_verified':False,'audible_cries_enabled':False}
assert checked==6*7776
(OUT/'cry-policy-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
