# -*- coding: utf-8 -*-
"""Giải ngân, quản trị rủi ro, xác suất chạm mục tiêu và điểm 70/30 cho Lọc port.

Mọi ngưỡng ở đây đến từ nghiên cứu R38/R39 (research/r38_giai_ngan.py, research/r39_dinh_gia.py,
evidence/r38_giai_ngan.json, evidence/r39_dinh_gia.json) và quyết định của anh Sơn ngày 15/10/2026:

  Trạng thái thị trường (VN-Index so với đỉnh 250 phiên):
    hoảng loạn ≤ −20%  → 2 đợt 60/40      (R38: lúc hoảng loạn mua sớm thắng; chia nhỏ mất 2–6 điểm %)
    còn lại            → 3 đợt 1/3        (R38: đuôi lỗ p10 −44,7% → −31,3%, giá mất ~1 điểm %)
  Đợt sau chỉ khi ĐI NGANG ≥ 20 phiên kể từ đợt trước: biên độ đóng cửa ≤ 8%, đầu–cuối lệch ≤ 4%,
    nửa sau cửa sổ không tạo đáy mới.  Không có nền sau 120 phiên → mua nốt nếu luận điểm còn đúng.
  Chạy luôn: đóng cửa ≥ giá đợt 1 +10% trước khi kịp đợt sau → mua NỬA phần còn lại ngay, nửa còn lại
    khi hồi về MA20 (≤ MA20 × 1,01) trong 60 phiên, quá hạn thì mua nốt. KHÔNG bỏ lỡ (R38: bỏ lỡ −8 điểm %/năm).
  Rủi ro (anh Sơn chốt: "nới nhưng vẫn phải quản trị rủi ro"):
    giá < giá vốn bình quân −7%  → NGỪNG mua thêm, rà lại luận điểm
    giá < giá vốn bình quân −15% → BÁN hết (kỷ luật)
    VN-Index đóng cửa dưới mốc dừng danh mục → hoãn mọi đợt mới
    mỗi mã ≤ 20% NAV; "nhiệt" danh mục (tổng tỷ trọng × khoảng cách tới mức bán) ≤ 10% NAV
  R38 cho quy tắc này: lợi suất TB 12 tháng +14,0%, mã xấu nhất −26,5%, Monte Carlo danh mục 8 mã
    p5 −5,7%, xác suất cả danh mục lỗ quá 10% sau 12 tháng 0,6% (so với 4,0% nếu mua 1 lần, không dừng).
"""
from __future__ import annotations

from math import erf, log, sqrt

HOANG_LOAN, CANG_THANG = -0.20, -0.10
NEN_PHIEN, NEN_BIEN, NEN_TROI = 20, 0.08, 0.04
CHAY = 0.10
HET_HAN = 120
HOI_MA20_HAN = 60
NGUNG_MUA, BAN = 0.07, 0.15
TRAN_MA, NHIET_TOI_DA = 12.5, 10.0
# Lớp DANH MỤC (R40, anh Sơn chốt 15/10/2026): mô phỏng danh mục theo lịch 2020→2026 cho thấy cắt lỗ từng mã KHÔNG
# chặn được sụt giảm danh mục (−54% năm 2022: cắt mã này lại mua ngay mã 'rẻ' khác đang rơi). Hai lớp sau mới chặn được:
MO_MOI_VNI = -0.10      # chỉ MỞ MÃ MỚI khi VN-Index thấp hơn đỉnh 250 phiên ≥ 10% (lúc bình thường 'rẻ' là bẫy giá trị)
NHIP_MO, NHIP_PHIEN = 2, 20   # tối đa 2 mã mới mỗi 20 phiên — rải tiền theo thời gian khi thị trường sập
K_TOI_DA = 8            # tối đa 8 mã, mỗi mã 12,5% NAV
# R40: +171,7% (16,2%/năm) 14/02/2020→15/10/2026, sụt giảm danh mục lớn nhất −18,7%; VN-Index +81,2%, −40,3%.
# Monte Carlo (bỏ ngẫu nhiên 30% cơ hội, 300 lần): trung vị 15,9%/năm, p5 11,8%/năm, sụt giảm p95 21,5%.
LIM = {'HOSE': 0.075, 'HNX': 0.105, 'UPCOM': 0.155}


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


