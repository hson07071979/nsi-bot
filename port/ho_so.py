# -*- coding: utf-8 -*-
"""HỒ SƠ DOANH NGHIỆP + VĨ MÔ THUẬN/NGHỊCH HẰNG NGÀY + VÒNG HỌC ĐỘ NHẠY (28/10/2026).

Dữ liệu (nhánh port-data):
  port/ho_so/<MÃ>.json            hồ sơ từng mã — Claude viết, cập nhật mỗi quý (sau mùa BCTC)
  port/ho_so/nganh/<slug>.json    chuỗi giá trị chung của một ngành — hồ sơ mã chỉ viết phần riêng của mình
  port/ho_so/vi_mo_vn.json        biến vĩ mô Việt Nam chưa có nguồn cào hằng ngày (lãi huy động, tín dụng, đầu tư công…)
                                  — Claude cập nhật tay theo tin, có ngày và nguồn
  port/state/vi_mo/               sổ vĩ mô cào mỗi sáng (vimo/cao.py)

Mỗi hồ sơ khai các biến vĩ mô nhạy nhất: bien (khoá trong sổ vĩ mô hoặc vi_mo_vn.json), chieu (+1: biến tăng là tốt cho
doanh nghiệp, −1: biến tăng là xấu), kenh (biến → kênh → biên lợi nhuận/dòng tiền, một câu), tre (độ trễ).
Hằng ngày:
  trạng thái biến = xu hướng (tăng/giảm/đi ngang theo z) × chiều  →  THUẬN / NGHỊCH / TRUNG TÍNH
  trạng thái mã   = tổng các biến (≥ +1 THUẬN, ≤ −1 NGHỊCH, còn lại TRUNG TÍNH)
Vòng học (tự kiểm, không tự sửa hồ sơ):
  1. Sổ trạng thái điểm-thời-gian (state/so_ho_so.json): mỗi ngày ghi mã nào THUẬN/NGHỊCH; sau 20 và 60 phiên chấm
     bằng giá thật: nhóm THUẬN có hơn VN-Index nhiều hơn nhóm NGHỊCH không.
  2. Độ nhạy đo được: tương quan giữa lợi suất hơn VN-Index 20 phiên của mã và thay đổi 20 phiên của biến (cửa sổ không
     chồng nhau, từ 2019). Chiều đo được ngược chiều Claude viết với |t| ≥ 2 → ĐỀ XUẤT sửa hồ sơ (ghi công khai).
  3. Mã đang giải ngân lật sang NGHỊCH → cờ rà luận điểm + chuông.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np

TEN_TT = {1: 'THUẬN', -1: 'NGHỊCH', 0: 'TRUNG TÍNH'}
VI_TRI = dict(thuong_nguon='Thượng nguồn', trung_nguon='Trung nguồn', ha_nguon='Hạ nguồn', tich_hop='Tích hợp chuỗi',
              tai_chinh='Trung gian tài chính', ha_tang='Hạ tầng')
CUA_SO = 20
CHAM = (20, 60)


def _rj(p: Path, d=None):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return d


def doc(root: Path) -> dict:
    """→ dict(ho_so={mã: hồ sơ}, nganh={slug: trang ngành}, vi_mo_vn={bien: ...})."""
    d = root / 'ho_so'
    hs, ng = {}, {}
    if d.exists():
        for p in sorted(d.glob('*.json')):
            if p.stem == 'vi_mo_vn':
                continue
            x = _rj(p)
            if isinstance(x, dict) and x.get('ma'):
                hs[str(x['ma']).upper()] = x
        for p in sorted((d / 'nganh').glob('*.json')) if (d / 'nganh').exists() else []:
            x = _rj(p)
            if isinstance(x, dict):
                ng[x.get('slug') or p.stem] = x
    return dict(ho_so=hs, nganh=ng, vi_mo_vn=(_rj(d / 'vi_mo_vn.json', {}) or {}).get('bien') or {})


def bien_hom_nay(vi_mo: dict | None, vi_mo_vn: dict) -> dict:
    """Gộp sổ vĩ mô cào (moi_nhat.json → bien) và biến VN cập nhật tay → {khoá: dict(ten, xu_huong, ...)}."""
    out = {}
    for k, r in ((vi_mo or {}).get('bien') or {}).items():
        out[k] = dict(ten=r.get('ten'), xu_huong=r.get('xu_huong') if r.get('gia_tri') is not None else 'thiếu',
                      gia_tri=r.get('gia_tri'), dv=r.get('dv'), thay_doi=r.get('thay_doi'), do=r.get('do'),
                      cua_so=r.get('cua_so'), kieu=r.get('kieu'), z=r.get('z'), ngay_so=r.get('ngay_so'), nguon=r.get('nguon'),
                      tu_dong=True)
    for k, r in (vi_mo_vn or {}).items():
        out[k] = dict(ten=r.get('ten'), xu_huong=r.get('xu_huong') or 'thiếu', gia_tri=r.get('gia_tri'), dv=r.get('dv'),
                      ngay_so=r.get('ngay'), nguon=r.get('nguon'), ly_do=r.get('ly_do'), tu_dong=False)
    return out


def thanh_khoan(B, kl: dict | None, n: int = CUA_SO) -> dict | None:
    """Biến tự tính từ dữ liệu NSI: giá trị giao dịch ước tính toàn bộ mã (giá điều chỉnh × khối lượng), trung bình n phiên.
    Xu hướng = z của thay đổi trung bình n phiên so với các cửa sổ n phiên không chồng nhau trong lịch sử (như sổ vĩ mô)."""
    if B is None or not kl or not getattr(B, 'lich', None):
        return None
    tong = np.zeros(len(B.lich))
    for s, v in kl.items():
        c = np.asarray((B.c or {}).get(s), dtype=float)
        if c.shape != tong.shape:
            continue
        x = c * np.asarray(v, dtype=float)
        tong += np.where(np.isfinite(x), x, 0.0)
    if len(tong) < 10 * n or not np.isfinite(tong).all():
        return None
    tb = np.convolve(tong, np.ones(n) / n, mode='valid')          # tb[i] = trung bình phiên i..i+n-1
    if (tb <= 0).any():
        return None
    # thay đổi % của trung bình n phiên qua mỗi n phiên; cửa sổ không chồng nhau tính lùi từ phiên cuối
    thay = [(tb[i] / tb[i - n] - 1) * 100 for i in range(len(tb) - 1, n - 1, -n)][:121]
    c, lich = thay[0], thay[1:]
    sd = float(np.std(lich)) if len(lich) >= 8 else 0.0
    if sd <= 0:
        return None
    z = round(float(c) / sd, 2)
    xh = 'tang' if z >= 0.5 else 'giam' if z <= -0.5 else 'ngang'
    return dict(ten='Thanh khoản chứng khoán VN (TB 20 phiên)', xu_huong=xh, gia_tri=round(float(tb[-1]) / 1e9, 0),
                dv='tỷ đồng/phiên (ước tính)', thay_doi=round(float(c), 2), do='pt', cua_so=n, kieu='ngày', z=z,
                ngay_so=B.lich[-1], nguon='NSI: giá điều chỉnh × khối lượng các mã trong port_gia', tu_dong=True)


def _dau(xh: str) -> int:
    return 1 if xh == 'tang' else -1 if xh == 'giam' else 0


def trang_thai(hs: dict, bien: dict) -> dict:
    """Trạng thái vĩ mô hôm nay của một mã theo các biến nhạy nó khai."""
    dong, tong, thieu = [], 0, 0
    for b in hs.get('bien') or []:
        k = b.get('bien')
        v = bien.get(k) or {}
        xh = v.get('xu_huong') or 'thiếu'
        try:
            chieu = int(b.get('chieu') or 0)
        except (TypeError, ValueError):
            chieu = 0
        tac = _dau(xh) * chieu if xh != 'thiếu' else 0
        thieu += xh == 'thiếu'
        tong += tac
        dong.append(dict(bien=k, ten=v.get('ten') or b.get('ten') or k, xu_huong=xh, chieu=chieu, tac=tac, tt=TEN_TT[tac],
                         kenh=b.get('kenh'), tre=b.get('tre'), gia_tri=v.get('gia_tri'), dv=v.get('dv'),
                         thay_doi=v.get('thay_doi'), do=v.get('do'), cua_so=v.get('cua_so'), kieu=v.get('kieu'),
                         ngay_so=v.get('ngay_so'), tu_dong=v.get('tu_dong'), ly_do=v.get('ly_do')))
    c = 1 if tong >= 1 else -1 if tong <= -1 else 0
    return dict(tong=TEN_TT[c], dau=c, diem=tong, bien=dong, thieu=thieu)


# ---------------------------------------------------------------- vòng học 2: độ nhạy đo được
def doc_chuoi(vi_mo_dir: Path, k: str) -> list[tuple[str, float]]:
    p = vi_mo_dir / 'chuoi' / f'{k}.csv'
    if not p.exists():
        return []
    out = []
    with p.open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                out.append((r['ngay'], float(r['gia_tri'])))
            except (KeyError, ValueError):
                pass
    return out


def _theo_lich(chuoi: list[tuple[str, float]], lich: list[str]) -> np.ndarray:
    """Giá trị biến tại từng phiên (giá trị gần nhất có ngày ≤ phiên; biến tháng tự kéo dài)."""
    a = np.full(len(lich), np.nan)
    j, last = 0, np.nan
    for i, d in enumerate(lich):
        while j < len(chuoi) and chuoi[j][0] <= d:
            last = chuoi[j][1]
            j += 1
        a[i] = last
    return a


def do_nhay(B, sym: str, x: np.ndarray, do: str = 'pct', n: int = CUA_SO) -> dict | None:
    """Tương quan (lợi suất mã − lợi suất VN-Index, n phiên) với (thay đổi của biến, n phiên); cửa sổ không chồng nhau."""
    a = (B.c or {}).get(sym) if B is not None else None
    if a is None or len(a) != len(x):
        return None
    v = np.asarray(B.vni, dtype=float)
    ys, xs = [], []
    for i in range(len(a) - 1, n - 1, -n):
        j = i - n
        if not (a[i] > 0 and a[j] > 0 and v[i] > 0 and v[j] > 0 and np.isfinite(x[i]) and np.isfinite(x[j])):
            continue
        if do == 'diem':
            dx = x[i] - x[j]
        elif x[j]:
            dx = x[i] / x[j] - 1
        else:
            continue
        ys.append((a[i] / a[j]) - (v[i] / v[j]))
        xs.append(dx)
    m = len(ys)
    if m < 12:
        return dict(n=m, r=None, t=None)
    xs, ys = np.array(xs), np.array(ys)
    if xs.std() == 0 or ys.std() == 0:
        return dict(n=m, r=0.0, t=0.0)
    r = float(np.corrcoef(xs, ys)[0, 1])
    t = r * math.sqrt((m - 2) / max(1e-9, 1 - r * r))
    return dict(n=m, r=round(r, 3), t=round(t, 2))


def hoc_do_nhay(hs_all: dict, B, vi_mo_dir: Path, vi_mo: dict | None) -> dict:
    """→ {mã: {biến: dict(n, r, t, khop)}} + danh sách đề xuất sửa (chiều đo được ngược chiều viết, |t| ≥ 2)."""
    bien_meta = (vi_mo or {}).get('bien') or {}
    cache, out, de_xuat = {}, {}, []
    lich = list(B.lich) if B is not None else []
    for sym, hs in hs_all.items():
        for b in hs.get('bien') or []:
            k = b.get('bien')
            if k not in bien_meta:
                continue                    # biến VN cập nhật tay: chưa có chuỗi lịch sử để đo
            if k not in cache:
                cache[k] = _theo_lich(doc_chuoi(vi_mo_dir, k), lich) if lich else None
            x = cache[k]
            if x is None:
                continue
            d = do_nhay(B, sym, x, bien_meta[k].get('do') or 'pct')
            if not d:
                continue
            try:
                chieu = int(b.get('chieu') or 0)
            except (TypeError, ValueError):
                chieu = 0
            khop = None
            if d.get('t') is not None and abs(d['t']) >= 2 and chieu:
                khop = (d['r'] > 0) == (chieu > 0)
                if not khop:
                    de_xuat.append(dict(ma=sym, bien=k, chieu_viet=chieu, r=d['r'], t=d['t'], n=d['n'],
                                        noi_dung=f'{sym}: hồ sơ viết {k} tăng là {"tốt" if chieu > 0 else "xấu"}, nhưng giá {d["n"]} '
                                                 f'cửa sổ 20 phiên từ 2019 cho tương quan {d["r"]:+.2f} (t {d["t"]:+.1f}) — '
                                                 'xem lại kênh truyền dẫn hoặc độ trễ'))
            d['khop'] = khop
            out.setdefault(sym, {})[k] = d
    return dict(theo_ma=out, de_xuat=de_xuat)


# ---------------------------------------------------------------- vòng học 1: sổ trạng thái điểm-thời-gian
def ghi_so(so: list[dict], ngay: str, tt_all: dict) -> list[dict]:
    so = [r for r in so if r.get('ngay') != ngay]
    for sym, t in tt_all.items():
        so.append(dict(ngay=ngay, ma=sym, dau=t['dau'], diem=t['diem']))
    return so[-60000:]


def cham_so(so: list[dict], B) -> dict:
    """Lợi suất hơn VN-Index sau 20/60 phiên của nhóm THUẬN vs NGHỊCH (mỗi dòng sổ chấm khi đủ phiên)."""
    if B is None or not B.lich:
        return {}
    pos = {d: i for i, d in enumerate(B.lich)}
    v = np.asarray(B.vni, dtype=float)
    out = {}
    for n in CHAM:
        g = {1: [], -1: [], 0: []}
        for r in so:
            i = pos.get(r['ngay'])
            a = B.c.get(r['ma'])
            if i is None or a is None or i + n >= len(B.lich) or not (a[i] > 0 and a[i + n] > 0):
                continue
            g[r['dau']].append((a[i + n] / a[i] - v[i + n] / v[i]) * 100)
        out[f'{n}p'] = {TEN_TT[k]: dict(n=len(x), tb=round(float(np.mean(x)), 2) if x else None) for k, x in g.items()}
        a1, a2 = out[f'{n}p']['THUẬN']['tb'], out[f'{n}p']['NGHỊCH']['tb']
        out[f'{n}p']['chenh'] = round(a1 - a2, 2) if a1 is not None and a2 is not None else None
    return out


# ---------------------------------------------------------------- giá + nền cho thẻ port (phần 2)
def gia_nen(B, sym: str, n: int = 250) -> dict | None:
    a = (B.c or {}).get(sym) if B is not None else None
    if a is None:
        return None
    k = min(n, len(a))
    w = a[-k:]
    ngay = list(B.lich[-k:])
    c = [round(float(x), 2) if np.isfinite(x) else None for x in w]
    f = [x for x in w[-30:] if np.isfinite(x)]
    if not f:
        return None
    ok = [x for x in w if np.isfinite(x)]
    return dict(ngay=ngay, gia=c, nen_tren=round(float(max(f)), 2), nen_duoi=round(float(min(f)), 2),
                nen_tu=ngay[-30] if len(ngay) >= 30 else ngay[0], dinh=round(float(max(ok)), 2),
                ngay_dinh=ngay[int(np.nanargmax(w))])


def chay(root: Path, state: Path, B, asof: str, vi_the: set[str] | None = None, gui=None,
         ma_port: list[str] | None = None, kl: dict | None = None) -> dict:
    """Một lượt: đọc hồ sơ + vĩ mô, chấm thuận/nghịch, ghi sổ, học độ nhạy, cờ + chuông mã đang cầm lật NGHỊCH."""
    D = doc(root)
    vdir = state / 'vi_mo'
    vi_mo = _rj(vdir / 'moi_nhat.json')
    bien = bien_hom_nay(vi_mo, D['vi_mo_vn'])
    tk = thanh_khoan(B, kl)
    if tk:
        bien['thanh_khoan_ck_vn'] = tk
    tt = {s: trang_thai(h, bien) for s, h in D['ho_so'].items()}
    so = _rj(state / 'so_ho_so.json', []) or []
    truoc = {}
    for r in so:
        if r.get('ngay') < asof:
            truoc[r['ma']] = r['dau']                 # trạng thái gần nhất trước hôm nay
    so = ghi_so(so, asof, tt)
    (state / 'so_ho_so.json').write_text(json.dumps(so, ensure_ascii=False), encoding='utf-8')
    co = []
    for s in sorted(set(vi_the or ()) & set(tt)):
        if tt[s]['dau'] == -1 and truoc.get(s, 0) != -1:
            nghich = [b['ten'] for b in tt[s]['bien'] if b['tac'] == -1]
            co.append(dict(ma=s, ngay=asof, noi_dung=f'{s} lật sang NGHỊCH vĩ mô: ' + ', '.join(nghich) + ' — rà lại luận điểm'))
    if co and gui:
        try:
            gui('Port: mã đang giải ngân lật NGHỊCH vĩ mô', '\n'.join(c['noi_dung'] for c in co))
        except Exception as e:  # noqa: BLE001 — chuông hỏng không được làm hỏng lượt chạy
            print('chuông hồ sơ lỗi:', e)
    hoc = hoc_do_nhay(D['ho_so'], B, vdir, vi_mo) if B is not None else dict(theo_ma={}, de_xuat=[])
    for s, t in tt.items():
        for b in t['bien']:
            b['do_nhay'] = (hoc['theo_ma'].get(s) or {}).get(b['bien'])
    gia = {s: gia_nen(B, s) for s in sorted(set(ma_port or []) | set(D['ho_so']))} if B is not None else {}
    gia = {s: g for s, g in gia.items() if g}
    return dict(ho_so=D['ho_so'], nganh=D['nganh'], trang_thai=tt, bien=bien,
                vi_mo_ngay=(vi_mo or {}).get('ngay'), vi_mo_loi=(vi_mo or {}).get('loi_nguon') or [],
                co=co, hoc=dict(de_xuat=hoc['de_xuat'], cham=cham_so(so, B), so_dong=len(so)),
                gia=gia, vi_tri_ten=VI_TRI)
