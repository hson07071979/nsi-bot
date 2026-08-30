# -*- coding: utf-8 -*-
"""
NGUYEN SON INVEST - BOT GIAO DICH
Thi cong dung theo "KAFI - He Thong Giao Dich Hop Nhat v1.0"
Lop 0 -> Lop 9. Khong nhin truoc (fundamentals chi dung sau publicDate).
"""
import json, numpy as np, datetime as dt, math
from prep import build, parse_funda

BANKS = set("ACB BID CTG EIB HDB LPB MBB MSB NAB NVB OCB SHB SSB STB TCB TPB VAB VBB VCB VIB VPB ABB BAB KLB PGB SGB BVB".split())
BROKERS = set("SSI VND VCI HCM VIX SHS MBS BSI CTS FTS AGR VDS ORS APS PSI TVS TVB EVS IVS BVS DSC HBS VIG WSS APG".split())
INSUR = set("BVH BMI PVI PTI BIC MIG ABI PGI VNR".split())

# Nap tu data/sector2.json khi chay engine2 — dung de mien tru CFO cho nganh
# co dong tien kinh doanh am mot cach CO CAU (bat dong san om quy dat / xay do dang).
REALESTATE = set()
def load_sector_groups(sect):
    REALESTATE.clear()
    for sym, name in (sect or {}).items():
        if 'Bất động sản' in str(name): REALESTATE.add(sym)

CFG = dict(
    nav0=1_000_000_000.0,
    fee_buy=0.0015, fee_sell=0.0025,   # phi + thue ban
    slip=0.002,
    base_size=0.10, max_pos=0.20, max_total=0.60, max_sector=0.30,
    min_history=250, min_mktcap=1000e9,
    icr_block=1.5, icr_warn=2.5, de_block=4.0, icr_cfo_rescue=False, cfo_icr_min=3.0,
    npl_block=0.03, car_block=0.08, car_warn=0.09,
    trig_hose=0.058, trig_hnx=0.088,
    vol_floor=2.0, vol_ceil=4.5, gtgd_min=15e9,
    base_len=30, base_range=0.12, base_range_a=0.10,
    volat_min=0.015,
    score_floor=55,
    t_valve=3, stop=-0.07, hard_stop=-0.10, big_win=0.25,
    ma_trail=20, ma_trail_fast=10, conf=2,
    dday_window=25, dday_reset=0.05,
    no_ceil_in_base=True, trig_mult=1.0, max_pos_n=10,
    # cong tac hang C (mac dinh TAT - phai backtest truoc khi bat)
    use_protective_candle=True, use_big_sell=True, use_orange_cut=True,
    use_partial_take=True, use_hard_stop=True, use_pyramid=True,
    use_cond6=True, use_cond8=True, use_market_gate=True,
    trail_ma=20, trail_fast=10,
)

def sma(a,n):
    out=np.full_like(a,np.nan)
    c=np.nancumsum(np.nan_to_num(a,nan=0.0),axis=0)
    cnt=np.cumsum(~np.isnan(a),axis=0)
    out[n-1:]=(c[n-1:]-np.vstack([np.zeros((1,a.shape[1])),c[:-n]]))/n
    ok=(cnt[n-1:]-np.vstack([np.zeros((1,a.shape[1])),cnt[:-n]]))==n
    out[n-1:][~ok]=np.nan
    return out

def rolling_max(a,n):
    from numpy.lib.stride_tricks import sliding_window_view
    out=np.full_like(a,np.nan)
    if a.shape[0]>=n:
        w=sliding_window_view(a,n,axis=0)
        out[n-1:]=np.nanmax(w,axis=-1)
    return out

def rolling_min(a,n):
    from numpy.lib.stride_tricks import sliding_window_view
    out=np.full_like(a,np.nan)
    if a.shape[0]>=n:
        w=sliding_window_view(a,n,axis=0)
        out[n-1:]=np.nanmin(w,axis=-1)
    return out

# ---------------- LOP 2: CHAM DIEM CANSLIM ----------------
def _n(x, d=None):
    try:
        if x is None: return d
        if isinstance(x,float) and math.isnan(x): return d
        return x
    except Exception: return d