# ---------------------------------------------------------------- trạng thái thị trường
def trang_thai_tt(D: dict) -> dict:
    reg = [r for r in (D.get('regime') or []) if _num(r.get('vni'))]
    if not reg:
        return dict(ten='không rõ', so_dot=3, ty_le=[1 / 3] * 3)
    v = [r['vni'] for r in reg[-250:]]
    dd = v[-1] / max(v) - 1
    if dd <= HOANG_LOAN:
        ten, so, tl = 'hoảng loạn', 2, [0.6, 0.4]
    elif dd <= CANG_THANG:
        ten, so, tl = 'căng thẳng', 3, [1 / 3] * 3
    else:
        ten, so, tl = 'bình thường', 3, [1 / 3] * 3
    return dict(ten=ten, vni=v[-1], dinh_250=max(v), dd=round(dd * 100, 1), so_dot=so, ty_le=tl,
                den=reg[-1].get('light'), ngay=reg[-1].get('date'))


# ---------------------------------------------------------------- chuỗi giá (nến trang web) đã chỉnh khoảng nhảy
def chuoi_gia(D: dict, sym: str, san: str | None = None) -> tuple[list[str], list[float]]:
    bars = ((D.get('candles') or {}).get(sym) or {}).get('bars') or []
    d = [b[0] for b in bars if _num(b[4])]
    c = [float(b[4]) for b in bars if _num(b[4])]
    lim = LIM.get(str(san or 'HOSE').upper(), 0.075)
    for i in range(len(c) - 1, 0, -1):            # chia tách/cổ tức: chỉnh ngược quá khứ
        r = c[i] / c[i - 1] - 1
        if r < -lim:
            k = c[i] / c[i - 1]
            for j in range(i):
                c[j] *= k
    return d, c


# ---------------------------------------------------------------- xác suất chạm mục tiêu
def xac_suat_cham(c: list[float], T: float, H: int) -> float | None:
    """Bước ngẫu nhiên không trôi, σ = độ lệch chuẩn lợi suất ngày 60 phiên.
    R39: dự báo 50% → thực tế 51%, 70% → 65–67% (60–120 phiên, 1.363 lần kiểm)."""
    if not c or len(c) < 41 or not T or T <= 0:
        return None
    p = c[-1]
    if T <= p:
        return 1.0
    r = [log(c[i] / c[i - 1]) for i in range(max(1, len(c) - 60), len(c)) if c[i - 1] > 0 and c[i] > 0]
    if len(r) < 40:
        return None
    m = sum(r) / len(r)
    sd = (sum((x - m) ** 2 for x in r) / (len(r) - 1)) ** 0.5
    if sd <= 0:
        return None
    z = log(T / p) / (sd * sqrt(H))
    return round(2 * (1 - 0.5 * (1 + erf(z / sqrt(2)))), 3)


# ---------------------------------------------------------------- vị thế từ sổ lệnh
def vi_the(so_lenh: dict, sym: str) -> dict:
    ls = sorted([l for l in (so_lenh or {}).get('lenh') or [] if str(l.get('ma', '')).upper() == sym],
                key=lambda l: l.get('ngay', ''))
    von, cp, mua = 0.0, 0.0, []
    for l in ls:
        tl, g = float(l.get('ty_le') or 0), _num(l.get('gia'))
        if tl <= 0 or not g:
            continue
        if l.get('loai', 'mua') == 'mua':
            von += tl
            cp += tl / g
            mua.append(dict(ngay=l.get('ngay'), ty_le=tl, gia=g))
        elif von > 0:
            phan = min(tl / von, 1.0)
            cp -= cp * phan
            von -= von * phan
    return dict(von=round(von, 3), cp=cp, gia_von=(von / cp) if cp > 0 else None, mua=mua)


