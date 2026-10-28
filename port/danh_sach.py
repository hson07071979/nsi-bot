# -*- coding: utf-8 -*-
"""DANH SÁCH GIẢI NGÂN CỦA PORT (anh Sơn chốt 27–28/10/2026).

Port dành cho khách đầu tư theo giá trị: giải ngân NGAY khi mã đang ở nền thấp, nền chặt — khác bot
(mua theo dòng tiền khi phá nền). Tối đa 10 mã có tiền.

  1. Vũ trụ = pool TOP110 + watchlist NSI (pool.py). LOẠI CỨNG nền cao (cách đỉnh 250 phiên chưa tới −15%,
     hoặc biên độ 30 phiên > 20%). Qua lọc thì XẾP THEO ĐỘ CHẶT CỦA NỀN — càng chặt càng trước.
  2. Bốn điều kiện mua cho mã bị hạ định giá (anh Sơn duyệt 28/10) — code đo bằng số, Claude xác nhận trong luận điểm:
       a. Lợi nhuận tăng là thật: LN 4 quý tăng, không phải lãi bất thường, tiền từ kinh doanh 12 tháng dương
          (ngân hàng / chứng khoán / bảo hiểm không xét dòng tiền kinh doanh).
       b. Tốc độ tăng không chậm lại: PEG hiện tại ≤ PEG lúc giá ở đỉnh 250 phiên (P/E ÷ tăng trưởng LN 4 quý).
          Lúc đỉnh lợi nhuận không tăng thì chỉ cần hiện tại đang tăng.
       c. Lý do giảm nằm ngoài doanh nghiệp: cả ngành cũng cách đỉnh ≥ 10%, và mã không rơi sâu hơn ngành quá
          15 điểm % (rơi riêng lẻ = vấn đề của chính công ty).
       d. Đã cân bằng: nền 30 phiên ≤ 12% và 10 phiên gần nhất không tạo đáy mới so với 50 phiên trước đó.
  3. Hai danh sách để riêng:
       GIẢI NGÂN       — luận điểm ĐỦ KHUNG (hàm du_khung), kết luận ĐỦ ĐỂ XUỐNG TIỀN, điểm 70/30 ≥ 60, qua lọc,
                         qua đủ 4 điều kiện. Tỷ trọng 12% (≥70 điểm) / 8% (60–69), đợt 1 vào ngay.
       CẦN THÊM BẰNG CHỨNG — luận điểm còn thiếu phần nào / kết luận CHỜ PHÉP THỬ / chưa qua đủ 4 điều kiện: tối
                         đa đợt 1, 4% NAV (luật CHỜ PHÉP THỬ). Giải ngân xếp sau danh sách trên, chung trần 10 mã.
     Mã ĐANG CẦM mà trượt lọc / rơi khỏi hai danh sách: GIỮ, ngừng mua thêm; chỉ bán khi −15% hoặc luận điểm
     bị loại (anh Sơn 28/10). Nền chặt lại thì tự vào lại.
  4. Ứng viên = mã qua lọc chưa có luận điểm, xếp theo độ chặt — đầu vào cho Claude viết luận điểm ở kỳ review.
"""
from __future__ import annotations

import bisect
from datetime import date

import numpy as np

import loc_quy as LQ

TOI_DA_MA = 10
NEN_CAN_BANG = 0.12
NGANH_GIAM_TOI_THIEU = -0.10
LECH_NGANH_TOI_DA = -0.15
DIEM_TOI_THIEU = 60
NGANH_TAI_CHINH = ('Ngân hàng', 'Dịch vụ tài chính', 'Bảo hiểm')
DU = 'ĐỦ ĐỂ XUỐNG TIỀN'
CHO = 'CHỜ PHÉP THỬ'