def canslim_score(f, rs, mom_pct, near_high, vol_ratio, gtgd):
    """f = dict fundamentals hien hanh; tra ve (diem, chi tiet)"""
    rs=_n(rs); mom_pct=_n(mom_pct,0.0); near_high=_n(near_high); vol_ratio=_n(vol_ratio); gtgd=_n(gtgd)
    pts={}
    rev_g=f.get('rev_yoy'); npat_g=f.get('npat_yoy')
    pts['C1']=15 if (npat_g is not None and npat_g>=0.25) else 0
    pts['C2']=15 if (rev_g is not None and rev_g>=0.15) else 0          # * MOI - O'Neil
    pts['C3']=5 if f.get('accel') else 0
    pts['A1']=10 if (f.get('cagr3') is not None and f['cagr3']>=0.20) else 0
    roe=f.get('roe')
    pts['A2']=10 if (roe is not None and roe>=0.17) else 0              # * MOI
    pts['N']=10 if (near_high is not None and near_high>=-0.15) else 0
    pts['S']=5 if (vol_ratio is not None and vol_ratio>=1.2) else 0
    pts['L']=15 if (rs is not None and rs>=70) else 0
    pts['I']=10 if (gtgd is not None and gtgd>=15e9) else 0
    pts['Mom']=round(5*(mom_pct if mom_pct is not None else 0),1)                                 # * MOI - edge manh nhat
    if f.get('bad_quality'): pts['C1']=0; pts['C2']=0; pts['C3']=0        # LN bat thuong >30%
    return sum(pts.values()), pts

# ---------------- LOP 1: CONG RUI RO ----------------
def risk_gate(sym, f):
    """tra ve (block:bool, ly_do, he_so_size)"""
    if f is None: return True,'Chua co BCTC',0.0
    mult=1.0
    if sym in BANKS:
        npl=f.get('npl'); car=f.get('car')
        if npl is not None and npl>CFG['npl_block']: return True,f'NPL {npl:.2%} > 3%',0
        if car is not None and car>0 and car<CFG['car_block']: return True,f'CAR {car:.2%} < 8%',0
        if car is not None and CFG['car_block']<=car<CFG['car_warn']: mult*=0.5
        return False,'',mult
    # Cong ty chung khoan & bao hiem: CFO < 0 la BAN CHAT kinh doanh, khong phai canh bao.
    # Cho vay margin tang len an het dong tien kinh doanh — y het chuyen ngan hang cho vay.
    # Tai lieu da mien D/E va ICR cho ngan hang vi cung ly do; mien CFO cho CK/BH la nhat quan.
    # (Loi cu: kiem tra CFO dat TRUOC nhanh nay nen CTS, HCM... bi chan oan.)
    if sym in BROKERS or sym in INSUR:
        return False,'',mult
    cfo=f.get('cfo_ttm')
    if cfo is not None and cfo<0:
        # Bat dong san: CFO am trong ky om quy dat / xay do dang la co cau, khong phai benh.
        # Mac dinh VAN CHAN (dung tai lieu). Bat co RE_CFO_WARN de doi thanh co vang.
        if sym in REALESTATE and CFG.get('re_cfo_warn'):
            mult*=0.5
        else:
            return True,'CFO < 0',0
    icr=f.get('icr')
    if icr is not None and icr<CFG['icr_block']:
        # CUU XET BANG TIEN THAT: neu dong tien kinh doanh tra duoc lai vay nhieu lan
        # thi ICR ke toan thap khong phai la mat kha nang thanh toan.
        cicr=f.get('cfo_icr')
        if CFG.get('icr_cfo_rescue') and cicr is not None and cicr>=CFG['cfo_icr_min']:
            mult*=0.5
        else:
            return True,f'ICR {icr:.2f} < 1.5',0
    de=f.get('de')
    if de is not None and de>CFG['de_block']: return True,f'D/E {de:.2f} > 4.0',0
    if icr is not None and icr<CFG['icr_warn']: mult*=0.5
    return False,'',mult