def _phien_tu(dates: list[str], ngay: str | None) -> int | None:
    if not ngay or not dates:
        return None
    return sum(1 for d in dates if d > ngay)


def nen(c: list[float], sau: int) -> dict:
    """Đi ngang NEN_PHIEN phiên, cửa sổ phải nằm hoàn toàn sau `sau` phiên cuối (số phiên kể từ đợt trước)."""
    if len(c) < NEN_PHIEN or (sau is not None and sau < NEN_PHIEN):
        return dict(co=False, phien_da_di_ngang=None)
    # đếm số phiên đi ngang liên tục gần nhất (để hiển thị tiến độ)
    w = c[-NEN_PHIEN:]
    h = NEN_PHIEN // 2
    bien = max(w) / min(w) - 1
    troi = abs(w[-1] / w[0] - 1)
    day_moi = min(w[-h:]) < min(w[:-h])
    co = bien <= NEN_BIEN and troi <= NEN_TROI and not day_moi
    k = 0
    for n in range(2, min(len(c), 120) + 1):
        x = c[-n:]
        if max(x) / min(x) - 1 <= NEN_BIEN:
            k = n
        else:
            break
    return dict(co=co, bien=round(bien * 100, 1), troi=round(troi * 100, 1), day_moi=day_moi, phien_di_ngang=k)


