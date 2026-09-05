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


# ============================================================
# BẢNG KIỂM CHI TIẾT — CHỈ PHƠI BÀY, KHÔNG CHẤM LẠI
# ============================================================
# Mọi con số ở đây đều ĐÃ tính ở trên rồi. Hai hàm này không tính lại điều kiện
# nào — chỉ đóng gói (giá trị thực, ngưỡng, đạt/trượt) cho trang web hiện ra.
# Với CANSLIM thì đạt/trượt lấy THẲNG từ `_pts` của `canslim_score`, nên trang
# web không thể nói khác bot dù có sửa gì ở đây đi nữa.
#
# Đừng bao giờ gõ số ngưỡng trực tiếp vào đây. Luôn truyền từ `cfg`.
# Đổi mã điều kiện thì phải đổi cả bảng `BK` trong `site/p11.js`.

def _ck(code, actual, bench, op, dat=None, diem=None):
    if dat == 'info':
        tt = 'info'
    else:
        if dat is None:
            if actual is None or bench is None:
                dat = None
            elif op == '>=':
                dat = actual >= bench
            elif op == '<=':
                dat = actual <= bench
        tt = 'na' if dat is None else ('ok' if dat else 'no')
    return [code,
            None if actual is None else round(float(actual), 2),
            None if bench is None else round(float(bench), 2),
            tt,
            None if diem is None else round(float(diem), 1)]


def _pc(x, nd=1):
    """Phan so -> phan tram, giu nguyen None."""
    return None if (x is None or x != x) else round(float(x) * 100, nd)


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
            _pts = {}; nh = None; vratio = None
        else:
            b, w, _ = risk_gate(s, fa)
            blk, why = b, w
            npg_dk5 = fa.get('npat_yoy')
            tim, tim_vi = bool(fa.get('tim')), fa.get('tim_ly_do')
            nh = float(AC[i, j] / I['hi52'][i, j] - 1) if I['hi52'][i, j] > 0 else None
            vratio = float(I['volr'][i, j]) if I['volr'][i, j] == I['volr'][i, j] else None
            sc, _pts = canslim_score(fa, I['rs'][i, j], I['mom3'][i, j],
                                     nh, vratio, gt)
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

        # ---- BẢNG KIỂM CHI TIẾT (không đổi logic, chỉ phơi ra) ----
        chk = []
        ghi = {}          # ghi chu dong, chi co khi that su can

        if fa is not None:
            if fa.get('bad_quality'):
                ghi['C1'] = 'Lợi nhuận bất thường >30% — C1/C2/C3 bị ép về 0'

            def _cs(code, val, bench):
                """Dat/truot lay THANG tu _pts — nguon su that duy nhat."""
                return _ck(code, _pc(val), bench, '>=',
                           dat=(None if val is None else _pts.get(code, 0) > 0),
                           diem=_pts.get(code, 0))

            chk += [
                _cs('C1', fa.get('npat_yoy'), 25),
                _cs('C2', fa.get('rev_yoy'),  15),
                _ck('C3', (1 if fa.get('accel') else 0), 1, '>=',
                    dat=(_pts.get('C3', 0) > 0), diem=_pts.get('C3', 0)),
                _cs('A1', fa.get('cagr3'), 20),
                _cs('A2', fa.get('roe'),   17),
                _ck('N', _pc(nh), -15, '>=',
                    dat=(None if nh is None else _pts.get('N', 0) > 0),
                    diem=_pts.get('N', 0)),
                _ck('S', vratio, 1.2, '>=',
                    dat=(None if vratio is None else _pts.get('S', 0) > 0),
                    diem=_pts.get('S', 0)),
                _ck('L', rs, 70, '>=',
                    dat=(None if rs is None else _pts.get('L', 0) > 0),
                    diem=_pts.get('L', 0)),
                _ck('I', gt / 1e9, 15, '>=',
                    dat=(_pts.get('I', 0) > 0), diem=_pts.get('I', 0)),
                _ck('Mom', _pc(I['mom3'][i, j]), None, 'thang',
                    dat='info', diem=_pts.get('Mom', 0)),
            ]

        # Cong sang loc — DUNG bang cac dieu kien da dung ra `miss` o tren.
        if br is None:
            ghi['NEN'] = 'Chưa dựng được nền — hệ thống tính là KHÔNG ĐẠT'
        if npg_dk5 is None:
            ghi['DK5'] = 'Chưa có dữ liệu — hệ thống cho qua điều kiện này'
        if blk:
            ghi['RUIRO'] = why

        chk += [
            _ck('UNI',   (1 if inuni else 0), 1, '>=', dat=inuni),
            _ck('MC',    mc / 1e9, cfg['min_mktcap'] / 1e9, '>='),
            _ck('GT',    gt / 1e9, cfg['gtgd_min'] / 1e9, '>='),
            _ck('NEN',   (None if br is None else br * 100),
                 cfg['base_range'] * 100, '<=',
                 dat=(False if br is None else br <= cfg['base_range'])),
            _ck('VOLAT', volat * 100, cfg['volat_min'] * 100, '>='),
            _ck('DIEM',  sc, cfg['score_floor'], '>='),
            _ck('DK5',   _pc(npg_dk5), None, 'band',
                 dat=(True if npg_dk5 is None else not (0 <= npg_dk5 < 0.25))),
            _ck('RUIRO', (0 if blk else 1), 1, '>=', dat=(not blk)),
        ]

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
            block=(why if blk else None), miss=miss,
            chk=chk, chk_ghi=ghi,
            n_thieu=sum(1 for c in chk if c[3] == 'no' and c[0] in
                        ('UNI', 'MC', 'GT', 'NEN', 'VOLAT', 'DIEM', 'DK5', 'RUIRO')),
            volat=round(volat * 100, 2))
    return out