# ---- khung một luận điểm "đủ sâu" (anh Sơn 28/10: mọi mã giải ngân phải phân tích kỹ như nhau) ----
CHUOI = dict(vi_mo='khâu 1–2: quốc tế + vĩ mô Việt Nam truyền dẫn sang mã', nganh='khâu 3: ngành, chu kỳ, cung cầu',
             doanh_nghiep='khâu 4: vị thế doanh nghiệp', mo_hinh_kd='mô hình kinh doanh, tiền đến từ đâu',
             lanh_dao='lãnh đạo, cổ đông', chuoi_gia_tri='chuỗi giá trị', dan_nguoc_vi_mo='dẫn ngược lên vĩ mô')
KHAU = ('quoc_te', 'vi_mo_vn', 'nganh', 'doanh_nghiep', 'gia_sai')
SO = ('dinh_gia', 'kqkd', 'suc_khoe_tc')
GIA_SAI = dict(tin_xau='tin xấu là gì', co_that_su_xau='có thật sự xấu (bản chất)', trang_thai='trạng thái tin xấu',
               ky_vong_ngam='kỳ vọng ngầm trong giá', nguoi_ban_can_bien='người bán cận biên',
               counter='phản biện cùng trục', phep_thu='phép thử tin xấu tiếp theo')
THE_CATALYST = dict(catalyst='catalyst là gì', chi_truoc='tốn gì trước (capex/opex, tốc độ mở)',
                    hoa_von='điểm hòa vốn từng đơn vị', dieu_kien_can='điều kiện cần', dieu_kien_du='điều kiện đủ',
                    khi_nao_tien_ve='khi nào tiền về (từ lần mở rộng trước)', moc_quy='mốc theo quý',
                    phan_bien='phản biện')


def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def _du_chu(s, n=30) -> bool:
    return isinstance(s, str) and len(s.strip()) >= n


def _quy_key(lbl):
    try:
        q, y = str(lbl).upper().replace('Q', '').split('/')
        y = int(y)
        return (y + 2000 if y < 100 else y, int(q))
    except (ValueError, AttributeError):
        return None


def du_khung(t: dict, quy_moi: str | None = None) -> list[str]:
    """Các phần còn THIẾU của một luận điểm so với khung đủ sâu. Rỗng = đủ khung.
    quy_moi = quý BCTC mới nhất đã có (vd 'Q3/26') — luận điểm phải ghi đã đọc tới quý đó (`quy_bctc`)."""
    t = t or {}
    thieu = []
    ch = t.get('chuoi') or {}
    thieu += [v for k, v in CHUOI.items() if not _du_chu(ch.get(k))]
    if len([x for x in t.get('bull') or [] if _du_chu(x, 15)]) < 3:
        thieu.append('ít nhất 3 ý bull')
    if len([x for x in t.get('bear') or [] if _du_chu(x, 15)]) < 3:
        thieu.append('ít nhất 3 ý bear')
    pd = t.get('pitch_diem') or {}
    if any(_num((pd.get('khau') or {}).get(k)) is None for k in KHAU):
        thieu.append('điểm đủ 5 khâu')
    if any(_num((pd.get('so') or {}).get(k)) is None for k in SO):
        thieu.append('điểm phần số 30')
    if _num(pd.get('tong')) is None or not str(pd.get('ket_luan') or '').strip():
        thieu.append('tổng điểm + kết luận sau debate')
    gs = pd.get('gia_sai') or {}
    thieu += ['khâu 5 — ' + v for k, v in GIA_SAI.items() if not _du_chu(gs.get(k), 15)]
    if not _du_chu(t.get('vo_hieu')):
        thieu.append('điều kiện vô hiệu (bằng sự kiện)')
    if not any(k.get('loai') == 'funda' for k in t.get('kiem_chung') or []):
        thieu.append('mốc cơ bản chấm được bằng số')
    if not _du_chu(t.get('dinh_gia')):
        thieu.append('định giá so với chính nó và ngành')
    if not _du_chu(t.get('pitch')):
        thieu.append('pitch cho khách')
    if t.get('catalyst_can_chi_truoc'):
        tc = t.get('the_catalyst') or {}
        thieu += ['thẻ catalyst — ' + v for k, v in THE_CATALYST.items()
                  if not (tc.get(k) if k == 'moc_quy' else _du_chu(tc.get(k), 10))]
    if quy_moi:
        a, b = _quy_key(t.get('quy_bctc')), _quy_key(quy_moi)
        if b and (not a or a < b):
            thieu.append(f'chưa cập nhật BCTC {quy_moi}')
    return thieu