# ---------------- CHUAN BI FUNDAMENTAL THEO NGAY ----------------
def funda_timeline(rows):
    """Tra ve list (avail_date, dict metrics) tich luy, khong nhin truoc."""
    out=[]
    for i,r in enumerate(rows):
        m={}
        m['roe']=r.get('roe'); m['de']=r.get('de'); m['npl']=r.get('npl'); m['car']=r.get('car')
        m['mktcap']=r.get('marketCap'); m['pb']=r.get('pb')
        # TTM interest expense & cfo
        win=rows[max(0,i-3):i+1]
        ie=[abs(x.get('intexp') or 0) for x in win]
        cf=[x.get('cfo') for x in win if x.get('cfo') is not None]
        m['cfo_ttm']=sum(cf) if len(cf)>=3 else None
        ebit=r.get('ebit')
        tot_ie=sum(ie)
        m['icr']= (ebit/tot_ie) if (ebit is not None and tot_ie>0) else (99.0 if ebit is not None else None)
        m['ie_ttm']=tot_ie if tot_ie>0 else None
        # Kha nang tra lai bang TIEN THAT (dong tien kinh doanh), do luong tot hon ICR ke toan
        m['cfo_icr']= (m['cfo_ttm']/tot_ie) if (m['cfo_ttm'] is not None and tot_ie>0) else None
        # YoY quarterly
        prev={ (x['y'],x['q']):x for x in rows }
        py=prev.get((r['y']-1,r['q']))
        def g(a,b):
            if a is None or b is None or b<=0: return None
            return a/b-1
        m['rev_yoy']=g(r.get('rev'), py.get('rev') if py else None)
        m['npat_yoy']=g(r.get('npat'), py.get('npat') if py else None)
        # tang toc QoQ
        pq=rows[i-1] if i>0 else None
        m['accel']= bool(pq and r.get('npat') is not None and pq.get('npat') is not None and r['npat']>pq['npat']>0)
        # CAGR 3 nam (TTM npat vs TTM 12 quy truoc)
        def ttm(k):
            w=rows[max(0,k-3):k+1]
            v=[x.get('npat') for x in w if x.get('npat') is not None]
            return sum(v) if len(v)==4 else None
        a=ttm(i); b=ttm(i-12) if i>=12 else None
        m['cagr3']=((a/b)**(1/3)-1) if (a and b and a>0 and b>0) else None
        # ---------- DEN TIM: lai tang nho HOAT DONG BAT THUONG ----------
        # Mot doanh nghiep ban mieng dat, thanh ly nha may hay duoc hoan thue thi
        # LNST quy do vot len, bo cham diem nhin vao tuong la doanh nghiep dang khoe.
        # Sang quy sau khong con khoan do nua thi so lieu sup. Phai tach ra.
        #
        #   loi nhuan LOI     = truoc thue TRU phan khac  -> tu ban hang, tu van hanh
        #   loi nhuan KHAC    = isa14                      -> mot lan, khong lap lai
        #
        # Bat den tim khi mot trong hai chuyen xay ra:
        #   1. Phan khac chiem tren 30% LNST  (luat cu, giu nguyen)
        #   2. LNST tang so cung ky NHUNG loi nhuan loi lai GIAM — tang truong rong ruot
        oth=r.get('other'); np_=r.get('npat'); pre=r.get('pretax')
        m['bad_quality']= bool(oth is not None and np_ and np_>0 and (oth/np_)>0.30)
        core = (pre - oth) if (pre is not None and oth is not None) else None
        core_py = None
        if py is not None:
            _p, _o = py.get('pretax'), py.get('other')
            if _p is not None and _o is not None:
                core_py = _p - _o
        m['core'] = core
        m['core_yoy'] = g(core, core_py) if (core is not None and core_py is not None and core_py > 0) else None
        m['other_share'] = (oth / np_) if (oth is not None and np_ and np_ > 0) else None
        pre_py = py.get('pretax') if py else None
        m['pretax_yoy'] = g(pre, pre_py) if (pre is not None and pre_py is not None and pre_py > 0) else None
        rong_ruot = bool(m.get('pretax_yoy') is not None and m['pretax_yoy'] > 0
                         and m.get('core_yoy') is not None and m['core_yoy'] < 0)
        m['tim'] = bool(m['bad_quality'] or rong_ruot)
        m['tim_ly_do'] = ('lợi nhuận khác chiếm %.0f%% LNST' % (m['other_share'] * 100)
                          if m['bad_quality'] else
                          ('lợi nhuận trước thuế +%.0f%% nhưng lợi nhuận lõi %.0f%%'
                           % (m['pretax_yoy'] * 100, m['core_yoy'] * 100) if rong_ruot else None))
        m['label']=f"{r['y']}Q{r['q']}"
        out.append((r['avail'], m))
    out.sort(key=lambda x:x[0])
    return out