# ---------------------------------------------------------------- kế hoạch cho từng mã
def ke_hoach(t: dict, vt_muc_tieu: float | None, tt: dict, dates: list[str], c: list[float],
             so_lenh: dict, san_sang: dict | None, kc_cham: list[dict], dung_vni: float | None) -> dict:
    sym = t['ma']
    v = vi_the(so_lenh, sym)
    p = c[-1] if c else None
    muc = vt_muc_tieu or 0.0
    out = dict(ty_trong_muc_tieu=muc, da_giai_ngan=v['von'], gia_von=round(v['gia_von'], 3) if v['gia_von'] else None,
               so_lan_mua=len(v['mua']), trang_thai_tt=tt.get('ten'))
    if t.get('trang_thai') not in ('trong_port',) or muc <= 0:
        out.update(hanh_dong='Không giải ngân (không nằm trong danh mục hoặc tỷ trọng 0).', muc='cho')
        return out
    k2_sai = any(k.get('ket_qua') == 'SAI' and k.get('loai') == 'funda' for k in kc_cham or [])
    ma20 = sum(c[-20:]) / 20 if len(c) >= 20 else None
    vni_duoi = bool(dung_vni and tt.get('vni') and tt['vni'] < dung_vni)
    tl = tt.get('ty_le') or [1 / 3] * 3
    # ---- chưa có lệnh nào
    if not v['mua']:
        ss = (san_sang or {}).get('ket_luan')
        if vni_duoi:
            out.update(hanh_dong=f'Hoãn: VN-Index dưới mốc dừng {dung_vni:,.1f}.', muc='hoan')
        elif (tt.get('dd') is not None) and tt['dd'] / 100 > MO_MOI_VNI:
            out.update(hanh_dong=f'Không mở mã mới: VN-Index chỉ {tt["dd"]}% so với đỉnh 250 phiên (cần ≤ −10%) — lúc bình thường "rẻ" dễ là bẫy giá trị (R39/R40).', muc='cho')
        elif ss == 'ĐỦ ĐỂ XUỐNG TIỀN':
            out.update(hanh_dong=f'Đợt 1: mua {tl[0]*100:.0f}% tỷ trọng mục tiêu = {muc*tl[0]:.1f}% NAV '
                                 f'(thị trường {tt.get("ten")}, kế hoạch {len(tl)} đợt).', muc='mua', ty_le_mua=round(muc * tl[0], 2))
        else:
            out.update(hanh_dong=f'Chưa mua: {ss or "chưa chấm sẵn sàng"}.', muc='cho')
        return out
    # ---- đã có vị thế
    gv = v['gia_von']
    lo = (p / gv - 1) if (p and gv) else None
    out['lai_lo_pct'] = round(lo * 100, 1) if lo is not None else None
    out['gia_ngung_mua'] = round(gv * (1 - NGUNG_MUA), 3)
    out['gia_ban'] = round(gv * (1 - BAN), 3)
    if lo is not None and lo <= -BAN:
        out.update(hanh_dong=f'BÁN toàn bộ: đóng cửa {p:,.2f} dưới giá vốn −15% ({out["gia_ban"]:,.2f}) — kỷ luật đã chốt.', muc='ban')
        return out
    if k2_sai:
        out.update(hanh_dong='Mốc cơ bản K2 SAI → rà lại luận điểm; theo quy tắc: đóng luận điểm, không dời mốc.', muc='ra_soat')
        return out
    con = max(muc - v['von'], 0.0)
    if con <= 1e-6:
        out.update(hanh_dong='Đã đủ tỷ trọng mục tiêu. Giữ; theo dõi mốc K và mức bán.', muc='giu')
        return out
    if lo is not None and lo <= -NGUNG_MUA:
        out.update(hanh_dong=f'NGỪNG mua thêm: giá dưới giá vốn −7% ({out["gia_ngung_mua"]:,.2f}). Rà lại pitch trước khi làm gì tiếp.', muc='ngung')
        return out
    if vni_duoi:
        out.update(hanh_dong=f'Hoãn đợt tiếp: VN-Index dưới mốc dừng {dung_vni:,.1f}.', muc='hoan')
        return out
    p1, n1 = v['mua'][0]['gia'], v['mua'][0]['ngay']
    tu_dot_truoc = _phien_tu(dates, v['mua'][-1]['ngay'])
    tu_dot_1 = _phien_tu(dates, n1)
    # chạy luôn trước đợt 2?
    chay = len(v['mua']) == 1 and p and p >= p1 * (1 + CHAY)
    nb = nen(c, tu_dot_truoc)
    out['nen'] = nb
    out['phien_tu_dot_truoc'] = tu_dot_truoc
    if chay or (len(v['mua']) >= 2 and v['mua'][-1]['gia'] >= p1 * (1 + CHAY) and v['von'] < muc):
        if len(v['mua']) == 1:
            out.update(hanh_dong=f'CHẠY +{(p/p1-1)*100:.0f}% so với đợt 1: mua NGAY nửa phần còn lại = {con/2:.1f}% NAV; '
                                 f'nửa còn lại ({con/2:.1f}% NAV) khi đóng cửa ≤ MA20×1,01 ({(ma20 or 0)*1.01:,.2f}) trong 60 phiên, quá hạn thì mua nốt.',
                       muc='mua', ty_le_mua=round(con / 2, 2))
        else:
            hoi = ma20 and p <= ma20 * 1.01
            qua_han = tu_dot_truoc is not None and tu_dot_truoc >= HOI_MA20_HAN
            out.update(hanh_dong=(f'Mua nốt {con:.1f}% NAV: ' + ('đã hồi về MA20.' if hoi else 'quá 60 phiên chờ hồi.')) if (hoi or qua_han)
                       else f'Chờ hồi về MA20×1,01 ({(ma20 or 0)*1.01:,.2f}) để mua nốt {con:.1f}% NAV (còn {HOI_MA20_HAN-(tu_dot_truoc or 0)} phiên).',
                       muc='mua' if (hoi or qua_han) else 'cho', ty_le_mua=round(con, 2) if (hoi or qua_han) else None)
        return out
    so_dot = len(tl)
    dot_ke = min(len(v['mua']), so_dot - 1)
    w_ke = min(muc * tl[dot_ke], con)
    if nb.get('co'):
        out.update(hanh_dong=f'Đợt {len(v["mua"])+1}: đã đi ngang {NEN_PHIEN} phiên (biên {nb["bien"]}%) → mua {w_ke:.1f}% NAV.', muc='mua', ty_le_mua=round(w_ke, 2))
    elif tu_dot_1 is not None and tu_dot_1 >= HET_HAN:
        out.update(hanh_dong=f'Quá {HET_HAN} phiên không có nền: luận điểm còn đúng → mua nốt {con:.1f}% NAV.', muc='mua', ty_le_mua=round(con, 2))
    else:
        can = max(NEN_PHIEN - (tu_dot_truoc or 0), 0)
        out.update(hanh_dong=(f'Chờ nền: cần đi ngang {NEN_PHIEN} phiên sau đợt trước (còn ít nhất {can} phiên)' if can else
                              f'Chờ nền: {NEN_PHIEN} phiên gần nhất chưa đủ đi ngang (biên {nb.get("bien")}%, tạo đáy mới: {"có" if nb.get("day_moi") else "không"})')
                   + f'. Đợt kế {w_ke:.1f}% NAV. Hết hạn sau {max(HET_HAN-(tu_dot_1 or 0),0)} phiên.', muc='cho')
    return out


