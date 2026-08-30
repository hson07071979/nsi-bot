# -*- coding: utf-8 -*-
"""TRA CUU TUNG MA — phien toi can gi de bot bao mua?

Voi moi ma trong vu tru, tinh ra DUNG hai nguong cua phien ke tiep:
  - gia dong cua toi thieu  = gia tham chieu x (1 + bien do bat tran)
  - khoi luong toi thieu    = 2 x khoi luong binh quan 20 phien
va cho biet ma dang o trang thai nao: da du diem mua, dang cho, chua vao nen,
hay bi cong rui ro chan han.
"""
import csv
import datetime as dt
import numpy as np
from engine import risk_gate, canslim_score, as_of
from manual import loai as _loai


def _names(path='data/by_exchange.csv'):
    out = {}
    try:
        for r in csv.DictReader(open(path, encoding='utf-8')):
            ex = {'HSX': 'HOSE', 'HNX': 'HNX', 'UPCOM': 'UPCOM'}.get(r['exchange'], r['exchange'])
            out[r['symbol']] = (r.get('organ_name') or r.get('organ_short_name') or '', ex)
    except Exception:
        pass
    return out


def build(d, I, tls, sect, cfg, topn):
    """Tra ve dict {sym: {...}} cho o tra cuu tren trang web."""
    S = [str(x) for x in d['sym']]
    cal = [str(x) for x in d['cal']]
    i = len(cal) - 1
    today = dt.date.fromisoformat(cal[i])
    NM = _names()
    LOAI = _loai()          # ma anh Son loai thu cong trong loai.txt
    MC, TV, AC = d['MarketCap'], d['TotalValue'], d['AdjClose']
    base_rng = (I['base_hi'] - I['base_lo']) / np.where(I['base_lo'] > 0, I['base_lo'], np.nan)

    def f2(x, nd=2):
        return None if (x is None or x != x) else round(float(x), nd)

    out = {}
    for j, s in enumerate(S):
        close = float(d['PriceClose'][i, j])
        if not (close == close) or close <= 0:
            continue
        nm, ex = NM.get(s, ('', 'HOSE'))
        thr = float(I['thr'][j])
        vma = float(I['vma20'][i, j]) if I['vma20'][i, j] == I['vma20'][i, j] else 0.0
        gt = float(I['tvma20'][i, j]) if I['tvma20'][i, j] == I['tvma20'][i, j] else 0.0
        mc = float(MC[i, j]) if MC[i, j] == MC[i, j] else 0.0
        br = float(base_rng[i, j]) if base_rng[i, j] == base_rng[i, j] else None
        volat = float(I['volat20'][i, j]) if I['volat20'][i, j] == I['volat20'][i, j] else 0.0
        rs = f2(I['rs'][i, j], 1)
        inuni = bool(topn[i, j])

        tl = tls.get(s)
        fa = as_of(tl, today) if tl else None
        if fa is None:
            blk, why = True, 'Chưa có báo cáo tài chính'
            sc = 0.0; fund = 0; npg_dk5 = None; tim, tim_vi = False, None
        else:
            b, w, _ = risk_gate(s, fa)
            blk, why = b, w
            npg_dk5 = fa.get('npat_yoy')
            tim, tim_vi = bool(fa.get('tim')), fa.get('tim_ly_do')
            sc, _pts = canslim_score(fa, I['rs'][i, j], I['mom3'][i, j],
                                     float(AC[i, j] / I['hi52'][i, j] - 1) if I['hi52'][i, j] > 0 else None,
                                     float(I['volr'][i, j]), gt)
            sc = float(sc) if sc == sc else 0.0
            fund = sum(_pts.get(k, 0) for k in ('C1', 'C2', 'C3', 'A1', 'A2'))

        # --- hai nguong cua phien ke tiep ---
        need_px = close * (1 + thr)          # gia tham chieu phien toi = gia dong cua hom nay
        need_vol = vma * float(cfg['vol_floor'])

        # --- trang thai ---
        miss = []
        if not inuni:
            miss.append(f'chưa vào TOP {cfg["top_n"]} thanh khoản')
        if mc < cfg['min_mktcap']:
            miss.append(f'vốn hoá {mc/1e9:.0f} tỷ < {cfg["min_mktcap"]/1e9:.0f} tỷ')
        if gt < cfg['gtgd_min']:
            miss.append(f'GTGD bình quân {gt/1e9:.0f} tỷ < {cfg["gtgd_min"]/1e9:.0f} tỷ')
        if br is None or br > cfg['base_range']:
            miss.append('chưa tạo được nền giá chặt' + (f' (nền {br*100:.0f}%)' if br else ''))
        if volat < cfg['volat_min']:
            miss.append('biên độ dao động quá thấp')
        if sc < cfg['score_floor']:
            miss.append(f'điểm CANSLIM {sc:.0f} < {cfg["score_floor"]}')
        # DK5 — bo may bo qua truong hop loi nhuan rong chi tang 0-25%: khong du
        # manh de bung no, nhung du dep de danh lua bo cham diem. Truoc day o tra
        # cuu khong kiem dieu nay nen watchlist rong hon vu tru bot thuc su mua.
        # NHAN PHAI IN MOT CHU SO THAP PHAN.
        # Loi cu: in {x*100:.0f}% nen 24,96% hien ra "25%", ma dung 25% thi KHONG
        # bi chan (luat la 0 <= x < 0,25). Doc nhan thay "tang 25% (0-25%)" trong
        # nhu he tu mau thuan — thuc ra luat dung, chi co nhan lam tron len. Va ghi
        # khoang bang dau bat dang thuc de khong ai tuong 25% nam trong vung bi loai.
        if npg_dk5 is not None and 0 <= npg_dk5 < 0.25:
            miss.append(f'lợi nhuận ròng chỉ tăng {npg_dk5*100:.1f}% (vùng yếu: 0% ≤ x < 25%)')

        # Ba nhom, KHONG doi nguyen tac mua (van doi diem >= score_floor):
        #   cho       — qua het, chi cho phien bung no  -> DUOC MUA
        #   fa        — qua het TRU diem, diem 40-45     -> CHI DE MAT, khong mua
        #   khongdat  — con thieu thu khac
        fa_lo = cfg.get('fa_score_lo', 40)
        miss_khac = [m for m in miss if not m.startswith('điểm CANSLIM')]
        if s in LOAI:
            # Anh Son da tu tay gat ma nay. Quyet dinh cua nguoi dung tren moi
            # con so — nhung van noi ro ly do la "do anh loai", khong giau di.
            state, label = 'loai', 'ĐÃ LOẠI THỦ CÔNG'
        elif blk:
            state, label = 'chan', 'CỔNG RỦI RO CHẶN'
        elif not miss:
            state, label = 'cho', 'CHỜ ĐIỂM MUA'
        elif not miss_khac and fa_lo <= sc < cfg['score_floor']:
            state, label = 'fa', 'CHƯA ĐẠT VỀ CƠ BẢN'
        else:
            state, label = 'khongdat', 'CHƯA ĐỦ ĐIỀU KIỆN'

        out[s] = dict(
            sym=s, name=nm, exch=ex, price=round(close / 1000, 2),
            need_px=round(need_px / 1000, 2), thr=round(thr * 100, 1),
            need_vol=int(need_vol), vma20=int(vma),
            gtgd=round(gt / 1e9, 1), mktcap=round(mc / 1e9),
            base=(None if br is None else round(br * 100, 1)),
            score=round(sc, 1), rs=rs, sector=sect.get(s, 'Khác'),
            inuni=inuni, state=state, label=label, fund=int(fund),
            loai=(s in LOAI), tim=tim, tim_vi=tim_vi,
            block=(why if blk else None), miss=miss)
    return out
