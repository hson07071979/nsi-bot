# -*- coding: utf-8 -*-
"""TRA CUU TUNG MA — phien toi can gi de bot bao mua?

Voi moi ma trong vu tru, tinh ra DUNG hai nguong cua phien ke tiep:
  - gia dong cua toi thieu  = gia tham chieu x (1 + bien do bat tran)
  - khoi luong toi thieu    = 2 x khoi luong binh quan 20 phien
va cho biet ma dang o trang thai nao: da du diem mua, dang cho, chua vao nen,
hay bi cong rui ro chan han.
"""
import csv
import json
import datetime as dt
import numpy as np
from engine import risk_gate, canslim_score, as_of
from manual import loai as _loai
from vithe import phan_bo, tom_tat_danh_muc
from fa_ind import rmax as _rmax, rmin as _rmin


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


def build(d, I, tls, sect, cfg, topn, light='XANH', vi_the=None, nav=None):
    """Tra ve dict {sym: {...}} cho o tra cuu tren trang web."""
    # --- TAP MA DANG CAM ---
    # Ma da mua roi thi KHONG con la "cho diem mua" nua. Neu van de nhan cu thi
    # hai phien tran lien tiep se ra hai lenh mua cung mot ma — thanh 50% tai
    # khoan vao mot cho, vo ly. Bo may von da chan (`if sym in pos: continue`)
    # va so lenh that cung chan (`h['sym'] not in dang_cam`), nhung TRANG WEB va
    # CHUONG BAO thi chua biet — nen van hien "CHO DIEM MUA" cho ma dang cam.
    #
    # Gop ca hai quyen so: so chay cua bo may (`vi_the`) va so ghi tien
    # (`data/portfolio.json`, workflow da tai ve). Thieu file thi bo qua.
    _cam = {str(p.get('sym', '')).upper() for p in (vi_the or []) if p.get('sym')}
    for _p in ('data/portfolio.json', 'portfolio.json'):
        try:
            _P = json.load(open(_p, encoding='utf-8'))
            _cam |= {str(x.get('sym', '')).upper() for x in (_P.get('open') or [])
                     if x.get('sym') and (x.get('sh') or 0) > 0}
            break
        except Exception:
            continue

    # Trang thai danh muc hien tai — de biet con bao nhieu cho cho lenh moi.
    # Khong truyen thi coi nhu danh muc rong, va phan giai thich NOI RO dieu do.
    _dm_n, _dm_tong, _dm_nganh, _dm_tien = tom_tat_danh_muc(vi_the, nav) \
        if (vi_the is not None and nav) else (0, 0.0, {}, 1.0)
    S = [str(x) for x in d['sym']]
    cal = [str(x) for x in d['cal']]
    i = len(cal) - 1
    today = dt.date.fromisoformat(cal[i])
    NM = _names()
    LOAI = _loai()          # ma anh Son loai thu cong trong loai.txt
    MC, TV, AC = d['MarketCap'], d['TotalValue'], d['AdjClose']
    # ⚠️ NEN GIA PHAI TINH CHO PHIEN KE TIEP, KHONG PHAI PHIEN VUA CHOT.
    # `I['base_hi']` = shift(rmax(AC,30),1) — tuc nen tai dong k la cua so 30 phien
    # TRUOC dong k. Vay nen dung cho phien KE TIEP chinh la cua so ket thuc tai
    # phien vua chot, tuc rmax/rmin KHONG dich, lay o dong i.
    #
    # LOI CU (phat hien 15/09/2026 qua ca BVH): cho ra `base_rng[i]` — la nen cua
    # PHIEN VUA CHOT — nen `thresholds.json` mang mot con so TRE MOT PHIEN sang
    # phien sau. BVH nen 21,0% suot toi 11/09 roi tut con 16,1% o phien 14/09 (mot
    # dinh cu roi khoi cua so 30 phien). Co may cham dung 16,1% va MUA; lop quet
    # trong phien doc thresholds thay 21,0% -> state 'khongdat' -> khong bao gio
    # keu MUA -> so lenh that bo lo ca lenh. Do lai toan bo: 1/119 tin hieu bi bo
    # sot vi dung loi nay.
    #
    # Cac truong khac cua thresholds.json (ref, need_px, need_vol) DEU da huong ve
    # phien ke tiep roi; rieng nen thi khong. Day la sua cho khong nhat quan do.
    _hi30 = _rmax(d['AdjClose'], 30)
    _lo30 = _rmin(d['AdjClose'], 30)
    base_rng = (_hi30 - _lo30) / np.where(_lo30 > 0, _lo30, np.nan)

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
            rmul = 0.0
            sc = 0.0; fund = 0; npg_dk5 = None; tim, tim_vi = False, None
            _pts = {}; nh = None; vratio = None
        else:
            b, w, rmul = risk_gate(s, fa)
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
            # Giu state='cho' (verify_build.py va CSS dua vao no), chi doi NHAN.
            # Doi ca state se lam watchlist lech voi o tra cuu -> verify bao truot.
            state = 'cho'
            label = 'ĐANG CẦM' if s in _cam else 'CHỜ ĐIỂM MUA'
        elif not miss_khac and fa_lo <= sc < cfg['score_floor']:
            state, label = 'fa', 'CHƯA ĐẠT VỀ CƠ BẢN'
        else:
            state, label = 'khongdat', 'CHƯA ĐỦ ĐIỀU KIỆN'

        # MA DANG CAM PHAI NOI LA DANG CAM O MOI TRANG THAI, khong chi nhanh 'cho'.
        # Vi sao: file nay mo ta PHIEN KE TIEP. Mot ma vua mua xong bang cay bung
        # no hom qua thi cay do da nam trong cua so 30 phien => nen gia rong ra =>
        # state tut ve 'khongdat' kem dong "chua tao duoc nen gia chat". Dung ve
        # mot lenh MUA MOI, nhung doc nham thanh "he thong cham no truot" (BSR,
        # 15/09/2026: da mua 8.200 cp luc 30,45 ma trang Chi tiet ma van ghi CHUA
        # DU DIEU KIEN). Giu nguyen `state` vi verify_build.py va CSS dua vao no.
        if s in _cam:
            label = ('ĐANG CẦM' if state in ('cho', 'khongdat', 'fa')
                     else 'ĐANG CẦM · ' + label)

        # --- NEU LENH NAY DUOC VAO THI VAO BAO NHIEU PHAN TRAM NAV ---
        # Dung chung ham voi chuong bao va thresholds.json, va ham do tai hien
        # dung cong thuc trong engine2.run() (da doi chung 119/119 lenh that).
        if blk or s in LOAI:
            vt = None
        else:
            vt = phan_bo(light, rmul=rmul, base_rng=br, cfg=cfg,
                         so_ma_dang_cam=_dm_n, tong_dang_cam=_dm_tong,
                         nganh_dang_cam=_dm_nganh.get(sect.get(s, 'Khác'), 0.0),
                         tien_mat=_dm_tien)

        # --- NHOM "CHI VUONG CONG CFO" — de anh Son soi tay ---
        # Luat KHONG doi mot chu: ma nay VAN bi chan, van khong vao watchlist,
        # bot van khong mua. Day chi la mot cai nhan de trang web tach rieng ra.
        # Dieu kien: qua HET moi dieu kien sang loc (miss rong) va thu DUY NHAT
        # chan no la cong CFO. Neu con thieu thu khac thi khong tinh — vi luc do
        # bo cong CFO di no cung chua du dieu kien.
        dang_cam = s in _cam
        cfo_only = bool(blk and why == 'CFO < 0' and not miss and s not in LOAI)
        cfo_ty = None
        if fa is not None and fa.get('cfo_ttm') is not None:
            try:
                cfo_ty = round(float(fa['cfo_ttm']) / 1e9, 1)
            except (TypeError, ValueError):
                cfo_ty = None

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
            volat=round(volat * 100, 2),
            size_pct=(vt['pct'] if vt else None),
            size_tran=(vt['tran'] if vt else None),
            size_1dong=(vt['mot_dong'] if vt else None),
            size_vi_sao=(vt['vi_sao'] if vt else None),
            size_thuc=(vt['pct_thuc'] if vt else None),
            size_vao_duoc=(vt['vao_duoc'] if vt else None),
            cfo_only=cfo_only, cfo_ty=cfo_ty, dang_cam=dang_cam)
    return out
