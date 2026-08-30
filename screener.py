# -*- coding: utf-8 -*-
"""BỘ LỌC CỔ PHIẾU + WATCHLIST — Nguyễn Sơn Invest
Chấm mọi mã trong vũ trụ theo CANSLIM + cơ bản + chất lượng nền, rồi chọn watchlist.
Tiêu chí watchlist cố tình để mức VỪA (không quá chặt) để không bỏ lỡ deal."""
import json, numpy as np, datetime as dt
import engine2 as E
from engine import risk_gate, canslim_score, as_of, BANKS, BROKERS, INSUR

from manual import ghim as _ghim, loai as _loai

# Hai danh sach thu cong cua anh Son, doc tu ghim.txt va loai.txt o goc repo.
# Doc MOT LAN luc nap module — mot lan chay screener la mot anh chup.
SEED = _ghim()          # ma ghim: luon giu trong watchlist
LOAI = _loai()          # ma loai: khong bao gio vao watchlist, khong bao gio keu chuong

# ⚠️ CAC NGUONG NAY PHAI TRUNG KHOP VOI `lookup.py` VA KHOI `PROD` TRONG `produce2.py`.
# Truoc day watchlist noi long hon (nen 25%, diem 40) nen sinh ra mau thuan: MWG nam
# trong watchlist va xep hang cao, nhung o tra cuu lai bao "chua tao duoc nen gia chat"
# vi bot doi nen <= 18%. Mot ma hoac dang CHO DIEM MUA, hoac khong — khong the vua
# trong watchlist vua khong du dieu kien.
WL = dict(
    min_score      = 45,         # = score_floor cua bot — NGUONG MUA, khong doi
    fa_score_lo    = 40,         # nhom "chua dat co ban": 40 <= diem < 45, DE RIENG
    min_mktcap     = 1000e9,
    min_gtgd20     = 15e9,       # = gtgd_min cua bot
    use_top_liquid = True,
    top_n          = 110,        # = top_n cua bot
    max_base_range = 0.18,       # = base_range cua bot
    min_volat      = 0.015,      # = volat_min cua bot
    min_rs         = 0,          # bot khong chan theo RS, chi hien de tham khao
    max_from_high  = -0.99,      # bot khong chan theo khoang cach dinh
    allow_yellow   = True,       # co vang (ICR 1,5-2,5) van vao, chi danh dau
)

def grade(x, cuts, labels):
    for c,l in zip(cuts,labels):
        if x is not None and x>=c: return l
    return labels[-1]

def screen(as_of_date=None):
    d,I,tls,sect = E.load()
    S=[str(x) for x in d['sym']]; cal=d['cal']; i=len(cal)-1
    day = as_of_date or dt.date.fromisoformat(str(cal[i]))
    AC=d['AdjClose']; PX=d['PriceClose']; MC=d['MarketCap']; TV=d['TotalValue']
    base_rng=(I['base_hi']-I['base_lo'])/np.where(I['base_lo']>0,I['base_lo'],np.nan)
    # dong tien trung binh 20 phien
    ordimb=I['ordimb']
    oi20=np.nanmean(ordimb[max(0,i-19):i+1],axis=0)
    # VU TRU: chi TOP 100 ma thanh khoan nhat (xep hang theo GTGD binh quan 20 phien
    # cua CHINH phien dang xet). Dong bo voi bot: bot chi giao dich trong nhom nay.
    from vn300 import build_topn
    TOPN = build_topn(I, WL.get('top_n', 110))[i]
    rows=[]
    for j,s in enumerate(S):
        if np.isnan(AC[i,j]) or I['nbars'][i,j]<250: continue
        if WL.get('use_top_liquid', True) and not TOPN[j]: continue
        mc=float(MC[i,j]) if MC[i,j]==MC[i,j] else None
        tl=tls.get(s); f=as_of(tl,day) if tl else None
        if f is None:
            rows.append(dict(sym=s,sector=sect.get(s,'Khác'),price=round(float(PX[i,j])/1000,2),
                mktcap=mc, score=None, blocked=True, block='Chưa có BCTC', wl=False)); continue
        blk,why,rmul=risk_gate(s,f)
        from_high=float(AC[i,j]/I['hi52'][i,j]-1) if I['hi52'][i,j]>0 else None
        sc,pts=canslim_score(f, I['rs'][i,j], I['mom3'][i,j], from_high,
                             float(I['volr'][i,j]), float(I['tvma20'][i,j]))
        br=float(base_rng[i,j]) if base_rng[i,j]==base_rng[i,j] else None
        rs=float(I['rs'][i,j]) if I['rs'][i,j]==I['rs'][i,j] else None
        gt=float(I['tvma20'][i,j]) if I['tvma20'][i,j]==I['tvma20'][i,j] else None
        oi=float(oi20[j]) if oi20[j]==oi20[j] else None
        # diem co ban rieng (thang 55): C1 C2 C3 A1 A2
        fund = (pts.get('C1',0)+pts.get('C2',0)+pts.get('C3',0)+pts.get('A1',0)+pts.get('A2',0))
        tech = sc-fund
        volat = float(I['volat20'][i,j]) if I['volat20'][i,j]==I['volat20'][i,j] else 0.0
        # Moi dieu kien TRU diem so. Tach ra de phan biet "truot vi diem" voi
        # "truot vi ky thuat / cong rui ro" — hai chuyen khac han nhau.
        # DK5 — bo may bo qua truong hop loi nhuan rong chi tang 0-25%. Phai co o
        # day nua, khong thi watchlist rong hon vu tru bot thuc su mua va o tra cuu
        # se noi khac watchlist (loi MWG cu, kieu khac).
        _npg = f.get('npat_yoy')
        dk5_ok = not (_npg is not None and 0 <= _npg < 0.25)
        khac_ok = (not blk) and dk5_ok and (mc or 0)>=WL['min_mktcap'] \
             and (gt or 0)>=WL['min_gtgd20'] and (br is not None and br<=WL['max_base_range']) \
             and volat>=WL['min_volat'] \
             and (rs or 0)>=WL['min_rs'] and (from_high is None or from_high>=WL['max_from_high'])
        # Quyen phu quyet cua anh Son: ma nam trong loai.txt bi gat khoi ca hai
        # nhom, du diem so co dep toi dau. Van giu trong bang de con thay minh
        # da tu bo cai gi.
        bi_loai = s in LOAI
        ok    = khac_ok and sc>=WL['min_score'] and not bi_loai                  # DUOC MUA
        fa_wl = khac_ok and (WL['fa_score_lo'] <= sc < WL['min_score']) and not bi_loai   # CHI DE MAT
        rows.append(dict(sym=s, sector=sect.get(s,'Khác'), price=round(float(PX[i,j])/1000,2),
            mktcap=round(mc/1e9) if mc else None,
            score=round(float(sc),1), fund=fund, tech=round(float(tech),1),
            pts=pts, rs=round(rs,1) if rs else None,
            gtgd20=round(gt/1e9,1) if gt else None,
            base=round(br*100,1) if br is not None else None,
            from_high=round(from_high*100,1) if from_high is not None else None,
            ordimb20=round(oi,2) if oi else None,
            roe=round(f.get('roe')*100,1) if f.get('roe') is not None else None,
            rev_yoy=round(f.get('rev_yoy')*100,1) if f.get('rev_yoy') is not None else None,
            npat_yoy=round(f.get('npat_yoy')*100,1) if f.get('npat_yoy') is not None else None,
            icr=round(f.get('icr'),2) if f.get('icr') is not None else None,
            de=round(f.get('de'),2) if f.get('de') is not None else None,
            quarter=f.get('label'),
            blocked=bool(blk), block=why if blk else '',
            warn=(rmul<1.0), wl=bool(ok), fa_wl=bool(fa_wl), loai=bool(bi_loai),
            tim=bool(f.get('tim')), tim_vi=f.get('tim_ly_do'),
            grade_score=grade(sc,[75,60,45,0],['Cao','Khá','Vừa','Thấp']),
            grade_base=grade(-(br or 9),[-0.12,-0.18,-0.25,-9],['Chặt','Khá chặt','Okay','Rộng']) if br is not None else 'Không rõ'))
    rows.sort(key=lambda r:(-(r['score'] or -1)))
    return dict(asof=str(cal[i]), n=len(rows), rows=rows,
                watchlist=[r for r in rows if r['wl']],
                fa_watchlist=[r for r in rows if r.get('fa_wl')],
                loai=sorted(LOAI), seed=SEED, rules=WL)

