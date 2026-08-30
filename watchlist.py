# -*- coding: utf-8 -*-
"""WATCHLIST tự quản — Nguyễn Sơn Invest
Mỗi lần chạy: chấm lại toàn bộ thị trường, loại mã hết đạt, thêm mã mới đạt,
giữ nguyên các mã anh Sơn ghim thủ công (pinned) kèm lý do nếu chúng không còn đạt."""
import json, os, datetime as dt
from screener import screen, SEED, LOAI, WL

STATE='data/watchlist_state.json'

def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {'pinned':SEED, 'members':{}, 'log':[]}

def save_state(s): json.dump(s, open(STATE,'w'), ensure_ascii=False, indent=1)

def refresh(max_size=40):
    st=load_state()
    r=screen()
    # ghim.txt la nguon su that cho danh sach ghim — file thang the state cu
    st['pinned']=list(SEED)
    # loai.txt thang tat ca: ma bi loai thi ra khoi ca ghim lan thanh vien
    if LOAI:
        st['pinned']=[x for x in st['pinned'] if x not in LOAI]
        for sym in [x for x in st['members'] if x in LOAI]:
            del st['members'][sym]
    idx={x['sym']:x for x in r['rows']}
    today=r['asof']
    fit={x['sym'] for x in r['watchlist']}
    added=[]; removed=[]; kept=[]
    # loai
    for sym in list(st['members']):
        if sym in fit: kept.append(sym); continue
        x=idx.get(sym)
        why = (x['block'] if x and x['blocked'] else
               ('điểm %.0f < %d'%(x['score'],WL['min_score']) if x and x['score'] is not None and x['score']<WL['min_score'] else
                ('nền %.1f%% > %d%%'%(x['base'],WL['max_base_range']*100) if x and x['base'] and x['base']>WL['max_base_range']*100 else
                 ('GTGD %.0f tỷ < %d tỷ'%(x['gtgd20'],WL['min_gtgd20']/1e9) if x and x.get('gtgd20') is not None and x['gtgd20']<WL['min_gtgd20']/1e9 else
                  'không còn đạt ngưỡng'))))
        if sym in st['pinned']:
            st['members'][sym]['status']='ghim'; st['members'][sym]['note']=why; kept.append(sym); continue
        removed.append({'sym':sym,'why':why,'score':x['score'] if x else None})
        del st['members'][sym]
    # them
    for x in r['watchlist']:
        if x['sym'] in st['members']: 
            st['members'][x['sym']].update({'score':x['score'],'status':'đạt','note':''})
            continue
        if len(st['members'])>=max_size and x['sym'] not in st['pinned']: continue
        st['members'][x['sym']]={'added':today,'score':x['score'],'status':'đạt','note':''}
        added.append({'sym':x['sym'],'score':x['score'],'sector':x['sector'],'base':x['base'],'rs':x['rs']})
    # ghim ma chua co
    for s in st['pinned']:
        if s not in st['members'] and s in idx:
            x=idx[s]
            st['members'][s]={'added':today,'score':x['score'],'status':'ghim',
                              'note': x['block'] if x['blocked'] else 'chưa đạt ngưỡng'}
    st['log'].insert(0, {'date':today,'added':[a['sym'] for a in added],
                         'removed':[a['sym'] for a in removed],'size':len(st['members'])})
    st['log']=st['log'][:60]
    save_state(st)
    detail=[]
    for sym,meta in st['members'].items():
        x=idx.get(sym,{})
        detail.append({**{k:x.get(k) for k in ('sym','sector','price','score','fund','tech','base','rs',
                        'gtgd20','ordimb20','roe','rev_yoy','npat_yoy','icr','de','from_high','quarter',
                        'blocked','block','grade_score','grade_base','mktcap')}, **meta, 'sym':sym})
    detail.sort(key=lambda x:(x['status']!='đạt', -(x['score'] or -1)))
    out={'asof':today,'added':added,'removed':removed,'members':detail,
         'universe':r['n'],'n_fit':len(r['watchlist']),'rules':WL,'pinned':st['pinned']}
    json.dump(out, open('data/watchlist.json','w'), ensure_ascii=False)
    return out

if __name__=='__main__':
    o=refresh()
    print(f"WATCHLIST {o['asof']}  |  {len(o['members'])} mã  |  quét {o['universe']} mã, {o['n_fit']} đạt chuẩn")
    print(f"\n+ THÊM ({len(o['added'])}): "+', '.join(f"{a['sym']}({a['score']})" for a in o['added']) if o['added'] else '\n+ THÊM: không có')
    print(f"- LOẠI ({len(o['removed'])}): "+', '.join(f"{a['sym']} — {a['why']}" for a in o['removed']) if o['removed'] else '- LOẠI: không có')
    print(f"\n{'MÃ':6s}{'Điểm':>6s}{'CB':>4s}{'Nền%':>7s}{'RS':>6s}{'GTGD':>7s}{'DòngTiền':>9s}  {'Hạng':10s} {'Trạng thái':12s} Ghi chú")
    for x in o['members']:
        print(f"{x['sym']:6s}{x['score'] or 0:6.1f}{x['fund'] or 0:4d}{x['base'] or 0:7.1f}{x['rs'] or 0:6.1f}"
              f"{x['gtgd20'] or 0:7.1f}{x['ordimb20'] or 0:9.2f}  {(x['grade_score'] or '')+'/'+(x['grade_base'] or ''):10s} "
              f"{x['status']:12s} {x['note'] or ''}")