def as_of(tl, d):
    lo,hi=0,len(tl)-1; res=None
    while lo<=hi:
        mid=(lo+hi)//2
        if tl[mid][0]<=d: res=tl[mid][1]; lo=mid+1
        else: hi=mid-1
    return res

# ---------------- LOP 5: CONG THI TRUONG (he den 4 muc) ----------------
def market_regime(D, vni):
    """G1: chi so deu trong so cua universe vs MA200. G2: VN-Index vs MA50. G3: dem ngay phan phoi."""
    C=D['C']; N=C.shape[0]
    ret=np.full_like(C,np.nan); ret[1:]=C[1:]/C[:-1]-1
    ret=np.where(np.abs(ret)>0.35, np.nan, ret)
    eq=np.nanmean(ret,axis=1); eq=np.nan_to_num(eq,nan=0.0)
    g1=np.cumprod(1+eq)*1000.0
    g1ma=np.array([np.nan]*N)
    for i in range(199,N): g1ma[i]=g1[i-199:i+1].mean()
    # VN-Index map vao lich
    import datetime as _dt
    vmap={_dt.datetime.utcfromtimestamp(t).date():(c,v) for t,c,v in zip(vni['t'],vni['c'],vni['v'])}
    vc=np.array([vmap.get(d,(np.nan,np.nan))[0] for d in D['dates']],dtype=float)
    vv=np.array([vmap.get(d,(np.nan,np.nan))[1] for d in D['dates']],dtype=float)
    vc=_ffill(vc); vv=_ffill(vv)
    vma50=np.array([np.nan]*N)
    for i in range(49,N): vma50[i]=np.nanmean(vc[i-49:i+1])
    # ngay phan phoi tren VN-Index
    ddays=[]; dcount=np.zeros(N,dtype=int)
    for i in range(1,N):
        chg=vc[i]/vc[i-1]-1 if vc[i-1]>0 else 0
        if chg< -0.002 and vv[i]>vv[i-1]: ddays.append((i,vc[i]))
        ddays=[(k,p) for (k,p) in ddays if (i-k)<=CFG['dday_window'] and vc[i]<p*(1+CFG['dday_reset'])]
        dcount[i]=len(ddays)
    light=[]; size=[]
    for i in range(N):
        if not np.isnan(g1ma[i]) and g1[i]<g1ma[i]: l='DO'; s=0.0
        elif dcount[i]>=5: l='CAM'; s=0.0
        elif (not np.isnan(vma50[i]) and vc[i]<vma50[i]) or dcount[i]>=3: l='VANG'; s=0.5
        elif np.isnan(g1ma[i]): l='VANG'; s=0.5
        else: l='XANH'; s=1.0
        light.append(l); size.append(s)
    return dict(g1=g1,g1ma=g1ma,vni=vc,vma50=vma50,dcount=dcount,light=light,size=np.array(size))

def _ffill(a):
    out=a.copy()
    for i in range(1,len(out)):
        if np.isnan(out[i]): out[i]=out[i-1]
    return out

