# -*- coding: utf-8 -*-
"""NGUYEN SON INVEST - BOT v2 (du lieu FireAnt)
   He 9 lop theo 'He Thong Giao Dich Hop Nhat v1.0', chay walk-forward khong nhin truoc."""
import numpy as np, json, datetime as dt, copy
from fa_prep import build as fa_build
from fa_ind import indicators
from regime2 import build_regime
from prep import parse_funda
from engine import funda_timeline, as_of, risk_gate, canslim_score, BANKS, BROKERS, INSUR

CFG = dict(
  nav0=1_000_000_000.0, fee_buy=0.0015, fee_sell=0.0025, slip=0.002,
  base_size=0.10, max_pos=0.20, max_total=0.60, max_pos_n=8, min_size=0.02,
  min_mktcap=1000e9, min_history=250,
  use_top_liquid=True, top_n=300,   # chi giao dich TOP 300 GTGD binh quan 20 phien (tinh theo tung phien)
  vol_floor=2.0, vol_ceil=4.5, gtgd_min=15e9, volat_min=0.015,
  base_len=30, base_range=0.18, no_ceil_in_base=False,
  score_floor=45, use_cond6=False, use_cond8=True,
  t_valve=6, stop=-0.07, hard_stop=-0.10, big_win=0.25,
  trail_ma=30, trail_fast=10, conf=2,
  use_protective_candle=False, use_big_sell=False, use_orange_cut=True,
  # Chi ha 1/3 khi den THUC SU XAU DI so voi luc mua. Mua duoi den Cam (co 35%)
  # roi hai phien sau lai ha 1/3 cung vi den Cam la vo ly — khong co gi thay doi ca.
  orange_cut_only_if_worse=False,
  use_partial_take=False, use_hard_stop=True, use_pyramid=True,
  use_market_gate=True, use_ftd=True, ftd_gain=0.015,
  size_map={'XANH':1.0,'VANG':0.5,'CAM':0.0,'DO':0.0},
  use_ordimb=False, ordimb_min=1.0, hard_ceiling=False, use_fnet=False, rs_min=0,
  use_giveback=False, gb_trigger=0.10, gb_keep=0.50, use_shelf=False, shelf_range=0.10,
  re_cfo_warn=False, icr_cfo_rescue=False, cfo_icr_min=3.0,   # True = BDS co CFO<0 chi bi co vang (size x0.5) thay vi chan han
  use_be=False, be_trigger=0.08, be_level=0.01,
  start='2019-01-02', end=None,
  # --- LOP KIEM DINH: truot gia bat doi xung ---
  # Chieu MUA tran thuong truot it (khop duoc la may) nhung THIEU khoi luong.
  # Chieu BAN thao khi gay MA thi truot RAT NANG vi trang ben mua.
  # De None thi ca hai chieu dung chung 'slip' nhu cu — khong doi hanh vi PROD.
  slip_buy=None, slip_sell=None,
  # --- LOP KIEM DINH: ngat mach bao ve von (circuit breaker) ---
  # Win rate ~36% thi mot chuoi 8-10 lenh thua lien tiep la chuyen binh thuong
  # ve mat xac suat. Ngat mach KHONG doan thi truong — no chi ha do lon vi the
  # sau khi thiet hai da xay ra, va tu mo lai khi NAV lap dinh moi.
  cb_enable=False, cb_dd=0.08, cb_losses=6, cb_cut=0.5, cb_days=10,
)

class Pos:
    __slots__=('sym','j','ei','epx','sh','peak','b20','b10','part','pyr','sector','bo_low')
    def __init__(s,**kw):
        for k,v in kw.items(): setattr(s,k,v)

_CACHE={}
def load():
    if 'd' not in _CACHE:
        d=fa_build(); _CACHE['d']=d
        _CACHE['I']=indicators(d)
        fu=parse_funda('data/funda_raw2.json')
        _CACHE['tls']={s:funda_timeline(r) for s,r in fu.items() if r}
        try: _CACHE['sect']=json.load(open('data/sector2.json'))
        except Exception: _CACHE['sect']={}
        from engine import load_sector_groups
        load_sector_groups(_CACHE['sect'])
    return _CACHE['d'], _CACHE['I'], _CACHE['tls'], _CACHE['sect']