# ---------------------------------------------------------------- 4 điều kiện
def _i(B, d: str):
    if B is None or not B.lich:
        return None
    i = bisect.bisect_right(B.lich, d) - 1
    return i if i >= 0 else None


def _cuoi_quy(y: int, q: int) -> str:
    return {1: f'{y}-03-31', 2: f'{y}-06-30', 3: f'{y}-09-30', 4: f'{y}-12-31'}[q]


def _pe_tai(rows: list[dict], B, sym: str, d: str):
    """(P/E theo giá ngày d, tăng trưởng LN 4 quý %) dùng các quý đã công bố tới ngày d.
    P/E của quý (giá cuối quý) đổi sang giá ngày d bằng tỷ lệ giá điều chỉnh."""
    r = LQ.rows_den(rows, date.fromisoformat(d))
    if not r:
        return None, None
    so = LQ.diem_so(r) or {}
    g = so.get('np4_yoy')
    m = r[-1]
    pe = _num(m.get('pe'))
    a = B.c.get(sym) if B is not None else None
    i, iq = _i(B, d), _i(B, _cuoi_quy(m['y'], m['q']))
    if pe is None or not (0 < pe < 200) or a is None or i is None or iq is None or not (a[i] > 0 and a[iq] > 0):
        return None, g
    return round(pe * float(a[i]) / float(a[iq]), 2), g


def loi_4q(bc: dict | None):
    """Lợi nhuận KINH DOANH CỐT LÕI 4 quý gần nhất so với 4 quý trước đó, từ bctc.phan_tich (khoản 'loi':
    doanh nghiệp = lãi gộp − chi phí bán hàng, quản lý; ngân hàng = thu lãi + phí − chi phí hoạt động).
    → (nay, truoc, % thay đổi | None). Thiếu 8 quý thì None."""
    q = [x.get('loi') for x in (bc or {}).get('quy') or []]
    if len(q) < 8 or any(v is None for v in q[-8:]):
        return None
    nay, truoc = sum(q[-4:]), sum(q[-8:-4])
    pct = round((nay - truoc) / truoc * 100, 1) if truoc > 0 else None
    return dict(nay=round(nay, 1), truoc=round(truoc, 1), pct=pct)