if __name__=='__main__':
    import sys
    r=screen()
    wl=r['watchlist']
    fa=r['fa_watchlist']
    print(f"Quet {r['n']} ma  |  danh sach mua: {len(wl)} ma  |  chua dat co ban (FA): {len(fa)} ma  |  phien {r['asof']}")
    _bl=[x for x in r['rows'] if x.get('loai')]
    print(f"Thu cong: ghim {len(SEED)} ma (ghim.txt) | loai {len(LOAI)} ma (loai.txt)"
          + (f" -> gat khoi watchlist: {' '.join(x['sym'] for x in _bl)}" if _bl else ""))
    if fa:
        print(f"\n--- CHUA DAT VE CO BAN (FA) — diem {WL['fa_score_lo']}-{WL['min_score']}, DE RIENG, khong vao danh sach mua ---")
        for x in fa:
            print(f"  {x['sym']:5s} diem {x['score']:5.1f} (co ban {x['fund']:2d}/55, ky thuat {x['tech']:5.1f}) "
                  f"nen {x['base'] or 0:5.1f}% RS {x['rs'] or 0:5.1f}  {x['sector'][:24]}")
    print('\n--- TOP 25 WATCHLIST ---')
    print(f"{'MA':5s} {'Diem':>5s} {'CB':>3s} {'KT':>5s} {'Nen%':>6s} {'RS':>5s} {'GTGD':>6s} {'DongTien':>8s} {'ROE%':>6s} {'DThu%':>7s}  Nganh")
    for x in wl[:25]:
        print(f"{x['sym']:5s} {x['score']:5.1f} {x['fund']:3d} {x['tech']:5.1f} {x['base'] or 0:6.1f} {x['rs'] or 0:5.1f} "
              f"{x['gtgd20'] or 0:6.1f} {x['ordimb20'] or 0:8.2f} {x['roe'] or 0:6.1f} {x['rev_yoy'] or 0:7.1f}  {x['sector'][:22]}")
    print('\n--- SEED cua anh Son ---')
    idx={x['sym']:x for x in r['rows']}
    for s in SEED:
        x=idx.get(s)
        if not x: print(f"  {s:5s}  KHONG CO trong vu tru"); continue
        st='✔ VAO watchlist' if x['wl'] else ('✗ '+(x['block'] or 'khong dat nguong'))
        print(f"  {s:5s} diem {x['score']} (CB {x['fund']}/55) nen {x['base']}% RS {x['rs']} GTGD {x['gtgd20']}ty  -> {st}")
    def _cv(o):
        import numpy as _np
        if isinstance(o,dict): return {k:_cv(v) for k,v in o.items()}
        if isinstance(o,list): return [_cv(x) for x in o]
        if isinstance(o,(_np.floating,_np.integer)): return float(o)
        if isinstance(o,_np.bool_): return bool(o)
        return o
    json.dump(_cv(r), open('data/screener.json','w'), ensure_ascii=False)
