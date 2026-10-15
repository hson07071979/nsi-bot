# -*- coding: utf-8 -*-
"""Vòng học của port — phần "chấm AI có đoán đúng không" (anh Sơn 15/10/2026).

Bốn thứ, đều chấm bằng giá thật, không để AI tự chấm mình:

1. MỤC TIÊU + TIMING. Mỗi luận điểm có 1–2 mục tiêu giá (T1, T2), mỗi mục tiêu có nguồn (mốc kỹ thuật/định giá),
   số phiên dự kiến chạm và hạn chót. Code chạy từng phiên sau ngày ghi: chạm mục tiêu trước → ĐẠT (kèm lệch timing
   = phiên thực tế − phiên dự kiến); chạm giá vô hiệu trước → VÔ HIỆU; hết hạn → HẾT HẠN (kèm còn cách mục tiêu bao xa).
   Timing được phép lệch — mục đích là đo xem dự đoán thời gian của AI lệch hệ thống bao nhiêu để hiệu chỉnh.

2. SỔ DỰ ĐOÁN. Mỗi luận điểm, mỗi nguồn (port + 3 máy) ghi một dòng khi bắt đầu nói và mỗi khi đổi chiều,
   kèm ảnh chụp đặc trưng lúc đó (định giá, tăng trưởng, RS, đèn…). Sau 20/60/120 phiên chấm vượt VN-Index.
   Đây vừa là bảng "ai đúng ở đâu", vừa là bộ dữ liệu có nhãn để sau này dựng mô hình học máy (cần ≥ 30–50 mẫu).

3. SẴN SÀNG XUỐNG TIỀN. Một checklist do code kiểm (không phải AI tự khen): chuỗi tư duy đủ, luận điểm có bằng chứng,
   bull/bear cân, debate ≥ 5 vòng có đủ phe, máy ngược chiều đã được trả lời, có mục tiêu + timing có nguồn,
   vô hiệu không quá −7%, R:R đủ, có mốc kiểm chứng cả giá lẫn cơ bản. Thiếu một mục là CHƯA ĐỦ.

4. HIỆU QUẢ THỰC. Sổ lệnh port/so_lenh.json (ghi tay từng đợt giải ngân: ngày, mã, % vốn, giá khớp).
   Code tính NAV, lãi/lỗ tuyệt đối, so với VN-Index cùng kỳ, theo mã và theo đợt.
"""
from __future__ import annotations

import math

MOC = (20, 60, 120)          # ~1 tháng, ~3 tháng, ~6 tháng
NGUON = ('port', 'bot', 'tin', 'daily')
MAU_TOI_THIEU = 10           # dưới mức này không ra tỷ lệ
CHUAN_LO = 7.0               # chuẩn vô hiệu của anh Sơn: không lỗ quá −7%


# ---------------------------------------------------------------- tiện ích giá
def phien_sau(gia: dict, sym: str, tu: str) -> list[tuple[str, float]]:
    v = gia.get('VNINDEX') or {}
    return [(d, p) for d, p in sorted((gia.get(sym) or {}).items()) if d > tu and d in v]


def gia_tai(gia: dict, sym: str, d: str):
    s = gia.get(sym) or {}
    if d in s:
        return s[d]
    truoc = [k for k in s if k <= d]
    return s[max(truoc)] if truoc else None


def vuot_vni(gia: dict, sym: str, tu: str, n: int):
    p0, v0 = gia_tai(gia, sym, tu), gia_tai(gia, 'VNINDEX', tu)
    ps = phien_sau(gia, sym, tu)
    if not (p0 and v0) or len(ps) < n:
        return None
    d, p = ps[n - 1]
    return round(((p / p0) / (gia['VNINDEX'][d] / v0) - 1) * 100, 2)