def run(cfg=None, log=True):
    C=dict(CFG); C.update(cfg or {})
    import engine as _eng
    _eng.CFG['re_cfo_warn']=C.get('re_cfo_warn',False)
    _eng.CFG['icr_cfo_rescue']=C.get('icr_cfo_rescue',False)
    _eng.CFG['cfo_icr_min']=C.get('cfo_icr_min',3.0)   # dong bo co sang risk_gate
    d,I,tls,sect = load()
    # Truot gia hai chieu. Khong khai bao rieng thi ca hai bang 'slip' — y het ban cu.
    SB = C['slip'] if C.get('slip_buy')  is None else float(C['slip_buy'])
    SS = C['slip'] if C.get('slip_sell') is None else float(C['slip_sell'])
    R=build_regime(d,I,C)
    cal=d['cal']; S=d['sym']; N=len(cal)
    PX=d['PriceClose']; AC=d['AdjClose']; AH=d['AdjHigh']; AL=d['AdjLow']; AO=d['AdjOpen']
    TV=d['TotalValue']; MC=d['MarketCap']; V=d['Volume']
    base_rng=(I['base_hi']-I['base_lo'])/np.where(I['base_lo']>0,I['base_lo'],np.nan)
    shelf_rng=(I['sh_hi']-I['sh_lo'])/np.where(I['sh_lo']>0,I['sh_lo'],np.nan)
    # VU TRU GIAO DICH: chi TOP N ma thanh khoan nhat, tinh lai theo TUNG PHIEN
    # (khong dung danh sach chi so cua hom nay ap nguoc lai qua khu -> khong nhin truoc)
    TOPN=None
    if C.get('use_top_liquid'):
        from vn300 import build_topn
        TOPN=build_topn(I, int(C.get('top_n',300)))
    base_ok = (base_rng<=C['base_range'])
    if C['use_shelf']: base_ok = base_ok | (shelf_rng<=C['shelf_range'])
    _thr = (I['thr_hard'] if C['hard_ceiling'] else I['thr'])
    if C.get('trig_pct') is not None:
        _thr = np.full_like(_thr, float(C['trig_pct']))
    trig=I['pct']>=_thr
    i0=int(np.searchsorted(cal,C['start']))
    # Cat duoi de chay walk-forward: mot lat cat thoi gian that su, khong phai loc sau.
    if C.get('end'): N=min(N,int(np.searchsorted(cal,C['end'],side='right')))
    # trang thai ngat mach
    cb_peak=C['nav0']; cb_streak=0; cb_until=-1; cb_log=[]
    nav=C['nav0']; cash=nav; pos={}; trades=[]; eq=[]; sigs=[]; blocked={}
    for i in range(i0,N):
        day=dt.date.fromisoformat(str(cal[i]))
        mv=0.0
        for p in pos.values():
            px=AC[i,p.j]
            mv += (px if not np.isnan(px) else p.epx)*p.sh
        nav=cash+mv
        eq.append((str(cal[i]),nav,R['light'][i],int(R['dcount'][i])))
        # ---------- LOP 8: BO THOAT ----------
        for sym in list(pos):
            p=pos[sym]; j=p.j; px=AC[i,j]
            if np.isnan(px): continue
            held=i-p.ei; gain=px/p.epx-1
            p.peak=max(p.peak,gain)
            mT=I['ma%d'%C['trail_ma']][i,j]; mF=I['ma%d'%C['trail_fast']][i,j]
            p.b20 = p.b20+1 if (not np.isnan(mT) and px<mT) else 0
            p.b10 = p.b10+1 if (not np.isnan(mF) and px<mF) else 0
            if held<2: continue
            r=None; frac=1.0
            if C['use_hard_stop'] and gain<=C['hard_stop']: r='Hard stop −10%'
            elif C['use_protective_candle'] and not np.isnan(p.bo_low) and px<p.bo_low: r='Cây nến bảo vệ'
            elif held>=3 and gain<=C['stop']: r='Cắt lỗ −7%'
            elif C['use_giveback'] and p.peak>=C['gb_trigger'] and gain<=p.peak*C['gb_keep']: r='Chốt bảo vệ (trả lại %d%% đỉnh)'%int((1-C['gb_keep'])*100)
            elif C['use_be'] and p.peak>=C['be_trigger'] and gain<=C['be_level']: r='Về bờ (đã lãi %d%%)'%int(C['be_trigger']*100)
            elif held>=C['t_valve'] and gain<=0: r='Van thời gian T+%d'%C['t_valve']
            elif C['use_big_sell'] and I['pct'][i,j]<-0.04 and V[i,j]>1.2*I['vma20'][i,j]: r='Big sell khẩn'; frac=0.5
            elif p.peak>=C['big_win'] and p.b10>=C['conf']: r='Trailing MA%d (lãi lớn)'%C['trail_fast']
            elif p.b20>=C['conf']: r='Trailing MA%d'%C['trail_ma']
            elif C['use_partial_take'] and gain>=0.20 and V[i,j]>C['vol_ceil']*I['vma20'][i,j]: r='Chốt 1/3 (vol > 4,5×)'; frac=1/3
            elif (C['use_orange_cut'] and R['light'][i]=='CAM' and not p.part
                  and (not C.get('orange_cut_only_if_worse')
                       or R['light'][p.ei] in ('XANH','VANG'))): r='Đèn Cam — hạ 1/3'; frac=1/3
            if r:
                sh=int(p.sh*frac//100*100) if frac<1 else p.sh
                if sh<=0: continue
                got=sh*px*(1-C['fee_sell']-SS); cash+=got
                trades.append(dict(sym=str(sym),sector=sect.get(str(sym),'Khác'),
                  entry=str(cal[p.ei]),exit=str(cal[i]),entry_px=round(float(p.epx),2),
                  exit_px=round(float(px),2),held=int(held),
                  pnl_pct=round(float(px*(1-C['fee_sell']-SS)/p.epx-1)*100,2),
                  pnl_vnd=round(float(got-sh*p.epx)),reason=r,
                  light=R['light'][p.ei],peak=round(float(p.peak)*100,1)))
                if C.get('cb_enable'):
                    cb_streak = cb_streak+1 if trades[-1]['pnl_pct']<=0 else 0
                p.sh-=sh
                if frac<1: p.part=True
                if p.sh<=0: del pos[sym]
        # ---------- LOP 0-7: MO LENH ----------
        smul=R['size'][i] if C['use_market_gate'] else 1.0
        # ---------- NGAT MACH BAO VE VON ----------
        # Kich hoat khi NAV thung nguong tu dinh HOAC dinh chuoi thua lien tiep.
        # Hieu luc cb_days phien, trong do co vi the bi nhan cb_cut (0 = ngung han).
        if C.get('cb_enable'):
            if nav>cb_peak: cb_peak=nav; cb_streak=0
            hit_dd  = (nav/cb_peak-1) <= -abs(C['cb_dd'])
            hit_str = cb_streak >= int(C['cb_losses'])
            if (hit_dd or hit_str) and i>cb_until:
                cb_until=i+int(C['cb_days'])
                cb_log.append(dict(date=str(cal[i]),
                                   ly_do=('NAV -%.0f%% tu dinh'%(100*abs(nav/cb_peak-1))) if hit_dd
                                         else ('%d lenh thua lien tiep'%cb_streak),
                                   den=str(cal[min(cb_until,N-1)])))
                cb_streak=0
            if i<=cb_until: smul*=float(C['cb_cut'])
        if smul>0 and len(pos)<C['max_pos_n']:
            uni = TOPN[i] if TOPN is not None else np.ones(len(S),dtype=bool)
            cand=np.where(trig[i] & uni & (MC[i]>C['min_mktcap']) & (I['nbars'][i]>=C['min_history'])
                          & (I['volr'][i]>=C['vol_floor']) & (TV[i]>=C['gtgd_min'])
                          & (I['volat20'][i]>=C['volat_min'])
                          & base_ok[i])[0]
            rows=[]
            for j in cand:
                sym=str(S[j])
                if sym in pos: continue
                if C['use_cond8'] and AC[i,j] < (AH[i,j]+AL[i,j])/2: continue
                if C['use_cond6'] and I['volr'][i,j]>C['vol_ceil']: continue
                if C['use_ordimb'] and not (I['ordimb'][i,j]>=C['ordimb_min']): continue
                if C['use_fnet'] and not (I['fnet'][i,j]>=0): continue
                if C['rs_min'] and not (I['rs'][i,j]>=C['rs_min']): continue
                tl=tls.get(sym)
                f=as_of(tl,day) if tl else None
                if f is None: continue
                blk,why,rmul=risk_gate(sym,f)
                if blk:
                    k=(why or 'NA').split()[0]; blocked[k]=blocked.get(k,0)+1; continue
                npg=f.get('npat_yoy')
                if npg is not None and 0<=npg<0.25: continue        # DK5
                sc,pts=canslim_score(f, I['rs'][i,j], I['mom3'][i,j],
                        float(AC[i,j]/I['hi52'][i,j]-1) if I['hi52'][i,j]>0 else None,
                        float(I['volr'][i,j]), float(I['tvma20'][i,j]))
                if sc<C['score_floor']: continue
                bm=1.2 if base_rng[i,j]<=0.10 else 1.0
                rows.append((sc,j,sym,rmul,bm,pts))
            rows.sort(key=lambda x:-x[0])
            for sc,j,sym,rmul,bm,pts in rows:
                secn=sect.get(sym,'Khác')
                tot=sum(AC[i,q.j]*q.sh for q in pos.values())
                sec=sum(AC[i,q.j]*q.sh for q in pos.values() if q.sector==secn)
                if tot/nav>=C['max_total']: break
                tgt=min(nav*C['base_size']*smul*rmul*bm, nav*C['max_pos'],
                        nav*C['max_total']-tot, nav*0.30-sec, cash)
                if tgt < nav*C['min_size']: continue
                # gia khop: mac dinh dong cua phien tin hieu.
                # entry_next_open=True -> khop gia mo cua phien sau (thuc te hon khi ma da du tran)
                ei=i; fill=AC[i,j]
                mode=C.get('entry_mode','close')      # close | next_open | next_vwap
                if C.get('entry_next_open'): mode='next_open'
                if mode!='close':
                    if i+1>=N: continue
                    if mode=='next_open': fo=AO[i+1,j]
                    else:
                        v=d['Volume'][i+1,j]; tv=d['TotalValue'][i+1,j]; ar=d['AdjRatio'][i+1,j]
                        fo=(tv/v/ar) if (v and v>0 and ar and ar>0) else AO[i+1,j]
                    if fo is None or np.isnan(fo) or fo<=0: continue
                    ei=i+1; fill=float(fo)
                px=fill*(1+SB)*(1+C['fee_buy'])
                sh=int(tgt/px//100*100)
                if sh<100: continue
                cash-=sh*px
                pos[sym]=Pos(sym=sym,j=int(j),ei=ei,epx=float(px),sh=sh,peak=0.0,b20=0,b10=0,
                             part=False,pyr=False,sector=secn,bo_low=float(AL[i,j]))
                if log: sigs.append(dict(date=str(cal[i]),sym=sym,score=round(float(sc),1),
                    px=round(float(PX[i,j])/1000,2),light=R['light'][i],sector=secn,pts=pts,
                    size_pct=round(sh*px/nav*100,2)))
        # ---------- LOP 9: PYRAMID ----------
        for sym,p in list(pos.items()):
            if not C['use_pyramid'] or p.pyr or R['light'][i]!='XANH': continue
            held=i-p.ei
            if not (4<=held<=7): continue
            px=AC[i,p.j]
            if np.isnan(px) or px/p.epx-1<0.10 or px<0.999*I['hi10'][i,p.j]: continue
            add=int(p.sh*0.5//100*100)
            c2=px*(1+SB)*(1+C['fee_buy'])
            if add<100 or (px*p.sh+add*px)>nav*C['max_pos'] or add*c2>cash: continue
            p.epx=(p.epx*p.sh+c2*add)/(p.sh+add); cash-=add*c2; p.sh+=add; p.pyr=True
    return dict(eq=eq,trades=trades,signals=sigs,R=R,blocked=blocked,pos=pos,
                nav=nav,cash=cash,cal=cal,d=d,I=I,cfg=C,cb_log=cb_log)

def metrics(r):
    eq=np.array([x[1] for x in r['eq']]); tr=r['trades']
    yrs=max(len(eq)/250,1e-9); dd=1-eq/np.maximum.accumulate(eq)
    p=[t['pnl_pct'] for t in tr]; w=[x for x in p if x>0]; l=[x for x in p if x<=0]
    gp=sum(t['pnl_vnd'] for t in tr if t['pnl_vnd']>0); gl=abs(sum(t['pnl_vnd'] for t in tr if t['pnl_vnd']<0))
    rets=np.diff(eq)/eq[:-1]
    return dict(trades=len(tr),per_year=round(len(tr)/yrs,1),
      total_return=round(float(eq[-1]/eq[0]-1),4),cagr=round(float((eq[-1]/eq[0])**(1/yrs)-1),4),
      maxdd=round(float(dd.max()),4),winrate=round(len(w)/len(p),4) if p else 0,
      avg_win=round(float(np.mean(w)),2) if w else 0,avg_loss=round(float(np.mean(l)),2) if l else 0,
      rr=round(abs(np.mean(w)/np.mean(l)),2) if (w and l) else None,
      pf=round(gp/gl,2) if gl>0 else None,expectancy=round(float(np.mean(p)),2) if p else 0,
      sharpe=round(float(np.mean(rets)/np.std(rets)*np.sqrt(250)),2) if np.std(rets)>0 else None,
      final_nav=round(float(eq[-1])))