def bon_dieu_kien(r: dict, rows: list[dict] | None, B, bc: dict | None = None) -> dict:
    """r = một dòng bảng pool (pool.dung_bang). Mỗi điều kiện: dat True/False/None (thiếu dữ liệu) + câu dễ đọc.
    bc = bctc.phan_tich của mã (nếu có) → điều kiện a xét thêm lợi nhuận kinh doanh cốt lõi 4 quý."""
    f, so = r.get('f') or {}, r.get('so') or {}
    lk = r.get('lk') or dict(cfo_ty=r.get('cfo_ty'), tim=r.get('tim'), tim_vi=r.get('tim_vi'))
    tc = any(k.lower() in (r.get('nganh') or '').lower() for k in NGANH_TAI_CHINH)
    out = {}
    # a. lợi nhuận tăng là thật
    np4, cfo, tim = _num(so.get('np4_yoy') if so else r.get('np4_yoy')), _num(lk.get('cfo_ty')), bool(lk.get('tim'))
    if np4 is None:
        out['a'] = dict(dat=None, cau='thiếu số lợi nhuận 4 quý')
    else:
        l4 = loi_4q(bc)
        cot_loi_ok = l4 is None or (l4['pct'] is not None and l4['pct'] > 0) or (l4['truoc'] <= 0 < l4['nay'])
        ok = np4 > 0 and not tim and cot_loi_ok and (tc or cfo is None or cfo > 0)
        if ok and not tc and cfo is None:
            ok = None                                   # chưa có số tiền từ kinh doanh → chưa xác nhận được
        cau = f'LN 4 quý {np4:+.1f}%'
        if l4:
            cau += (f' · lợi nhuận kinh doanh cốt lõi 4 quý {l4["pct"]:+.1f}%' if l4['pct'] is not None else
                    f' · lợi nhuận kinh doanh cốt lõi 4 quý {l4["truoc"]:,.0f} → {l4["nay"]:,.0f} tỷ'.replace(',', '.'))
        if tim:
            cau += ' · lãi bất thường: ' + str(lk.get('tim_vi') or '')
        if not tc:
            cau += f' · tiền từ kinh doanh 12 tháng {cfo:,.0f} tỷ'.replace(',', '.') if cfo is not None else ' · chưa có số tiền từ kinh doanh'
        out['a'] = dict(dat=ok, cau=cau)
    # b. tốc độ tăng không chậm lại (PEG hiện tại so với lúc đỉnh)
    sym = r['ma']
    a = B.c.get(sym) if B is not None else None
    if a is None or rows is None or not B.lich:
        out['b'] = dict(dat=None, cau='thiếu giá hoặc BCTC lịch sử')
    else:
        n = min(250, len(B.lich))
        w = a[-n:]
        if not np.isfinite(w).any():
            out['b'] = dict(dat=None, cau='thiếu giá')
        else:
            i_dinh = len(B.lich) - n + int(np.nanargmax(w))
            d_dinh, d_nay = B.lich[i_dinh], B.lich[-1]
            pe0, g0 = _pe_tai(rows, B, sym, d_dinh)
            pe1, g1 = _pe_tai(rows, B, sym, d_nay)
            if g1 is None:
                out['b'] = dict(dat=None, cau='thiếu tăng trưởng LN 4 quý hiện tại')
            elif g1 <= 0:
                out['b'] = dict(dat=False, cau=f'LN 4 quý đang giảm ({g1:+.1f}%)', g_nay=g1, g_dinh=g0)
            elif g0 is None or g0 <= 0:
                out['b'] = dict(dat=True, cau=f'lúc đỉnh ({d_dinh}) LN không tăng ({g0 if g0 is not None else "?"}%), nay tăng {g1:+.1f}%',
                                g_nay=g1, g_dinh=g0)
            elif pe0 is None or pe1 is None:
                ok = g1 >= g0
                out['b'] = dict(dat=ok, cau=f'tăng trưởng LN 4 quý {g0:+.1f}% lúc đỉnh → {g1:+.1f}% nay (thiếu P/E để tính PEG)',
                                g_nay=g1, g_dinh=g0)
            else:
                peg0, peg1 = pe0 / g0, pe1 / g1
                out['b'] = dict(dat=peg1 <= peg0, g_nay=g1, g_dinh=g0, peg_nay=round(peg1, 3), peg_dinh=round(peg0, 3),
                                cau=f'PEG {peg0:.2f} lúc đỉnh {d_dinh} (P/E {pe0:.1f}, LN 4 quý {g0:+.1f}%) → {peg1:.2f} nay '
                                    f'(P/E {pe1:.1f}, {g1:+.1f}%)')
    # c. lý do giảm nằm ngoài doanh nghiệp
    td, nt = _num(f.get('tu_dinh')), _num(r.get('nganh_tu_dinh'))
    if td is None or nt is None:
        out['c'] = dict(dat=None, cau='thiếu số so ngành')
    else:
        lech = td - nt
        out['c'] = dict(dat=nt <= NGANH_GIAM_TOI_THIEU and lech >= LECH_NGANH_TOI_DA,
                        cau=f'mã cách đỉnh {td * 100:.0f}%, cả ngành (trung vị) {nt * 100:.0f}% → lệch {lech * 100:+.0f} điểm %')
    # d. đã cân bằng
    nen = _num(f.get('nen30'))
    if a is None or nen is None or np.isfinite(a).sum() < 60:
        out['d'] = dict(dat=None, cau='thiếu giá 60 phiên')
    else:
        c = a[np.isfinite(a)]
        day_moi = float(np.min(c[-10:])) < float(np.min(c[-60:-10]))
        out['d'] = dict(dat=nen <= NEN_CAN_BANG and not day_moi,
                        cau=f'nền 30 phiên {nen * 100:.1f}%' + (' · 10 phiên gần nhất tạo đáy mới' if day_moi else ' · không tạo đáy mới'))
    out['so_dat'] = sum(1 for k in 'abcd' if out[k]['dat'] is True)
    out['du'] = out['so_dat'] == 4
    return out