def _num(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


# ---------------------------------------------------------------- 1. mục tiêu + timing
def cham_muc_tieu(t: dict, gia: dict, tu: str | None) -> list[dict]:
    """Chấm từng mục tiêu: ĐẠT / VÔ HIỆU / HẾT HẠN / đang mở. `tu` = ngày bắt đầu đếm (ngày vào hoặc ngày mở)."""
    sym, stop = t['ma'], _num(t.get('vo_hieu_gia'))
    out = []
    for m in t.get('muc_tieu') or []:
        g, han, dk = _num(m.get('gia')), int(m.get('han_phien') or 120), _num(m.get('du_kien_phien'))
        r = {**m}
        if not (g and tu):
            out.append({**r, 'trang_thai': 'loi', 'ghi_chu': 'thiếu giá mục tiêu hoặc ngày bắt đầu'})
            continue
        p0 = gia_tai(gia, sym, tu)
        r.update(ngay_tu=tu, gia_tu=p0, cach_pct=round((g / p0 - 1) * 100, 1) if p0 else None)
        ps = phien_sau(gia, sym, tu)
        cao = p0 or 0
        ket = None
        for i, (d, c) in enumerate(ps, 1):
            cao = max(cao, c)
            if c >= g:
                ket = dict(trang_thai='dong', ket_qua='ĐẠT', ngay_dong=d, phien=i,
                           lech_timing=(i - dk) if dk is not None else None)
                break
            if stop and c <= stop:
                ket = dict(trang_thai='dong', ket_qua='VÔ HIỆU', ngay_dong=d, phien=i, gia_luc_dong=c)
                break
            if i >= han:
                ket = dict(trang_thai='dong', ket_qua='HẾT HẠN', ngay_dong=d, phien=i, gia_luc_dong=c,
                           con_cach_pct=round((g / c - 1) * 100, 1))
                break
        if ket is None:
            c = ps[-1][1] if ps else p0
            ket = dict(trang_thai='mo', phien=len(ps), han_phien=han,
                       con_cach_pct=round((g / c - 1) * 100, 1) if c else None,
                       tien_do_pct=round((cao - p0) / (g - p0) * 100, 1) if p0 and g != p0 else None)
        out.append({**r, **ket})
    return out


def rr(t: dict, p) -> list[dict]:
    """R:R đến từng mục tiêu = (mục tiêu − giá) ÷ (giá − giá vô hiệu)."""
    stop = _num(t.get('vo_hieu_gia'))
    out = []
    for m in t.get('muc_tieu') or []:
        g = _num(m.get('gia'))
        v = round((g - p) / (p - stop), 2) if (g and p and stop and p > stop) else None
        out.append(dict(id=m.get('id'), gia=g, rr=v))
    return out


# ---------------------------------------------------------------- 3. sẵn sàng xuống tiền
def san_sang(t: dict, ho_so: dict, thieu: list[str], p, kc_cham: list[dict] | None = None, den: str | None = None) -> dict:
    """Checklist do code kiểm, hai tầng:
    - Luận điểm đủ chặt chưa (chuỗi, luận cứ, bull/bear, debate, máy, khâu 5, mốc cơ bản, điểm 70/30) — 8 mục.
    - Điều kiện vào của riêng luận điểm đã thỏa chưa (`dieu_kien_vao`: đèn NSI, mốc kiểm chứng đã ĐÚNG…).
    Chỉ khi cả hai đạt mới là ĐỦ ĐỂ XUỐNG TIỀN."""
    ck = []

    def add(ten, dat, ghi=''):
        ck.append(dict(ten=ten, dat=bool(dat), ghi_chu=ghi))

    add('Chuỗi 7 khâu + bull/bear + định giá + vô hiệu đủ', not thieu, '; '.join(thieu))
    ld = t.get('luan_diem') or []
    co_bc = [x for x in ld if any(str(b).upper().startswith(('FACT', 'OBSERVATION')) for b in (x.get('bang_chung') or []))]
    tro_trong = [x.get('id') for x in ld if x.get('nhan') in ('INTERPRETATION', 'CONFIRMATION') and x not in co_bc]
    add('Luận điểm có luận cứ: mỗi INTERPRETATION có ≥1 FACT/OBSERVATION', ld and not tro_trong and co_bc,
        ('thiếu bằng chứng: ' + ', '.join(map(str, tro_trong))) if tro_trong else f'{len(co_bc)}/{len(ld)} luận điểm có FACT')
    nb, ne = len(t.get('bull') or []), len(t.get('bear') or [])
    add('Bull và bear cân (mỗi bên ≥ 3 ý)', nb >= 3 and ne >= 3, f'bull {nb} · bear {ne}')
    db = t.get('debate') or []
    ben = {x.get('ben') for x in db}
    add('Debate ≥ 5 vòng, có bull, bear và trọng tài', len(db) >= 5 and {'bull', 'bear', 'trong_tai'} <= ben,
        f'{len(db)} vòng · phe: {", ".join(sorted(b for b in ben if b))}')
    add('Máy ngược chiều đã được trả lời', not ho_so.get('chua_tra_loi'),
        ('chưa trả lời: ' + ', '.join(ho_so['chua_tra_loi'])) if ho_so.get('chua_tra_loi') else
        (f"ngược: {', '.join(ho_so.get('nguoc') or [])} — đã trả lời" if ho_so.get('nguoc') else 'không máy nào ngược'))
    # Khung 70/30 sửa 15/10/2026 (anh Sơn): port đi dài, KHÔNG số hóa điểm mua/bán — bỏ mục tiêu T1/T2,
    # giá vô hiệu −7%, R:R. Thay bằng: khâu 5 "giá đã phản ánh hết tin xấu chưa" có phép thử, mốc cơ bản, điểm 70/30.
    pd = t.get('pitch_diem') or {}
    gs = pd.get('gia_sai') or {}
    add('Khâu 5: gọi tên tin xấu, kỳ vọng ngầm trong giá và phép thử tin xấu tiếp theo',
        all(str(gs.get(k) or '').strip() for k in ('tin_xau', 'ky_vong_ngam', 'phep_thu')),
        str(gs.get('ket_luan') or 'thiếu pitch_diem.gia_sai'))
    kc = t.get('kiem_chung') or []
    add('Có mốc kiểm chứng cơ bản (code chấm)', any(k.get('loai') == 'funda' for k in kc), f'{len(kc)} mốc')
    l70, s30 = _num(pd.get('luan_diem_70')), _num(pd.get('so_30'))
    add('Có điểm 70/30 và kết luận bằng lời', l70 is not None and s30 is not None and str(pd.get('ket_luan') or '').strip(),
        f"{pd.get('tong')} điểm · {pd.get('ket_luan')}" if pd.get('ket_luan') else 'thiếu pitch_diem')
    r = rr(t, p)
    r1 = r[0]['rr'] if r else None
    rmax = max((x['rr'] for x in r if x['rr'] is not None), default=None)
    stop = _num(t.get('vo_hieu_gia'))
    lo = round((1 - stop / p) * 100, 1) if (stop and p) else None
    dat = sum(1 for x in ck if x['dat'])
    vao = dieu_kien_vao(t, kc_cham or [], den)
    chat = dat == len(ck)
    ket = ('ĐỦ ĐỂ XUỐNG TIỀN' if chat and all(x['dat'] for x in vao) else
           'LUẬN ĐIỂM ĐỦ CHẶT — CHỜ ĐIỀU KIỆN VÀO' if chat else 'CHƯA ĐỦ')
    # Kết luận bằng lời sau debate là quyết định (anh Sơn chốt 15/10); checklist chỉ kiểm hình thức.
    if chat and str(pd.get('ket_luan') or '').strip():
        ket = str(pd['ket_luan'])
    return dict(muc=ck, dat=dat, tong=len(ck), dieu_kien_vao=vao, r1=r1, rmax=rmax, lo_toi_da=lo, ket_luan=ket)


def dieu_kien_vao(t: dict, kc_cham: list[dict], den: str | None) -> list[dict]:
    """Điều kiện vào riêng của từng luận điểm. Loại: den (đèn NSI không thuộc danh sách), kiem_chung (mốc id đã có kết quả)."""
    ten_den = {'DO': 'ĐỎ', 'CAM': 'CAM', 'VANG': 'VÀNG', 'XANH': 'XANH'}
    out = []
    for d in t.get('dieu_kien_vao') or []:
        if d.get('loai') == 'den':
            khong = d.get('khong') or ['DO']
            out.append(dict(ten='Đèn NSI không phải ' + '/'.join(ten_den.get(x, x) for x in khong),
                            dat=bool(den) and den not in khong, ghi_chu=f'đèn hiện tại {ten_den.get(den, den)}'))
        elif d.get('loai') == 'kiem_chung':
            k = next((x for x in kc_cham if x.get('id') == d.get('id')), None)
            can = d.get('can', 'ĐÚNG')
            out.append(dict(ten=f"Mốc {d.get('id')} {can}: {(k or {}).get('noi_dung', '')}",
                            dat=bool(k) and k.get('ket_qua') == can,
                            ghi_chu=(k or {}).get('ket_qua') or (k or {}).get('ghi_chu') or 'chưa có kết quả'))
        else:
            out.append(dict(ten=str(d.get('mo_ta') or d), dat=False, ghi_chu='loại điều kiện lạ'))
    return out


# ---------------------------------------------------------------- 2. sổ dự đoán + độ chính xác
def dac_trung(sym: str, D: dict) -> dict:
    """Ảnh chụp đặc trưng lúc dự đoán — dữ liệu đầu vào cho mô hình học sau này."""
    lk = (D.get('lookup') or {}).get(sym) or {}
    f = (D.get('funda') or {}).get(sym) or {}

    def last(k):
        a = [x for x in (f.get(k) or []) if _num(x) is not None]
        return a[-1] if a else None

    def med(k, lo, hi):
        a = sorted(x for x in (f.get(k) or []) if _num(x) is not None and lo < x < hi)
        return a[len(a) // 2] if len(a) >= 4 else None
    pe, pb, pe_tv, pb_tv = last('pe'), last('pb'), med('pe', 0, 200), med('pb', 0, 50)
    reg = (D.get('regime') or [{}])[-1]
    return dict(gia=_num(lk.get('price')), pe=pe, pb=pb,
                pe_rel=round(pe / pe_tv, 2) if pe and pe_tv and pe > 0 else None,
                pb_rel=round(pb / pb_tv, 2) if pb and pb_tv else None,
                roe=last('roe'), ny=last('ny'), ry=last('ry'), rs=_num(lk.get('rs')), diem=_num(lk.get('score')),
                diem_cb=_num(lk.get('fund')), nganh=lk.get('sector'), den=reg.get('light'), br50=reg.get('br50'),
                vni=reg.get('vni'))


def ghi_du_doan(so: list[dict], the: list[dict], D: dict, gia: dict, asof: str) -> int:
    """Mỗi (mã, nguồn): ghi một dòng khi lần đầu thấy hoặc khi đổi chiều. Trả về số dòng mới."""
    moi = 0
    for x in the:
        t = x['luan']
        if t.get('trang_thai') not in ('nghien_cuu', 'trong_port'):
            continue
        sym = t['ma']
        cp = {'tang': 1, 'giam': -1, 'trung_lap': 0}.get(t.get('chieu'), 0)
        may = x['ho_so']['may']
        chieu = {'port': cp, **{k: may[k]['chieu'] for k in ('bot', 'tin', 'daily')}}
        dt = None
        for ng, c in chieu.items():
            cu = [r for r in so if r['ma'] == sym and r['nguon'] == ng]
            if cu and cu[-1]['chieu'] == c:
                continue
            dt = dt or dac_trung(sym, D)
            row = dict(id=f'{sym}-{ng}-{asof}', ngay=asof, ma=sym, nguon=ng, chieu=c,
                       gia0=gia_tai(gia, sym, asof), vni0=gia_tai(gia, 'VNINDEX', asof), dac_trung=dt)
            if ng == 'port':
                row.update(trang_thai_port=t.get('trang_thai'),
                           dong_thuan=sum(1 for k in ('bot', 'tin', 'daily') if cp and may[k]['chieu'] == cp),
                           nguoc=sum(1 for k in ('bot', 'tin', 'daily') if cp and may[k]['chieu'] == -cp),
                           muc_tieu=[dict(id=m.get('id'), gia=m.get('gia'), du_kien_phien=m.get('du_kien_phien'))
                                     for m in t.get('muc_tieu') or []])
            so.append(row)
            moi += 1
    return moi


def cham_du_doan(so: list[dict], gia: dict) -> None:
    for r in so:
        for n in MOC:
            if f'vuot_{n}p' in r:
                continue
            ex = vuot_vni(gia, r['ma'], r['ngay'], n)
            if ex is not None:
                r[f'vuot_{n}p'] = ex
                r[f'dung_{n}p'] = None if r['chieu'] == 0 else (ex > 0) == (r['chieu'] > 0)


def wilson_thap(k: int, n: int, z: float = 1.645) -> float | None:
    """Cận dưới khoảng tin cậy 90% của tỷ lệ đúng — dùng để nói 'đủ mạnh chưa' thay vì nhìn tỷ lệ trần."""
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - s) / d * 100, 1)