# ---------------- CHI BAO KY THUAT ----------------
def indicators(D):
    C=D['C']; H=D['H']; L=D['L']; V=D['V']; O=D['O']; N,M=C.shape
    I={}
    for n in (10,20,30,50,200):
        I[f'ma{n}']=sma(C,n)
    I['vma20']=sma(V,20)
    turn=C*V*1000.0
    I['gtgd20']=sma(turn,20)
    I['turn']=turn
    rng=(H-L)/np.where(C>0,C,np.nan)
    I['volat20']=sma(rng,20)
    I['hi52']=rolling_max(H,250)
    I['hi10']=rolling_max(H,10)
    I['nbars']=np.cumsum(~np.isnan(C),axis=0)
    chg=np.full_like(C,np.nan); chg[1:]=C[1:]/C[:-1]-1
    I['chg']=chg
    r12=np.full_like(C,np.nan); r12[250:]=C[250:]/C[:-250]-1
    r3=np.full_like(C,np.nan); r3[60:]=C[60:]/C[:-60]-1
    I['rs']=_pct_rank(r12)*100.0
    I['mom3']=_pct_rank(r3)
    # nen 30 phien truoc phien hien tai
    base_hi=np.full_like(C,np.nan); base_lo=np.full_like(C,np.nan)
    bl=CFG['base_len']
    rh=rolling_max(C,bl); rl=rolling_min(C,bl)
    base_hi[1:]=rh[:-1]; base_lo[1:]=rl[:-1]
    exch=np.array([1 if D['exch'][s]=='HNX' else 0 for s in D['sym']])
    thr=np.where(exch==1, CFG['trig_hnx'], CFG['trig_hose'])
    is_ceil=(chg>=thr*0.995).astype(float)
    cs=np.cumsum(is_ceil,axis=0)
    ceil_in_base=np.full_like(C,np.nan)
    ceil_in_base[bl+1:]=cs[bl:-1]-cs[:-bl-1]
    I['base_hi']=base_hi; I['base_lo']=base_lo; I['ceil_in_base']=ceil_in_base
    I['thr']=thr
    return I

def _pct_rank(a):
    out=np.full_like(a,np.nan)
    for i in range(a.shape[0]):
        row=a[i]; m=~np.isnan(row)
        if m.sum()<30: continue
        v=row[m]; order=v.argsort().argsort()
        out[i,m]=order/(len(v)-1)
    return out

# ---------------- LOP 3 + 4: NEN GIA & DIEM MUA ----------------
def check_buy(j, i, D, I, f, score):
    """Tra ve (ok, chi_tiet_8_dieu_kien, he_so_nen)"""
    C=D['C']; H=D['H']; L=D['L']; V=D['V']
    c=C[i,j]
    if np.isnan(c): return False,None,0
    chg=I['chg'][i,j]; thr=I['thr'][j]
    vr = V[i,j]/I['vma20'][i,j] if I['vma20'][i,j] else np.nan
    gtgd = c*V[i,j]*1000.0
    bh,blo=I['base_hi'][i,j], I['base_lo'][i,j]
    base_rng = (bh-blo)/blo if (blo and blo>0) else np.nan
    ceil_in = I['ceil_in_base'][i,j]
    volat=I['volat20'][i,j]
    mid=(H[i,j]+L[i,j])/2
    npat_g=f.get('npat_yoy') if f else None
    vr=_n(vr,0.0); gtgd=_n(gtgd,0.0); base_rng=_n(base_rng); ceil_in=_n(ceil_in); volat=_n(volat,0.0)
    cond={
     '1. Bien do tang gia': bool(chg is not None and chg>=thr*CFG['trig_mult']),
     '2. Volume >= 2.0 x TB20': bool(vr>=CFG['vol_floor']),
     '3. GTGD phien >= 15 ty': bool(gtgd>=CFG['gtgd_min']),
     '4a. Bien do nen <= %d%%'%int(CFG['base_range']*100): bool(base_rng is not None and base_rng<=CFG['base_range']),
     '4b. Khong co phien tran trong nen': bool(ceil_in==0 or not CFG['no_ceil_in_base']),
     '5. LNST YoY ngoai vung yeu': bool(npat_g is None or not (0<=npat_g<0.25)),
     '6. Tran volume <= 4.5 x TB20': bool(vr<=CFG['vol_ceil'] or not CFG['use_cond6']),
     '7. Bien dong TB20 >= 1.5%': bool(volat>=CFG['volat_min']),
     '8. Dong cua nua tren nen': bool(c>=mid or not CFG['use_cond8']),
    }
    ok=all(cond.values()) and score>=CFG['score_floor']
    bm = 1.2 if (base_rng is not None and base_rng<=CFG['base_range_a']) else 1.0
    return ok,cond,bm

