# -*- coding: utf-8 -*-
"""Ghép các phần mới của Lọc port (pool tuần — pool.py, 24/10/2026; lọc quý TOP110 — loc_quy.py, 22/10/2026) vào lượt build (anh Sơn 22/10/2026):
sổ giả lập + NAV (sim.py), đọc BCTC sâu (bctc.py), nhận định hằng ngày + vòng học (nhan_dinh.py), nhắc review (nhac.py).

Dữ liệu đều là thứ đã có, chỉ nối lại:
  · trang nguyensonfinance (DATA): nến 240 phiên, VN-Index, BCTC 12 quý, bảng tra cứu, đèn thị trường;
  · data/port_gia.npz — giá thô + giá điều chỉnh từ 2019 do dây chuyền hằng ngày cắt ra từ fa.npz (FireAnt);
  · data/funda_raw2.json — BCTC từng dòng từ Vietcap mà dây chuyền hằng ngày đã tải (cache "bctc-");
  · nsi-tin: mốc hỗ trợ/kháng cự của Daily.
Thiếu file nào thì phần đó lùi về dữ liệu của trang web và ghi rõ trong `nguon_moi`.
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import bctc as BC
import loc_quy as LQ
import nhac as NH
import nhan_dinh as ND
import pool as PO
import sim as SM

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
STATE = ROOT / 'state'


def rj(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def wj(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def doc_so_nd(state: Path = STATE) -> list[dict]:
    """Sổ nhận định chia theo tháng (state/so_nhan_dinh/YYYY-MM.json): mỗi lượt chỉ vài tháng gần nhất đổi,
    nên git không phải lưu lại cả sổ mỗi ngày."""
    out = []
    for f in sorted((state / 'so_nhan_dinh').glob('*.json')):
        out += rj(f, [])
    return out


def ghi_so_nd(so: list[dict], state: Path = STATE) -> None:
    thang: dict[str, list] = {}
    for r in so:
        thang.setdefault(r['ngay'][:7], []).append(r)
    for k, v in thang.items():
        f = state / 'so_nhan_dinh' / f'{k}.json'
        moi = json.dumps(v, ensure_ascii=False, separators=(',', ':'))
        if not f.exists() or f.read_text(encoding='utf-8') != moi:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(moi, encoding='utf-8')


def _port_gia():
    f = Path(os.environ.get('PORT_GIA') or REPO / 'data' / 'port_gia.npz')
    if not f.exists():
        return None
    import numpy as np
    z = np.load(f, allow_pickle=True)
    return dict(cal=[str(x) for x in z['cal']], sym=[str(x) for x in z['sym']], close=z['close'], adj=z['adj'])


def _funda_rows(D: dict):
    """BCTC theo quý có ngày được dùng (avail). Có funda_raw2.json thì đọc đúng cách của bot (prep.parse_funda,
    không nhìn trước); không có thì lấy 12 quý của trang web, coi như đã công bố (chỉ dùng cho nhận định hôm nay)."""
    f = Path(os.environ.get('FUNDA_RAW') or REPO / 'data' / 'funda_raw2.json')
    if f.exists():
        import sys
        sys.path.insert(0, str(REPO))
        cwd = os.getcwd()
        try:
            os.chdir(REPO)
            import prep
            return prep.parse_funda(str(f)), json.loads(f.read_text(encoding='utf-8')), 'funda_raw2.json'
        finally:
            os.chdir(cwd)
    out = {}
    for s, x in (D.get('funda') or {}).items():
        rows = []
        for k, q in enumerate(x.get('q') or []):
            try:
                qq, yy = q[1:].split('/')
                y, qi = 2000 + int(yy), int(qq)
            except ValueError:
                continue
            g = lambda a: (x.get(a) or [None] * (k + 1))[k] if k < len(x.get(a) or []) else None  # noqa: E731
            rows.append(dict(y=y, q=qi, avail=date.min, npat=g('np'), rev=g('rev'), pe=g('pe'), pb=g('pb'),
                             roe=g('roe')))
        out[s] = rows
    return out, None, 'trang web (12 quý, không có ngày công bố → không chạy lùi)'


def _bang_nhan_dinh(D: dict, pg):
    vni = {r['date']: r['vni'] for r in D.get('regime') or [] if r.get('date') and r.get('vni')}
    if pg:
        lich = [d for d in pg['cal'] if d in vni]
        pos = {d: i for i, d in enumerate(pg['cal'])}
        gia = {}
        for j, s in enumerate(pg['sym']):
            col = pg['adj'][:, j]
            gia[s] = {d: float(col[pos[d]]) for d in lich if col[pos[d]] == col[pos[d]]}
        return ND.Bang(lich, [vni[d] for d in lich], gia), 'port_gia.npz (giá điều chỉnh từ 2019)'
    lich = sorted(vni)[-300:]
    gia = {}
    for s, c in (D.get('candles') or {}).items():
        gia[s] = {b[0]: float(b[4]) for b in (c or {}).get('bars') or [] if len(b) >= 5 and b[4]}
    return ND.Bang(lich, [vni[d] for d in lich], gia), 'nến 240 phiên của trang web (không đủ để chạy lùi)'


def chay(D: dict, luan: dict[str, dict], danh_muc: dict, gia: dict, daily: dict | None, the: list[dict],
         asof: str, gui_chuong: bool = True, state: Path = STATE, root: Path = ROOT) -> dict:
    nguon = {}
    pg = _port_gia()
    # ------------------------------------------------ 1. sổ giả lập
    P = SM.chuoi_gia(D, gia)
    if pg:
        pos = {d: i for i, d in enumerate(pg['cal'])}
        for s in set(luan) & set(pg['sym']):
            j = pg['sym'].index(s)
            col = pg['close'][:, j]
            for d, i in pos.items():
                if d >= '2026-01-01' and col[i] == col[i] and d not in (gia.get(s) or {}):
                    P.setdefault(s, {})[d] = float(col[i])
    ho_tro = {}
    for s in luan:
        row = SM.daily_row(daily, s) or {}
        v = [x for x in (SM._vung(z) for z in row.get('ho_tro') or []) if x]
        if v:
            ho_tro[s] = v[0][0]
    so = rj(state / 'so_gia_lap.json', None) or SM.so_moi()
    ngay = [d for d in sorted(P.get('VNINDEX') or {}) if d >= (danh_muc or {}).get('ngay', asof) and d <= asof]
    lk_ng = {s_: (x or {}).get('sector', '') for s_, x in (D.get('lookup') or {}).items()}
    so = SM.chay(so, P, ngay, danh_muc, luan, ho_tro, nganh=lk_ng)
    wj(state / 'so_gia_lap.json', so)
    gia_lap = dict(tong_ket=SM.tong_ket(so, P), nav=so['nav'], lenh=so['lenh'][-200:], co=so['co'][-50:],
                   luat=SM.LUAT, ghi_chu=so.get('ghi_chu'))
    de_xuat = {}                      # 24/10/2026: bỏ mục tiêu T1/T2 — không đề xuất nữa
    # ------------------------------------------------ 2. đọc BCTC sâu
    rows_f, raw, nguon['bctc'] = _funda_rows(D)
    bc = BC.phan_tich_nhieu(raw, sorted(luan)) if raw else {}
    # ------------------------------------------------ 3. nhận định hằng ngày + vòng học
    B, nguon['gia_nhan_dinh'] = _bang_nhan_dinh(D, pg)
    lk = D.get('lookup') or {}
    nganh = {s: (lk.get(s) or {}).get('sector', '') for s in set(lk) | set(luan)}
    # R41: học + nhận định trên mọi mã đủ thanh khoản trong port_gia.npz (~170 mã), không chỉ ~110 mã TOP-N
    vu_tru = sorted({s for s, x in lk.items() if x.get('inuni')} | set(luan) | set((pg or {}).get('sym') or []))
    vu_tru = [s for s in vu_tru if s in B.c]
    ts = rj(root / 'trong_so.json', None) or ND.TRONG_SO_V1
    hoc = None
    if pg and raw:
        mau = ND.chay_lui(B, vu_tru, rows_f, nganh)
        hoc = ND.hoc(mau, ts)
        tk = hoc['thong_ke']
        wj(state / 'thong_ke_dac_trung.json', tk)
        hoc.pop('thong_ke', None)
    else:
        tk = rj(state / 'thong_ke_dac_trung.json', {}) or {}
    may = {x['luan']['ma']: {k: v['chieu'] for k, v in x['ho_so']['may'].items()} for x in the}
    so_nd = doc_so_nd(state)
    if B.lich and B.lich[-1] <= asof:
        ND.ghi_hom_nay(so_nd, B, vu_tru, rows_f, nganh, ts, tk, may)
    ND.cham_so(so_nd, B)
    port_syms = set(luan)
    for r in so_nd:                       # mã ngoài port: giữ dòng gọn để sổ không phình
        if r['ma'] not in port_syms:
            r.pop('ly_do', None)
            r.pop('f', None)
    ghi_so_nd(so_nd, state)
    hom_nay = [r for r in so_nd if r['ngay'] == (B.lich[-1] if B.lich else None) and r['ma'] in port_syms]
    nhan_dinh = dict(hom_nay=hom_nay, trong_so=ts, nguong=ND.NGUONG, bien=ND.BIEN,
                     do_chinh_xac=dict(tat_ca=ND.tong_ket_so(so_nd), port=ND.tong_ket_so(so_nd, port_syms)),
                     lich_su_port=[r for r in so_nd if r['ma'] in port_syms][-400:], hoc=hoc,
                     so_ma_theo_doi=len(vu_tru))
    # ------------------------------------------------ 3b. lọc quý TOP110 (22/10/2026) — nối BCTC trang đã cào
    # Lọc quý giữ làm sổ đo + chạy lùi; chuông chuyển sang pool tuần (24/10/2026) để khỏi hai danh sách cùng báo
    loc_quy = LQ.chay(D, rows_f, B, asof, state, pg_co=bool(pg), raw_co=bool(raw), gui_chuong=False, luan=luan)
    # ------------------------------------------------ 3c. pool tuần (24/10/2026) — watchlist NSI + 20–30 mã riêng
    pool = PO.chay(D, rows_f, B if pg else None, asof, state, luan=luan, gui_chuong=gui_chuong)
    # ------------------------------------------------ 4. nhắc review
    st = NH.kiem(D, luan, rj(state / 'nhac.json', {}), gia_lap['tong_ket'].get('co_mo') or [], gui_that=gui_chuong)
    wj(state / 'nhac.json', st)
    nguon['gia_gia_lap'] = 'port_gia.npz + ảnh chụp port' if pg else 'nến 240 phiên + ảnh chụp port'
    return dict(gia_lap=gia_lap, muc_tieu_de_xuat=de_xuat, bctc=bc, nhan_dinh=nhan_dinh, loc_quy=loc_quy, pool=pool,
                nhac=dict(quy=st['quy'], ky_review=st['ky_review'], lan_cuoi=st.get('lan_cuoi')), nguon_moi=nguon)