def _bang(rows: list[dict], n: int) -> dict:
    xs = [r for r in rows if r.get(f'dung_{n}p') is not None]
    k = sum(1 for r in xs if r[f'dung_{n}p'])
    al = [r[f'vuot_{n}p'] * (1 if r['chieu'] > 0 else -1) for r in xs]
    o = dict(da_cham=len(xs), dung=k, cho=sum(1 for r in rows if r['chieu'] != 0 and f'vuot_{n}p' not in r),
             alpha_tb=round(sum(al) / len(al), 2) if al else None)
    if len(xs) >= MAU_TOI_THIEU:
        o['ty_le'] = round(k / len(xs) * 100, 1)
        o['wilson_thap'] = wilson_thap(k, len(xs))
        o['ket_luan'] = ('ĐỦ MẠNH' if o['wilson_thap'] > 50 else
                         'CHƯA HƠN TUNG ĐỒNG XU' if o['ty_le'] > 50 else 'ĐANG SAI NHIỀU HƠN ĐÚNG')
    else:
        o['ty_le'] = o['wilson_thap'] = None
        o['ket_luan'] = f'chưa đủ mẫu ({len(xs)}/{MAU_TOI_THIEU})'
    return o


def do_chinh_xac(so: list[dict]) -> dict:
    out = {ng: {f'{n}p': _bang([r for r in so if r['nguon'] == ng], n) for n in MOC} for ng in NGUON}
    port = [r for r in so if r['nguon'] == 'port']
    out['port_theo_dong_thuan'] = {
        str(k): {f'{n}p': _bang([r for r in port if r.get('dong_thuan') == k], n) for n in MOC} for k in range(4)}
    out['so_mau'] = dict(tong=len(so), port=len(port),
                         da_cham_60p=sum(1 for r in so if 'vuot_60p' in r),
                         can_cho_mo_hinh=50)
    return out