# ---------------- BACKTEST ----------------
class Pos:
    __slots__=('sym','j','entry_i','entry_px','shares','cost','hi','bo_low','pyramided','part','sector','peak_gain','below20','below10','name')
    def __init__(self,**kw):
        for k,v in kw.items(): setattr(self,k,v)

def run(start='2019-01-01', end=None, cfg_over=None, log_signals=True):
    if cfg_over: CFG.update(cfg_over)
    D=build(); I=indicators(D)
    vni=json.load(open('data/VNINDEX.json'))
    R=market_regime(D,vni)
    fu=parse_funda()
    tls={s:funda_timeline(rows) for s,rows in fu.items()}
    sect=json.load(open('data/sector.json'))
    S=D['sym']; dates=D['dates']; C=D['C']; O=D['O']; H=D['H']; L=D['L']; V=D['V']
    N,M=C.shape
    sd=dt.date(*map(int,start.split('-')))
    ed=dt.date(*map(int,end.split('-'))) if end else dates[-1]
    i0=next(i for i,d in enumerate(dates) if d>=sd)
    i1=next((i for i,d in enumerate(dates) if d>ed), N)
    nav=CFG['nav0']; cash=nav; pos={}; trades=[]; eq=[]; signals=[]; blocked_stats={}
    jmap={s:j for j,s in enumerate(S)}
    for i in range(i0,i1):
        day=dates[i]
        # ---- mark to market
        mv=0.0
        for p in pos.values():
            px=C[i,p.j]
            if np.isnan(px): px=p.hi
            mv+=px*p.shares
        nav=cash+mv
        eq.append((day.isoformat(),nav,R['light'][i],int(R['dcount'][i])))
        # ---- LOP 8: BO THOAT
        for sym in list(pos):
            p=pos[sym]; j=p.j; px=C[i,j]
            if np.isnan(px): continue
            held=i-p.entry_i
            gain=px/p.entry_px-1
            p.peak_gain=max(p.peak_gain,gain)
            mT=I['ma%d'%CFG['trail_ma']][i,j]; mF=I['ma%d'%CFG['trail_fast']][i,j]
            p.below20 = p.below20+1 if (not np.isnan(mT) and px<mT) else 0
            p.below10 = p.below10+1 if (not np.isnan(mF) and px<mF) else 0
            if held<2: continue      # T+2 chua ve hang
            reason=None; frac=1.0
            if CFG['use_hard_stop'] and gain<=CFG['hard_stop']: reason='Hard stop -10%'
            elif CFG['use_protective_candle'] and not np.isnan(p.bo_low) and px<p.bo_low: reason='Cay nen bao ve'
            elif held>=3 and gain<=CFG['stop']: reason='Cat lo -7%'
            elif held>=CFG['t_valve'] and gain<=0: reason='Van T+%d'%CFG['t_valve']
            elif CFG['use_big_sell'] and I['chg'][i,j]<-0.04 and V[i,j]>1.2*I['vma20'][i,j]: reason='Big sell khan'; frac=0.5
            elif p.peak_gain>=CFG['big_win'] and p.below10>=CFG['conf']: reason='Trailing MA%d (lai lon)'%CFG['trail_fast']
            elif p.below20>=CFG['conf']: reason='Trailing MA%d'%CFG['trail_ma']
            elif CFG['use_partial_take'] and gain>=0.20 and V[i,j]>CFG['vol_ceil']*I['vma20'][i,j]: reason='Chot 1/3 (vol > 4.5x)'; frac=1/3
            elif CFG['use_orange_cut'] and R['light'][i]=='CAM' and not p.part: reason='Den CAM - ha 1/3'; frac=1/3
            if reason:
                sh=int(p.shares*frac//100*100) or p.shares
                if frac<1 and sh>=p.shares: sh=int(p.shares*frac//100*100)
                if sh<=0: continue
                proceeds=sh*px*(1-CFG['fee_sell']-CFG['slip'])
                cash+=proceeds
                trades.append(dict(sym=sym,name=p.name,sector=p.sector,
                    entry=dates[p.entry_i].isoformat(),exit=day.isoformat(),
                    entry_px=round(p.entry_px,2),exit_px=round(px,2),shares=sh,
                    held=held,pnl_pct=round((px*(1-CFG['fee_sell']-CFG['slip'])/p.entry_px-1)*100,2),
                    pnl_vnd=round(proceeds-sh*p.cost),reason=reason,partial=frac<1,
                    light=R['light'][p.entry_i],peak=round(p.peak_gain*100,1)))
                p.shares-=sh
                if frac<1: p.part=True
                if p.shares<=0: del pos[sym]
        # ---- LOP 5/6/7: MO LENH MOI
        sizemul=R['size'][i] if CFG['use_market_gate'] else 1.0
        if sizemul>0 and len(pos)<CFG['max_pos_n']:
            cands=[]
            for j,sym in enumerate(S):
                if sym in pos: continue
                if np.isnan(C[i,j]) or I['nbars'][i,j]<CFG['min_history']: continue
                tl=tls.get(sym)
                if not tl: continue
                f=as_of(tl,day)
                if f is None: continue
                mc=f.get('mktcap')
                if not mc or mc<CFG['min_mktcap']: continue
                blk,why,rmul=risk_gate(sym,f)
                if blk:
                    blocked_stats[why.split()[0] if why else 'NA']=blocked_stats.get(why.split()[0] if why else 'NA',0)+1
                    continue
                sc,pts=canslim_score(f, I['rs'][i,j], I['mom3'][i,j],
                        (C[i,j]/I['hi52'][i,j]-1) if I['hi52'][i,j] else None,
                        V[i,j]/I['vma20'][i,j] if I['vma20'][i,j] else None,
                        I['gtgd20'][i,j])
                ok,cond,bm=check_buy(j,i,D,I,f,sc)
                if not ok: continue
                cands.append((sc,sym,j,rmul,bm,f,pts,cond))
            cands.sort(key=lambda x:-x[0])
            for sc,sym,j,rmul,bm,f,pts,cond in cands:
                secname=sect.get(sym,'Khac')
                sec_val=sum(C[i,q.j]*q.shares for q in pos.values() if q.sector==secname)
                total_val=sum(C[i,q.j]*q.shares for q in pos.values())
                if total_val/nav>=CFG['max_total']: break
                target=nav*CFG['base_size']*sizemul*rmul*bm
                target=min(target, nav*CFG['max_pos'], nav*CFG['max_total']-total_val,
                           nav*CFG['max_sector']-sec_val, cash)
                px=C[i,j]*(1+CFG['slip'])
                if target < nav*0.02: continue          # bo qua vi the qua nho
                sh=int(target/ (px*(1+CFG['fee_buy'])) //100*100)
                if sh<100: continue
                cost=px*(1+CFG['fee_buy'])
                cash-=sh*cost
                pos[sym]=Pos(sym=sym,j=j,entry_i=i,entry_px=cost,shares=sh,cost=cost,
                    hi=C[i,j],bo_low=L[i,j],pyramided=False,part=False,sector=secname,
                    peak_gain=0.0,below20=0,below10=0,name=sym)
                if log_signals:
                    signals.append(dict(date=day.isoformat(),sym=sym,score=round(sc,1),
                        px=round(C[i,j],2),light=R['light'][i],sector=secname,
                        pts=pts,size_pct=round(sh*cost/nav*100,2)))
        # ---- LOP 9: PYRAMID
        for sym,p in list(pos.items()):
            if not CFG['use_pyramid'] or p.pyramided or R['light'][i]!='XANH': continue
            held=i-p.entry_i
            if not (4<=held<=7): continue
            px=C[i,p.j]
            if np.isnan(px) or px/p.entry_px-1<0.10: continue
            if px < 0.999*I['hi10'][i,p.j]: continue
            add=int(p.shares*0.5//100*100)
            val=(px*p.shares)+add*px
            if add<100 or val>nav*CFG['max_pos'] or add*px*(1+CFG['fee_buy'])>cash: continue
            c2=px*(1+CFG['slip'])*(1+CFG['fee_buy'])
            p.entry_px=(p.entry_px*p.shares+c2*add)/(p.shares+add)
            cash-=add*c2; p.shares+=add; p.pyramided=True
    return dict(eq=eq,trades=trades,signals=signals,regime=R,D=D,I=I,tls=tls,
                blocked=blocked_stats,pos=pos,dates=dates,nav=nav,cash=cash)
