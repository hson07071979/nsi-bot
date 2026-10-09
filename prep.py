"""Chuẩn hoá dữ liệu: ma trận giá + bảng cơ bản theo ngày công bố (không nhìn trước)."""
import json, numpy as np, datetime as dt, os

def to_date(ts): return dt.datetime.utcfromtimestamp(ts).date()

def build():
    prices=json.load(open('data/prices_raw.json'))
    uni=json.load(open('data/universe.json'))
    ex=json.load(open('data/exchange.json'))
    prices={s:prices[s] for s in uni if s in prices}
    cal=sorted({t for d in prices.values() for t in d['t']})
    caldates=[to_date(t) for t in cal]
    idx={t:i for i,t in enumerate(cal)}
    S=sorted(prices); N=len(cal); M=len(S)
    O=np.full((N,M),np.nan); H=O.copy(); L=O.copy(); C=O.copy(); V=np.zeros((N,M))
    for j,s in enumerate(S):
        d=prices[s]
        ii=np.array([idx[t] for t in d['t']])
        O[ii,j]=d['o']; H[ii,j]=d['h']; L[ii,j]=d['l']; C[ii,j]=d['c']; V[ii,j]=d['v']
    return dict(sym=S,cal=cal,dates=caldates,O=O,H=H,L=L,C=C,V=V,exch={s:ex.get(s,'HOSE') for s in S})

def qend(y,q): return dt.date(y,[3,6,9,12][q-1], [31,30,30,31][q-1])

def parse_funda(path='data/funda_raw.json'):
    raw=json.load(open(path))
    out={}
    for s,d in raw.items():
        recs={}
        phan={}          # (y,q) -> {'ratio','is','cf'}: phan nao cua quy da ve
        pub_is={}        # (y,q) -> ngay cong bo KQKD THO (chua qua chot chan)
        for r in d.get('ratio',[]):
            y=int(r.get('yearReport') or r.get('year') or 0); q=r.get('quarter')
            if not y or not q or int(q) not in (1,2,3,4): continue
            q=int(q)
            phan.setdefault((y,q),set()).add('ratio')
            recs[(y,q)]={'marketCap':r.get('marketCap'),'de':r.get('debtToEquity'),
                'roe':r.get('roe'),'ebit':r.get('ebit'),'npl':r.get('npl'),'car':r.get('car'),
                'pe':r.get('pe'),'ps':r.get('ps'),'pcf':r.get('priceToCashFlow'),
                'atm':r.get('afterTaxProfitMargin'),'pb':r.get('pb')}
        pub={}
        for r in d.get('is',[]):
            y=r.get('yearReport'); lr=r.get('lengthReport')
            if not y or lr not in (1,2,3,4): continue
            k=(int(y),int(lr))
            recs.setdefault(k,{})
            phan.setdefault(k,set()).add('is')
            rev = (r.get('isa3') or r.get('isb38') or r.get('isb27')
                   or r.get('isi103') or r.get('iss141'))   # DN thuong / ngan hang / bao hiem / chung khoan
            # LNST CUA CO DONG CONG TY ME (isa22) truoc, khong phai LNST tong (isa20).
            # Chu C trong CANSLIM la tang truong EPS, ma EPS tinh tren phan cua co dong
            # cong ty me. Cac trang tai chinh (CafeF, Vietstock) cung cong bo so nay —
            # dung isa20 thi bang tren web lech han voi moi noi khac. Vi du FPT quy
            # 1/2025: tong 2.596 ty nhung phan cong ty me chi 2.174 ty, chenh 19%.
            # Do A/B: +540,5% -> +536,0%, DD 12,65% -> 11,97%. Chenh trong pham vi nhieu,
            # va ban dung dinh nghia lai cho sut giam nho hon.
            npat = r.get('isa22') or r.get('isa20')
            recs[k].update({'rev':rev,'npat':npat,'npat_p':r.get('isa22'),
                            'intexp':r.get('isa8'),'other':r.get('isa14'),'pretax':r.get('isa16')})
            p=r.get('publicDate')
            if p: pub[k]=p[:10]; pub_is[k]=p[:10]
        for r in d.get('cf',[]):
            y=r.get('yearReport'); lr=r.get('lengthReport')
            if not y or lr not in (1,2,3,4): continue
            k=(int(y),int(lr)); recs.setdefault(k,{})
            phan.setdefault(k,set()).add('cf')
            recs[k]['cfo']=r.get('cfa18')
            p=r.get('publicDate')
            if p and k not in pub: pub[k]=p[:10]
        rows=[]
        for (y,q),v in sorted(recs.items()):
            pd_=pub.get((y,q))
            if pd_: avail=dt.date(*map(int,pd_.split('-')))
            else: avail=qend(y,q)+dt.timedelta(days=45)
            # ---- CHOT CHAN NHIN TRUOC (Lop 0.5 — toan ven du lieu) ----
            # Nguon doi khi tra ve ngay cong bo VO LY: CAP 2023Q1 ghi cong bo
            # 31/01/2023 trong khi quy do phai den 31/03/2023 moi ket thuc. Tin
            # theo con so do la cho bo may doc bao cao TRUOC KHI no ton tai —
            # dung loai nhin truoc am tham nhat, vi no khong bao loi, no chi lam
            # backtest dep len. Day ngay dung ve moc som nhat co the tin duoc.
            som_nhat = qend(y,q)+dt.timedelta(days=45)
            if avail < som_nhat: avail = som_nhat
            v=dict(v); v['y']=y; v['q']=q; v['avail']=avail
            v['phan']=sorted(phan.get((y,q),()))
            if pub_is.get((y,q)): v['pub_is']=pub_is[(y,q)]
            rows.append(v)
        out[s]=cho_du_phan(rows)
    return out


# ---------------- QUY MOI PHAI DU PHAN (anh Son duyet 09/10/2026) ----------------
# Vietcap tra ba phan RIENG: KQKD, luu chuyen tien te, bang chi so (ROE, D/E, EBIT).
# Truoc day ma nao co KQKD quy moi la bo may chuyen ngay sang quy do, ke ca khi
# hai phan kia chua ve -> mat ROE (tut 10 diem A2), mat EBIT/D-E (cong ICR, D/E
# bi bo qua), CFO 4 quy chi cong 3 quy (cong CFO co the lat). Gio:
#   * quy MOI NHAT chua co KQKD (chi co bang chi so / LCTT) -> chua dung quy do
#   * co KQKD nhung thieu phan ma quy truoc CO -> giu quy cu toi da CHO_DU_PHAN
#     ngay ke tu ngay cong bo KQKD; qua han thi nhan voi phan dang co, gan
#     'thieu_phan' de trang web canh bao
# Chi dung toi QUY MOI NHAT cua tung ma: lich su backtest (cac quy da du phan tu
# lau) khong doi.
CHO_DU_PHAN = 15

def cho_du_phan(rows):
    rows=list(rows)
    # quy moi nhat chua co KQKD: khong co gi de cham diem tang truong -> bo
    while rows and 'is' not in rows[-1].get('phan',()):
        rows.pop()
    if len(rows)<2: return rows
    moi, cu = rows[-1], rows[-2]
    can = {'is'} | (set(cu.get('phan',())) & {'cf','ratio'})
    thieu = sorted(can - set(moi.get('phan',())))
    if thieu:
        moi=dict(moi)
        moi['thieu_phan']=thieu
        goc = (dt.date(*map(int,moi['pub_is'].split('-'))) if moi.get('pub_is') else moi['avail'])
        moi['avail']=max(moi['avail'], goc+dt.timedelta(days=CHO_DU_PHAN))
        rows[-1]=moi
    return rows
