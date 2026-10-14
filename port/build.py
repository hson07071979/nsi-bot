# -*- coding: utf-8 -*-
"""Lọc port — vòng học thứ tư của bộ máy NSI (anh Sơn 14/10/2026).

Port KHÔNG chạy riêng. Mỗi luận điểm port phải DEBATE với ba bộ máy đã có, và cả bốn cùng bị CHẤM bằng giá thật:

  máy        | nói gì về một mã                                    | đã tự chấm ở đâu
  -----------|-----------------------------------------------------|-------------------------------------------
  bot        | trạng thái 9 điều kiện, tín hiệu, cổng rủi ro CFO/ICR | backtest + Monte Carlo (nsi-bot)
  tin        | trọng tài + 3 phe (lạc quan/thận trọng/vĩ mô) theo mã | nsi-tin out/cham_diem.json (T+4 vượt VNI)
  daily      | sổ dự báo mốc giữ/thủng/vượt + cấu trúc MA           | nsi-tin data/daily/so_du_bao.json
  port       | luận điểm vĩ mô → ngành → DN → dẫn ngược vĩ mô        | port/state/so_cham.json (file này tạo)

Vòng học:
  1. build đọc dữ liệu CÔNG KHAI của ba máy (không cào thêm), dựng "hồ sơ máy" cho từng mã trong port/luan_diem/.
  2. Máy nào ngược chiều luận điểm port → bắt buộc có `phan_bien_may.<máy>`; thiếu là cờ CHƯA TRẢ LỜI MÁY.
  3. Lần đầu thấy ngược chiều → mở một dòng SỔ BẤT ĐỒNG (giá mã + VNI lúc đó). Sau 20 và 60 phiên chấm:
     mã vượt hay thua VN-Index → port đúng hay máy đúng. Đây là bảng "ai đáng tin ở đâu".
  4. Mốc kiểm chứng của luận điểm (giá: giu/thung/vuot/duoi; cơ bản: chỉ tiêu quý ≥/≤ ngưỡng) chấm bằng code,
     không để AI tự chấm mình.
  5. Bài học (khi đóng luận điểm) + bảng tin cậy quay lại làm đầu vào cho lần debate sau.

Riêng tư: luận điểm và danh mục KH nằm trong nsi-bot (private) và KV `port/bundle` (trang quản trị có đăng nhập).
KHÔNG ghi gì của port sang nsi-tin (public) hay kênh video.

Chạy: python port/build.py   (env: SITE_HTML, TIN_DIR để chạy offline/test; KV_* để đẩy KV)
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hoc as H  # noqa: E402  (mục tiêu + timing, sổ dự đoán, sẵn sàng, hiệu quả thực)

ROOT = Path(__file__).resolve().parent
LUAN = ROOT / 'luan_diem'
STATE = ROOT / 'state'
OUT = ROOT / 'out'
VN = timezone(timedelta(hours=7))

SITE_URL = 'https://raw.githubusercontent.com/hson07071979/nguyensoninvest/main/index.html'
TIN_RAW = 'https://raw.githubusercontent.com/hson07071979/nsi-tin/main/'
MAYS = ('bot', 'tin', 'daily')
TEN_MAY = {'bot': 'Bot giao dịch', 'tin': 'NSI Tin (trọng tài 3 phe)', 'daily': 'NSI Daily (mốc + sổ dự báo)'}
CHIEU = {'tang': 1, 'giam': -1, 'trung_lap': 0}
MOC_CHAM = H.MOC             # 20 / 60 / 120 phiên: chấm sổ bất đồng, kết quả luận điểm, sổ dự đoán
TIN_NGAY = 10                # cửa sổ ngày lịch đọc nsi-tin cho quan điểm theo mã
LOAI_GIA = ('giu', 'thung', 'vuot', 'duoi')


# ---------------------------------------------------------------- đọc nguồn
def _get(url: str) -> str | None:
    import requests
    try:
        r = requests.get(url, timeout=60)
        return r.text if r.status_code == 200 else None
    except requests.RequestException:
        return None


def load_site() -> dict:
    p = os.environ.get('SITE_HTML')
    s = Path(p).read_text(encoding='utf-8') if p else _get(SITE_URL)
    if not s:
        raise RuntimeError('không đọc được DATA trang web')
    m = re.search(r'<script id="DATA"[^>]*>(.*?)</script>', s, re.S)
    return json.loads(m.group(1))


def tin_json(rel: str, default=None):
    d = os.environ.get('TIN_DIR')
    if d:
        f = Path(d) / rel
        return json.loads(f.read_text(encoding='utf-8')) if f.exists() else default
    t = _get(TIN_RAW + rel)
    try:
        return json.loads(t) if t else default
    except ValueError:
        return default


def rj(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def wj(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')


def load_luan() -> dict[str, dict]:
    out = {}
    for f in sorted(LUAN.glob('*.json')):
        t = rj(f, None)
        if not isinstance(t, dict):
            continue
        ma = str(t.get('ma') or f.stem).upper()
        t['ma'] = ma
        out[ma] = t
    return out


# ---------------------------------------------------------------- bảng lọc cơ bản
def _num(x):
    return x if isinstance(x, (int, float)) else None


def _last(a, k=1):
    v = [x for x in (a or []) if x is not None]
    return v[-k] if len(v) >= k else None


def funda_row(sym: str, f: dict | None, lk: dict | None) -> dict:
    f, lk = f or {}, lk or {}
    q = f.get('q') or []
    ny, ry, np_ = f.get('ny') or [], f.get('ry') or [], f.get('np') or []
    rev = f.get('rev') or []
    pe = [x for x in (f.get('pe') or []) if isinstance(x, (int, float)) and 0 < x < 200]
    pb = [x for x in (f.get('pb') or []) if isinstance(x, (int, float)) and 0 < x < 50]
    streak = 0
    for x in reversed(ny):
        if isinstance(x, (int, float)) and x > 0:
            streak += 1
        else:
            break

    def s4(a, off):
        v = a[len(a) - 4 - off:len(a) - off] if len(a) >= 4 + off else []
        return sum(v) if len(v) == 4 and all(isinstance(x, (int, float)) for x in v) else None

    def yoy4(a):
        a1, a0 = s4(a, 0), s4(a, 4)
        return round((a1 / a0 - 1) * 100, 1) if a1 is not None and a0 and a0 > 0 else None

    return dict(
        sym=sym, ten=lk.get('name'), san=lk.get('exch'), nganh=lk.get('sector'), gia=_num(lk.get('price')),
        von_hoa=_num(lk.get('mktcap')), gtgd=_num(lk.get('gtgd')), rs=_num(lk.get('rs')), diem=_num(lk.get('score')),
        diem_cb=_num(lk.get('fund')), trang_thai=lk.get('state'), chan=lk.get('block'), tim=bool(lk.get('tim')),
        tim_vi=lk.get('tim_vi'), quy=q[-1] if q else None,
        ry=_last(ry), ny=_last(ny), ny_truoc=_last(ny, 2), roe=_last(f.get('roe')),
        pe=_last(f.get('pe')), pb=_last(f.get('pb')),
        pe_tv=round(median(pe), 2) if len(pe) >= 4 else None, pb_tv=round(median(pb), 2) if len(pb) >= 4 else None,
        ny_lien=streak, np4_yoy=yoy4(np_), rev4_yoy=yoy4(rev),
    )


def bang_loc(D: dict) -> list[dict]:
    lk, fu = D.get('lookup') or {}, D.get('funda') or {}
    return [funda_row(s, fu.get(s), lk.get(s)) for s in sorted(set(lk) | set(fu))]


# ---------------------------------------------------------------- quan điểm từng máy
def _sign(x) -> int:
    return {'tot': 1, '+': 1, 'co_hoi': 1, 'tang': 1, 'xau': -1, '-': -1, 'giam': -1}.get(str(x or '').strip(), 0)


def may_bot(sym: str, D: dict) -> dict:
    lk = (D.get('lookup') or {}).get(sym)
    if not lk:
        return dict(chieu=0, ly_do=['bot không có mã này trong vũ trụ quét'], bang_chung=[])
    ly, bc = [], []
    asof = D.get('asof') or ''
    lim = (date.fromisoformat(asof) - timedelta(days=14)).isoformat() if asof else ''
    sig = [s for s in D.get('signals') or [] if s.get('sym') == sym]
    gan = [s for s in sig if s.get('date', '') >= lim]
    block = str(lk.get('block') or '')
    c = 0
    if block.startswith('CFO') or block.startswith('ICR'):
        c = -1
        ly.append(f'cổng rủi ro cơ bản chặn: {block}')
    elif gan or lk.get('state') == 'cho':
        c = 1
        ly.append('có tín hiệu mua trong 14 ngày' if gan else f"đủ điều kiện, {str(lk.get('label') or '').lower()}")
    else:
        ly.append(f"{str(lk.get('label') or lk.get('state')).lower()}" + (f": {'; '.join((lk.get('miss') or [])[:3])}"
                                                                         if lk.get('miss') else ''))
    bc.append(f"điểm {lk.get('score')} · điểm cơ bản {lk.get('fund')} · RS {lk.get('rs')} · nền {lk.get('base')}%")
    if lk.get('tim'):
        bc.append(f"cờ lợi nhuận bất thường: {lk.get('tim_vi')}")
    marks = (D.get('marks') or {}).get(sym) or []
    b = [m for m in marks if m.get('t') == 'B']
    s = [m for m in marks if m.get('t') == 'S']
    if b and s:
        pairs = list(zip(b, s))
        win = sum(1 for x, y in pairs if (y.get('pxa') or 0) > (x.get('pxa') or 0))
        bc.append(f'backtest trên mã: {len(pairs)} lệnh, thắng {win}')
    if sig:
        bc.append(f"tín hiệu gần nhất {sig[-1].get('date')} (đèn {sig[-1].get('light')})")
    return dict(chieu=c, ly_do=ly, bang_chung=bc, khung='ngắn hạn: động lượng/breakout + cổng rủi ro cơ bản')


def tin_reports(today: date) -> list[dict]:
    out = []
    for k in range(TIN_NGAY + 1):
        d = (today - timedelta(days=k)).isoformat()
        r = tin_json(f'out/{d}.json')
        if isinstance(r, dict) and r.get('ngay'):
            out.append(r)
    return out


def may_tin(sym: str, sector: str | None, reps: list[dict]) -> dict:
    tong, ly, bc = 0.0, [], []
    for r in reps:
        for tab in ('web', 'zalo'):
            for t in (r.get(tab) or {}).get('topics') or []:
                hit = [x for x in t.get('nganh_ma') or [] if str(x.get('ten', '')).strip().upper() == sym]
                lien = sym in [str(x).upper() for x in t.get('ma_lien_quan') or []]
                nganh = sector and any(sector.lower() in str(n).lower() or str(n).lower() in sector.lower()
                                       for n in t.get('nganh') or [] if str(n).strip())
                if not (hit or lien or nganh):
                    continue
                c = _sign(hit[0].get('chieu')) if hit else (_sign(t.get('danh_gia')) if lien else 0)
                w = (t.get('quan_trong') or 3) / 5
                if hit or lien:
                    tong += c * w
                phe = {p: (v or {}).get('nhan_dinh') for p, v in (t.get('phe') or {}).items()}
                bc.append(dict(ngay=r['ngay'], tab=tab, tieu_de=t.get('tieu_de'), chieu=c,
                               muc=('mã' if (hit or lien) else 'ngành'), xac_minh=t.get('xac_minh'),
                               danh_gia=t.get('danh_gia'), phe=phe,
                               noi_bo=(tab == 'zalo')))   # Zalo kín: chỉ dùng nội bộ, không trích cho KH
    c = 1 if tong >= 0.6 else (-1 if tong <= -0.6 else 0)
    ma = [x for x in bc if x['muc'] == 'mã']
    ly.append(f'{len(ma)} chủ đề nhắc mã, {len(bc) - len(ma)} chủ đề cùng ngành trong {TIN_NGAY} ngày; điểm chiều {tong:+.1f}'
              if bc else f'không có chủ đề nào về mã/ngành trong {TIN_NGAY} ngày')
    return dict(chieu=c, ly_do=ly, bang_chung=bc[-12:], khung='tin tức T+0..T+4, chấm vượt VN-Index')


def _ma_pct(txt: str, ten: str):
    m = re.search(ten + r'=[\d.]+\(([+-]?[\d.]+)%\)', txt or '')
    return float(m.group(1)) if m else None


def may_daily(sym: str, daily: dict | None, so: list[dict]) -> dict:
    ly, bc, c = [], [], 0
    mo = [r for r in so or [] if r.get('doi_tuong') == sym and r.get('trang_thai') == 'mo']
    dong = [r for r in so or [] if r.get('doi_tuong') == sym and r.get('trang_thai') == 'dong']
    if mo:
        s = sum(1 if r['loai'] in ('giu', 'vuot') else -1 for r in mo)
        c = (s > 0) - (s < 0)
        ly.append('sổ dự báo đang mở: ' + '; '.join(f"{r['loai']} {r['moc']} ({r.get('phien_da_qua', 0)}/{r['han_phien']} phiên)"
                                                   for r in mo))
    for r in dong[-3:]:
        bc.append(f"đã chấm {r.get('ngay_dong')}: {r['loai']} {r['moc']} → {r.get('ket_qua')}")
    fc = (daily or {}).get('fc') or {}
    row = None
    for arr in (fc.get('ma_theo_nhom') or {}).values():
        for x in arr:
            if x.get('ma') == sym:
                row = x
    if row:
        p50, p200 = _ma_pct(row.get('duong_ma'), 'MA50'), _ma_pct(row.get('duong_ma'), 'MA200')
        # duong_ma ghi "(giá so với MA)": dương = giá trên MA
        if not mo and p50 is not None and p200 is not None:
            c = 1 if (p50 > 0 and p200 > 0) else (-1 if (p50 < 0 and p200 < 0) else 0)
            ly.append(f'cấu trúc MA: giá {p50:+.1f}% so với MA50, {p200:+.1f}% so với MA200')
        if row.get('vung_dang_test'):
            bc.append(f"vùng đang test {row['vung_dang_test']}")
        if row.get('ho_tro'):
            bc.append('hỗ trợ ' + ' | '.join(row['ho_tro'][:2]))
        if row.get('khang_cu'):
            bc.append('kháng cự ' + ' | '.join(row['khang_cu'][:2]))
    if not mo and not row:
        ly.append('Daily chưa theo dõi mã này')
    return dict(chieu=c, ly_do=ly, bang_chung=bc, khung='kỹ thuật vài phiên: mốc hỗ trợ/kháng cự, sổ dự báo')


# ---------------------------------------------------------------- giá + chấm điểm
def snapshot(gia: dict, D: dict, syms) -> str:
    asof = D.get('asof')
    reg = (D.get('regime') or [{}])[-1]
    if reg.get('date') == asof and reg.get('vni'):
        gia.setdefault('VNINDEX', {})[asof] = reg['vni']
    lk = D.get('lookup') or {}
    for s in syms:
        p = (lk.get(s) or {}).get('price')
        if p:
            gia.setdefault(s, {})[asof] = p
    return asof


def phien_sau(gia: dict, sym: str, tu: str) -> list[tuple[str, float]]:
    """Các phiên (đã chụp giá) SAU ngày `tu`, có cả giá mã lẫn VNI."""
    v = gia.get('VNINDEX') or {}
    return [(d, p) for d, p in sorted((gia.get(sym) or {}).items()) if d > tu and d in v]


def gia_tai(gia: dict, sym: str, d: str):
    s = gia.get(sym) or {}
    if d in s:
        return s[d]
    truoc = [k for k in s if k <= d]
    return s[max(truoc)] if truoc else None


def cham_moc_gia(k: dict, ngay_ghi: str, gia: dict, sym: str) -> dict:
    loai, moc, han = k['loai'], float(k['moc']), int(k.get('han_phien') or 20)
    ps = phien_sau(gia, sym, ngay_ghi)
    for i, (d, c) in enumerate(ps, 1):
        ket = None
        if loai == 'giu' and c < moc: ket = 'SAI'
        elif loai == 'thung' and c < moc: ket = 'ĐÚNG'
        elif loai == 'vuot' and c > moc: ket = 'ĐÚNG'
        elif loai == 'duoi' and c > moc: ket = 'SAI'
        if ket is None and i >= han:
            ket = 'ĐÚNG' if loai in ('giu', 'duoi') else 'SAI'
        if ket:
            return dict(trang_thai='dong', ket_qua=ket, ngay_dong=d, gia_luc_dong=c, phien=i)
    return dict(trang_thai='mo', phien=len(ps), han_phien=han)


def cham_moc_cb(k: dict, fu: dict | None) -> dict:
    fu = fu or {}
    q = fu.get('q') or []
    if k.get('quy') not in q:
        return dict(trang_thai='mo', ghi_chu=f"chờ BCTC {k.get('quy')}")
    v = (fu.get(k.get('chi_tieu')) or [None] * len(q))[q.index(k['quy'])]
    if v is None:
        return dict(trang_thai='mo', ghi_chu='quý đã có nhưng chỉ tiêu trống')
    ss, ng = k.get('so_sanh', '>='), float(k['nguong'])
    ok = v >= ng if ss == '>=' else v <= ng
    return dict(trang_thai='dong', ket_qua='ĐÚNG' if ok else 'SAI', gia_tri=v)


def vuot_vni(gia: dict, sym: str, tu: str, n: int):
    """Lợi suất vượt VN-Index sau n phiên tính từ ngày `tu` (giá đóng cửa ngày `tu` làm gốc)."""
    p0, v0 = gia_tai(gia, sym, tu), gia_tai(gia, 'VNINDEX', tu)
    ps = phien_sau(gia, sym, tu)
    if not (p0 and v0) or len(ps) < n:
        return None
    d, p = ps[n - 1]
    return round(((p / p0) / (gia['VNINDEX'][d] / v0) - 1) * 100, 2)


def cham_bat_dong(so: list[dict], gia: dict) -> None:
    for r in so:
        for n in MOC_CHAM:
            ex = vuot_vni(gia, r['ma'], r['ngay'], n)
            if ex is not None:
                r[f'vuot_{n}p'] = ex
                r[f'port_dung_{n}p'] = (ex > 0) == (r['chieu_port'] > 0)


def tong_ket_bat_dong(so: list[dict]) -> dict:
    out = {}
    for may in MAYS:
        rows = [r for r in so if r['may'] == may]
        o = {'so_lan': len(rows)}
        for n in MOC_CHAM:
            xs = [r[f'port_dung_{n}p'] for r in rows if f'port_dung_{n}p' in r]
            o[f'{n}p'] = {'da_cham': len(xs), 'port_dung': sum(xs), 'may_dung': len(xs) - sum(xs),
                          'ty_le_port_dung': round(sum(xs) / len(xs) * 100, 1) if len(xs) >= 10 else None}
        out[may] = o
    return out


# ---------------------------------------------------------------- dựng gói
def ho_so(t: dict, D: dict, reps, daily, so_db) -> dict:
    sym = t['ma']
    sector = ((D.get('lookup') or {}).get(sym) or {}).get('sector')
    may = {'bot': may_bot(sym, D), 'tin': may_tin(sym, sector, reps), 'daily': may_daily(sym, daily, so_db)}
    cp = CHIEU.get(t.get('chieu'), 0)
    pb = t.get('phan_bien_may') or {}
    nguoc, chua = [], []
    for k, v in may.items():
        v['nguoc_port'] = bool(cp and v['chieu'] and v['chieu'] != cp)
        if v['nguoc_port']:
            nguoc.append(k)
            if not str((pb.get(k) or {}).get('noi_dung') if isinstance(pb.get(k), dict) else pb.get(k) or '').strip():
                chua.append(k)
    return dict(may=may, nguoc=nguoc, chua_tra_loi=chua, nganh=sector)


def kiem_tra_luan(t: dict) -> list[str]:
    """Luận điểm thiếu phần nào của chuỗi tư duy thì ghi ra — để debate không bỏ khâu."""
    thieu = []
    ch = t.get('chuoi') or {}
    for k, ten in (('vi_mo', 'vĩ mô'), ('nganh', 'ngành'), ('doanh_nghiep', 'doanh nghiệp'),
                   ('mo_hinh_kd', 'mô hình kinh doanh'), ('lanh_dao', 'lãnh đạo'), ('chuoi_gia_tri', 'vị trí chuỗi giá trị'),
                   ('dan_nguoc_vi_mo', 'dẫn ngược lên vĩ mô')):
        if not str(ch.get(k) or '').strip():
            thieu.append(f'chuỗi: thiếu {ten}')
    if not t.get('bull'): thieu.append('thiếu luận điểm bull')
    if not t.get('bear'): thieu.append('thiếu luận điểm bear')
    if not t.get('kiem_chung'): thieu.append('chưa có mốc kiểm chứng chấm được')
    if not str(t.get('vo_hieu') or '').strip(): thieu.append('thiếu điều kiện vô hiệu')
    if not str(t.get('dinh_gia') or '').strip(): thieu.append('thiếu dòng định giá')
    return thieu


def build(now: datetime | None = None) -> dict:
    now = now or datetime.now(VN)
    D = load_site()
    asof = D.get('asof')
    luan = load_luan()
    reps = tin_reports(now.date())          # gồm cả bản tin sáng nay (có thể mới hơn asof trang web)
    daily = tin_json('out/daily/latest.json', {})
    so_db = tin_json('data/daily/so_du_bao.json', []) or []
    cham_tin = tin_json('out/cham_diem.json', {}) or {}

    gia = rj(STATE / 'gia.json', {})
    so = rj(STATE / 'so_bat_dong.json', [])
    vao = rj(STATE / 'ngay_vao.json', {})
    so_dd = rj(STATE / 'so_du_doan.json', [])
    so_lenh = rj(ROOT / 'so_lenh.json', {})
    snapshot(gia, D, set(luan) | {r['ma'] for r in so} | {r['ma'] for r in so_dd}
             | {str(l.get('ma', '')).upper() for l in (so_lenh.get('lenh') or []) if l.get('ma')})

    fu = D.get('funda') or {}
    den = (D.get('regime_live') or {}).get('light') or (D.get('regime') or [{}])[-1].get('light')
    the = []
    for sym, t in luan.items():
        h = ho_so(t, D, reps, daily, so_db)
        cp = CHIEU.get(t.get('chieu'), 0)
        dang_chay = t.get('trang_thai') in ('nghien_cuu', 'trong_port')
        # sổ bất đồng: mở một dòng khi lần đầu thấy máy ngược chiều (mỗi cặp mã–máy chỉ một dòng đang mở)
        if dang_chay and asof:
            for may in h['nguoc']:
                mo = [r for r in so if r['ma'] == sym and r['may'] == may and f'port_dung_{MOC_CHAM[-1]}p' not in r]
                if not mo:
                    so.append(dict(ma=sym, may=may, ngay=asof, chieu_port=cp, chieu_may=h['may'][may]['chieu'],
                                   ly_do_may='; '.join(h['may'][may]['ly_do'])[:300],
                                   gia0=gia_tai(gia, sym, asof), vni0=gia_tai(gia, 'VNINDEX', asof)))
        if t.get('trang_thai') == 'trong_port' and sym not in vao:
            vao[sym] = t.get('ngay_vao') or asof
        kc = []
        for k in t.get('kiem_chung') or []:
            ng = k.get('ngay_ghi') or t.get('ngay_mo') or asof
            r = cham_moc_cb(k, fu.get(sym)) if k.get('loai') == 'funda' else (
                cham_moc_gia(k, ng, gia, sym) if k.get('loai') in LOAI_GIA else dict(trang_thai='loi', ghi_chu='loại mốc lạ'))
            kc.append({**k, **r, 'ngay_ghi': ng})
        kq = None
        if sym in vao:
            kq = {f'{n}p': vuot_vni(gia, sym, vao[sym], n) for n in MOC_CHAM}
            kq['ngay_vao'] = vao[sym]
        p_now = gia_tai(gia, sym, asof)
        thieu = kiem_tra_luan(t)
        tu = vao.get(sym) or t.get('ngay_vao') or t.get('ngay_mo') or asof
        the.append(dict(luan=t, ho_so=h, kiem_chung=kc, ket_qua=kq, thieu=thieu, gia=p_now,
                        muc_tieu_cham=H.cham_muc_tieu(t, gia, tu), rr=H.rr(t, p_now),
                        san_sang=H.san_sang(t, h, thieu, p_now, kc, den)))

    cham_bat_dong(so, gia)
    H.ghi_du_doan(so_dd, the, D, gia, asof)
    H.cham_du_doan(so_dd, gia)
    so_dong = [r for r in so_db if r.get('trang_thai') == 'dong']
    tin_cay = dict(
        port_vs_may=tong_ket_bat_dong(so),
        tin=cham_tin.get('tong_ket') or {},
        daily=dict(da_cham=len(so_dong), dung=sum(1 for r in so_dong if r.get('ket_qua') == 'ĐÚNG')),
        bot=dict(metrics=(D.get('prod') or {}).get('metrics') or {}, asof=asof),
        kiem_chung_port=dict(
            da_cham=sum(1 for x in the for k in x['kiem_chung'] if k.get('trang_thai') == 'dong'),
            dung=sum(1 for x in the for k in x['kiem_chung'] if k.get('ket_qua') == 'ĐÚNG')),
    )
    wj(STATE / 'gia.json', gia)
    wj(STATE / 'so_bat_dong.json', so)
    wj(STATE / 'ngay_vao.json', vao)
    wj(STATE / 'so_du_doan.json', so_dd)
    bundle = dict(
        cap_nhat=now.isoformat(timespec='minutes'), asof=asof,
        den=(D.get('regime_live') or {}).get('light') or (D.get('regime') or [{}])[-1].get('light'),
        luan_diem=the, danh_muc=rj(ROOT / 'danh_muc.json', {}), so_bat_dong=so[-300:], tin_cay=tin_cay,
        loc=bang_loc(D), ten_may=TEN_MAY,
        du_doan=so_dd[-400:], do_chinh_xac=H.do_chinh_xac(so_dd), timing=H.tong_ket_timing(the),
        hieu_qua=H.hieu_qua(so_lenh, gia, asof),
        nguon=dict(site_asof=asof, tin_so_ban=len(reps), daily_ngay=(daily or {}).get('ngay')),
    )
    wj(OUT / 'bundle.json', bundle)
    return bundle


def kv_put(bundle: dict) -> bool:
    acc, ns, tok = (os.environ.get(k) for k in ('CF_ACCOUNT_ID', 'CF_KV_NAMESPACE_ID', 'CF_API_TOKEN'))
    if not (acc and ns and tok):
        print('KV: thiếu secret CF_* trong nsi-bot → bỏ qua đẩy KV (gói vẫn ở port/out/bundle.json)')
        return False
    import requests
    url = f'https://api.cloudflare.com/client/v4/accounts/{acc}/storage/kv/namespaces/{ns}/values/port/bundle'
    r = requests.put(url, headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
                     data=json.dumps(bundle, ensure_ascii=False).encode('utf-8'), timeout=60)
    if not r.ok:
        raise RuntimeError(f'KV ghi port/bundle lỗi {r.status_code}: {r.text[:200]}')
    print('KV: đã đẩy port/bundle')
    return True


def main() -> int:
    b = build()
    n_ng = sum(len(x['ho_so']['nguoc']) for x in b['luan_diem'])
    n_ch = sum(len(x['ho_so']['chua_tra_loi']) for x in b['luan_diem'])
    print(f"asof {b['asof']} · {len(b['luan_diem'])} luận điểm · {n_ng} chỗ máy ngược chiều · {n_ch} chưa trả lời · "
          f"{len(b['loc'])} mã trong bảng lọc · {len(b['so_bat_dong'])} dòng sổ bất đồng")
    kv_put(b)
    return 0


if __name__ == '__main__':
    sys.exit(main())