def mo_gan_day(so_lenh: dict, dates: list[str]) -> dict:
    """Số mã đang nắm và số mã MỚI mở trong NHIP_PHIEN phiên gần nhất (theo ngày mua đầu tiên của từng mã)."""
    dau, von = {}, {}
    for l in sorted((so_lenh or {}).get('lenh') or [], key=lambda x: x.get('ngay', '')):
        m = str(l.get('ma', '')).upper()
        if l.get('loai', 'mua') == 'mua':
            dau.setdefault(m, l.get('ngay'))
    dang = [m for m in dau if (vi_the(so_lenh, m)['von'] or 0) > 1e-9]
    gan = [m for m in dang if (_phien_tu(dates, dau[m]) or 0) < NHIP_PHIEN]
    con = None
    if gan:
        cu_nhat = min(dau[m] for m in gan)
        con = NHIP_PHIEN - (_phien_tu(dates, cu_nhat) or 0)
    return dict(dang_nam=len(dang), mo_gan=len(gan), ma_mo_gan=gan, phien_toi_luot=con)


def xep_luot(the: list[dict], mg: dict) -> dict:
    """Trong các mã CHƯA có vị thế mà kế hoạch nói 'mua đợt 1', chỉ cho mở theo điểm 70/30 cao nhất,
    tối đa (NHIP_MO − số mã mới mở 20 phiên qua) và không vượt K_TOI_DA mã. Các mã còn lại: chờ lượt."""
    slot = max(0, min(NHIP_MO - mg['mo_gan'], K_TOI_DA - mg['dang_nam']))
    ung = [x for x in the if x.get('giai_ngan', {}).get('muc') == 'mua' and not x['giai_ngan'].get('so_lan_mua')]
    ung.sort(key=lambda x: -((x.get('diem_70_30') or {}).get('tong') or 0))
    for k, x in enumerate(ung):
        g = x['giai_ngan']
        g['thu_tu'] = k + 1
        if k >= slot:
            ly = (f'đã đủ {K_TOI_DA} mã' if mg['dang_nam'] >= K_TOI_DA else
                  f'đã mở {mg["mo_gan"]} mã mới trong {NHIP_PHIEN} phiên' + (f', lượt kế sau {mg["phien_toi_luot"]} phiên' if mg.get('phien_toi_luot') else '')
                  if mg['mo_gan'] >= NHIP_MO else f'xếp thứ {k+1} theo điểm 70/30, mỗi {NHIP_PHIEN} phiên chỉ mở {NHIP_MO} mã')
            g['hanh_dong'] = f'Chờ lượt ({ly}). Khi tới lượt: ' + g['hanh_dong']
            g['muc'] = 'cho_luot'
            g.pop('ty_le_mua', None)
    return dict(slot=slot, uu_tien=[x['luan']['ma'] for x in ung], **mg)