def tong_ket_timing(the: list[dict]) -> dict:
    """Lệch timing của các mục tiêu đã ĐẠT: dương = đến chậm hơn dự kiến."""
    lech = [m['lech_timing'] for x in the for m in x.get('muc_tieu_cham') or []
            if m.get('ket_qua') == 'ĐẠT' and m.get('lech_timing') is not None]
    kq = [m.get('ket_qua') for x in the for m in x.get('muc_tieu_cham') or [] if m.get('trang_thai') == 'dong']
    return dict(da_dong=len(kq), dat=kq.count('ĐẠT'), vo_hieu=kq.count('VÔ HIỆU'), het_han=kq.count('HẾT HẠN'),
                lech_tb=round(sum(lech) / len(lech), 1) if lech else None,
                lech_trung_vi=sorted(lech)[len(lech) // 2] if lech else None)


# ---------------------------------------------------------------- 4. hiệu quả thực từ sổ lệnh
def hieu_qua(so_lenh: dict, gia: dict, asof: str) -> dict | None:
    """Sổ lệnh: {"lenh":[{"ngay","ma","loai":"mua|ban","ty_le": % vốn ban đầu, "gia": giá khớp (tùy chọn)}]}.
    Bán ghi ty_le = % vốn ban đầu đã bỏ vào phần bán ra (tính theo giá vốn bình quân)."""
    lenh = sorted((so_lenh or {}).get('lenh') or [], key=lambda x: x.get('ngay', ''))
    if not lenh:
        return None
    vt, tien, loi, chot = {}, 100.0, [], 0.0
    for l in lenh:
        sym, tl = str(l.get('ma', '')).upper(), float(l.get('ty_le') or 0)
        p = _num(l.get('gia')) or gia_tai(gia, sym, l.get('ngay', ''))
        if not (sym and tl > 0 and p):
            loi.append(f"bỏ qua lệnh {l}: thiếu mã, tỷ lệ hoặc giá")
            continue
        v = vt.setdefault(sym, dict(cp=0.0, von=0.0, mua=[]))
        if l.get('loai', 'mua') == 'mua':
            v['cp'] += tl / p
            v['von'] += tl
            tien -= tl
            v['mua'].append(dict(ngay=l['ngay'], ty_le=tl, gia=p, dot=l.get('dot')))
        else:
            if v['von'] <= 0:
                loi.append(f'lệnh bán {sym} khi chưa có vị thế')
                continue
            phan = min(tl / v['von'], 1.0)
            cp_ban = v['cp'] * phan
            tien += cp_ban * p
            chot += cp_ban * p - v['von'] * phan
            v['cp'] -= cp_ban
            v['von'] -= v['von'] * phan
    ngay0 = lenh[0]['ngay']
    rows, nav = [], tien
    for sym, v in vt.items():
        p = gia_tai(gia, sym, asof)
        gt = v['cp'] * p if p else 0.0
        nav += gt
        if v['von'] > 1e-9:
            rows.append(dict(ma=sym, von=round(v['von'], 2), gia_tb=round(v['von'] / v['cp'], 3) if v['cp'] else None,
                             gia=p, gia_tri=round(gt, 2), lai_pct=round((gt / v['von'] - 1) * 100, 2) if v['von'] else None,
                             ty_trong_nav=None, so_lan_mua=len(v['mua'])))
    for r in rows:
        r['ty_trong_nav'] = round(r['gia_tri'] / nav * 100, 1) if nav else None
    v0, v1 = gia_tai(gia, 'VNINDEX', ngay0), gia_tai(gia, 'VNINDEX', asof)
    vni = round((v1 / v0 - 1) * 100, 2) if v0 and v1 else None
    ln = round(nav - 100, 2)
    return dict(tu_ngay=ngay0, den_ngay=asof, nav=round(nav, 2), lai_pct=ln, vni_pct=vni,
                vuot_vni=round(ln - vni, 2) if vni is not None else None,
                da_giai_ngan=round(sum(r['von'] for r in rows), 2),
                tien_mat=round(tien, 2), lai_da_chot=round(chot, 2), vi_the=sorted(rows, key=lambda r: -r['gia_tri']),
                so_lenh=len(lenh), loi=loi,
                ghi_chu='Lãi/lỗ tính trên toàn bộ vốn (tiền mặt chưa giải ngân lãi 0%); VN-Index tính từ ngày lệnh đầu tiên.')