# ---------------------------------------------------------------- hai danh sách
def _ket_luan(t: dict):
    pd = (t or {}).get('pitch_diem') or {}
    return str(pd.get('ket_luan') or '').strip().upper(), _num(pd.get('tong'))


def lap(bang: list[dict], luan: dict[str, dict], rows_f: dict | None, B, dang_cam: set[str] | None = None,
        bc: dict | None = None) -> dict:
    """bang = pool.dung_bang (đã chấm); luan = {mã: luận điểm}; dang_cam = mã sổ giả lập đang cầm;
    bc = {mã: bctc.phan_tich} (lợi nhuận cốt lõi cho điều kiện a)."""
    bc = bc or {}
    dang_cam = set(dang_cam or ())
    by = {r['ma']: r for r in bang}
    dat = sorted((r for r in bang if r['dat']), key=lambda r: (r['f'].get('nen30') if r['f'].get('nen30') is not None else 9, r['ma']))
    thu_tu = {r['ma']: k for k, r in enumerate(dat, 1)}
    quy_moi = None
    for r in bang:
        q = _quy_key(r.get('quy') or (r.get('so') or {}).get('quy'))
        if q and (quy_moi is None or q > quy_moi):
            quy_moi = q
    giai_ngan, can_them, giu, loai = [], [], [], []
    for s, t in sorted(luan.items()):
        if t.get('trang_thai') in ('loai', 'dong'):
            continue
        r = by.get(s)
        kl, diem = _ket_luan(t)
        q_ma = (r or {}).get('quy') or ((r or {}).get('so') or {}).get('quy')
        thieu = du_khung(t, q_ma)
        dk = bon_dieu_kien(r, (rows_f or {}).get(s), B, bc.get(s)) if r else None
        dong = dict(ma=s, nganh=(r or {}).get('nganh'), ket_luan=kl, diem=diem, thieu=thieu,
                    qua_loc=bool(r and r['dat']), loai_loc=(r or {}).get('loai') or (['không có trong vũ trụ TOP110 / watchlist'] if not r else []),
                    nen30=((r or {}).get('f') or {}).get('nen30'), tu_dinh=((r or {}).get('f') or {}).get('tu_dinh'),
                    thu_tu_chat=thu_tu.get(s), bon_dk=dk, dang_cam=s in dang_cam)
        if not dong['qua_loc']:
            (giu if s in dang_cam else loai).append(dict(dong, vi_sao='trượt lọc nền thấp/nền chặt: ' + '; '.join(dong['loai_loc'])))
        elif kl.startswith(DU) and (diem or 0) >= DIEM_TOI_THIEU and not thieu and dk and dk['du']:
            giai_ngan.append(dong)
        elif kl.startswith(DU) or kl.startswith(CHO) or kl.startswith('CẦN THÊM'):
            ly = []
            if thieu:
                ly.append('luận điểm còn thiếu: ' + ', '.join(thieu[:6]) + (f' (+{len(thieu) - 6})' if len(thieu) > 6 else ''))
            if dk and not dk['du']:
                ly.append('chưa qua đủ 4 điều kiện (' + ', '.join(k for k in 'abcd' if dk[k]['dat'] is not True) + ')')
            if kl.startswith(CHO):
                ly.append('chờ phép thử tin xấu')
            if kl.startswith(DU) and (diem or 0) < DIEM_TOI_THIEU:
                ly.append(f'điểm 70/30 {diem} < {DIEM_TOI_THIEU}')
            (can_them if ly or kl.startswith('CẦN THÊM') else giai_ngan).append(dict(dong, vi_sao='; '.join(ly)))
        else:
            (giu if s in dang_cam else loai).append(dict(dong, vi_sao=f'kết luận {kl or "chưa có"}'))
    # mã đang cầm mà không còn trong hai danh sách (vd luận điểm thiếu, chưa có kết luận) → giữ, ngừng mua
    co = {x['ma'] for x in giai_ngan + can_them + giu}
    for s in sorted(dang_cam - co):
        if s in luan and (luan[s].get('trang_thai') not in ('loai', 'dong')):
            giu.append(dict(ma=s, vi_sao='không còn trong danh sách giải ngân'))
    giai_ngan.sort(key=lambda x: (x['thu_tu_chat'] or 9999, x['ma']))
    can_them.sort(key=lambda x: (x['thu_tu_chat'] or 9999, x['ma']))
    # trần 10 mã có tiền: mã đang cầm (kể cả giữ không mua) chiếm chỗ trước, rồi GIẢI NGÂN, rồi CẦN THÊM BẰNG CHỨNG
    cho = TOI_DA_MA - len({x['ma'] for x in giu if x.get('dang_cam', True)} | (dang_cam & {x['ma'] for x in giai_ngan + can_them}))
    duoc_mo = []
    for x in giai_ngan + can_them:
        sai = [k for k in 'abcd' if x.get('bon_dk') and x['bon_dk'][k]['dat'] is False]
        if sai:
            # CẦN THÊM BẰNG CHỨNG chỉ dành cho chỗ còn THIẾU bằng chứng; điều kiện đo được mà TRƯỢT thì chưa
            # được đợt thăm dò 4% (đang cầm thì giữ, không mua thêm)
            x['duoc_mua'] = False
            x['vi_sao'] = ((x.get('vi_sao') + '; ') if x.get('vi_sao') else '') + \
                'chưa giải ngân (trượt ' + ', '.join(sai) + ')'
            continue
        if x['ma'] in dang_cam:
            x['duoc_mua'] = True
        elif cho > 0:
            x['duoc_mua'] = True
            duoc_mo.append(x['ma'])
            cho -= 1
        else:
            x['duoc_mua'] = False
            x['vi_sao'] = ((x.get('vi_sao') + '; ') if x.get('vi_sao') else '') + f'đã đủ {TOI_DA_MA} mã'
    co_luan = set(luan)
    ung_vien = []
    for r in dat:
        if r['ma'] in co_luan or not r.get('top110'):
            continue
        ung_vien.append(dict(ma=r['ma'], nganh=r['nganh'], nen30=r['f'].get('nen30'), tu_dinh=r['f'].get('tu_dinh'),
                             diem_pool=r['diem'], thu_tu_chat=thu_tu[r['ma']],
                             bon_dk=bon_dieu_kien(r, (rows_f or {}).get(r['ma']), B, bc.get(r['ma'])), vi_sao=r.get('vi_sao')))
        if len(ung_vien) >= 30:
            break
    return dict(giai_ngan=giai_ngan, can_them=can_them, giu_khong_mua=giu, loai=loai, ung_vien=ung_vien,
                so_qua_loc=len(dat), quy_bctc_moi=(f'Q{quy_moi[1]}/{str(quy_moi[0])[2:]}' if quy_moi else None),
                luat=dict(toi_da_ma=TOI_DA_MA, nen_can_bang=NEN_CAN_BANG, nganh_giam_toi_thieu=NGANH_GIAM_TOI_THIEU,
                          lech_nganh_toi_da=LECH_NGANH_TOI_DA, diem_toi_thieu=DIEM_TOI_THIEU))


def ma_duoc_mua(ds: dict) -> dict[str, str]:
    """{mã: 'du' | 'cho'} — mã sổ giả lập được mua đợt mới. 'cho' = luật CHỜ PHÉP THỬ (đợt 1, tối đa 4% NAV)."""
    out = {}
    for x in (ds or {}).get('giai_ngan') or []:
        if x.get('duoc_mua'):
            out[x['ma']] = 'du'
    for x in (ds or {}).get('can_them') or []:
        if x.get('duoc_mua'):
            out[x['ma']] = 'cho'
    return out