def nhiet_danh_muc(kh: list[dict]) -> dict:
    """'Nhiệt' = số % NAV sẽ mất thêm nếu mọi vị thế đang có rơi đúng tới mức bán (giá vốn −15%)."""
    tong, chi_tiet = 0.0, []
    for k in kh:
        v, lo = k.get('da_giai_ngan') or 0, k.get('lai_lo_pct')
        if v and lo is not None:
            mat = max(v * (1 + lo / 100) - v * (1 - BAN), 0.0)
            tong += mat
            chi_tiet.append(dict(ma=k.get('ma'), mat_toi_da=round(mat, 2)))
    full = sum(min(k.get('ty_trong_muc_tieu') or 0, TRAN_MA) for k in kh) * BAN
    return dict(hien_tai=round(tong, 2), khi_du_ty_trong=round(full, 2), tran=NHIET_TOI_DA,
                vuot=tong > NHIET_TOI_DA, chi_tiet=chi_tiet,
                vi_pham_tran_ma=[k.get('ma') for k in kh if (k.get('ty_trong_muc_tieu') or 0) > TRAN_MA])


# ---------------------------------------------------------------- điểm 70/30
def diem_70_30(t: dict, loc: dict | None, tt: dict, san_sang: dict | None, kc_cham: list[dict]) -> dict:
    """Pitch 70 = định giá so với chính nó 20 + trạng thái thị trường 20 + độ chặt lập luận 15 + 'vì sao thị trường
    định giá sai' 15 (Claude/anh Sơn chấm theo thang trong luận điểm: pitch_diem.dinh_gia_sai 0–15).
    Kết quả 30 = LN 4 quý 10 + ROE 10 + mốc K2 10.
    Cơ sở (R39): tăng trưởng LN/DT gần như không dự báo được lợi suất (IC ≈ 0, ai cũng thấy); định giá so với
    chính nó IC 0,12–0,17 (2022–25), 0,18 khi hoảng loạn; tốt + rẻ lúc bình thường là bẫy giá trị (−12,5 điểm so VNI)."""
    loc = loc or {}
    rel = []
    for a, b in (('pe', 'pe_tv'), ('pb', 'pb_tv')):
        x, y = _num(loc.get(a)), _num(loc.get(b))
        if x and y and x > 0 and y > 0:
            rel.append(x / y)
    r = sum(rel) / len(rel) if rel else None
    d_dg = 0 if r is None else (20 if r <= 0.6 else 14 if r <= 0.8 else 7 if r <= 1.0 else 0)
    d_tt = {'hoảng loạn': 20, 'căng thẳng': 12, 'bình thường': 4}.get(tt.get('ten'), 8)
    ss = san_sang or {}
    d_ld = round(15 * (ss.get('dat') or 0) / (ss.get('tong') or 9))
    pd_ = t.get('pitch_diem') or {}
    d_sai = max(0, min(15, int(pd_.get('dinh_gia_sai') or 0)))
    ny, roe = _num(loc.get('np4_yoy')), _num(loc.get('roe'))
    d_ln = 0 if ny is None else (10 if ny >= 15 else 6 if ny >= 0 else 0)
    d_roe = 0 if roe is None else (10 if roe >= 20 else 7 if roe >= 15 else 4 if roe >= 10 else 0)
    k2 = next((k for k in kc_cham or [] if k.get('id') == 'K2'), None)
    d_k2 = 5 if not k2 or k2.get('trang_thai') == 'mo' else (10 if k2.get('ket_qua') == 'ĐÚNG' else 0)
    pitch = d_dg + d_tt + d_ld + d_sai
    kq = d_ln + d_roe + d_k2
    return dict(tong=pitch + kq, pitch=pitch, ket_qua=kq,
                chi_tiet=dict(dinh_gia=d_dg, dinh_gia_rel=round(r, 2) if r else None, thi_truong=d_tt, lap_luan=d_ld,
                              dinh_gia_sai=d_sai, dinh_gia_sai_ly_do=pd_.get('ly_do'), loi_nhuan=d_ln, roe=d_roe, k2=d_k2))
