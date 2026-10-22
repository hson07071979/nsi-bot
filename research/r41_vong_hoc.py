# -*- coding: utf-8 -*-
"""R41 — kiểm vòng học nhận định hằng ngày trên vũ trụ rộng (22/10/2026).

Chạy: python research/r41_vong_hoc.py <thư mục giá FireAnt> <funda_raw2.json> <D.json> <liq.json>
  · thư mục giá: mỗi mã một file [[ngày, đóng cửa, giá điều chỉnh, GTGD], ...] (FireAnt HistoricalQuotes)
  · funda_raw2.json: cùng định dạng fetch_funda.py; D.json: bản dữ liệu trang (lấy VN-Index + ngành)
Ghi evidence/r41_vong_hoc.json. Không dùng trong dây chuyền — dây chuyền chạy port/nhan_dinh.hoc trên port_gia.npz.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'port'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import nhan_dinh as N  # noqa: E402
import prep  # noqa: E402


def main(gia_dir, funda, dpath, liq_path):
    prep.NGAY_DA_NGUON = False
    D = json.load(open(dpath, encoding='utf-8'))
    v = {r['date']: r['vni'] for r in D['regime'] if r.get('vni')}
    lich = sorted(v)
    liq = json.load(open(liq_path))
    het = lich[-1]

    def load(s):
        d = json.load(open(os.path.join(gia_dir, s + '.json')))
        return {x[0]: x[2] for x in d if x[0] <= het and x[2]}
    B = N.Bang(lich, [v[d] for d in lich], {s: load(s) for s in liq})
    fu = prep.parse_funda(funda)
    ng = {s: (D['lookup'].get(s) or {}).get('sector', '') for s in liq}
    rows = N.chay_lui(B, liq, fu, ng)
    out = dict(so_ma=len(liq), so_mau=len(rows), tu=rows[0]['ngay'], den=rows[-1]['ngay'])
    # từng đặc trưng một mình (dấu +): ai thật sự mang thông tin
    tk = N.thong_ke(rows)
    out['tung_dac_trung'] = {}
    for k in N.DAC_TRUNG:
        ts = dict(ten=k, w={x: (1.0 if x == k else 0.0) for x in N.DAC_TRUNG}, b=0.0)
        out['tung_dac_trung'][k] = {n: N._cham_bo([r for r in rows if r['f'].get(k) is not None], n, ts, tk)
                                    for n in N.KY}
    for ten, ts in (('v1', N.TRONG_SO_V1),):
        h = N.hoc(rows, ts)
        h.pop('thong_ke', None)
        out['hoc_' + ten] = h
    # bộ đề xuất chấm lại như "bộ đang dùng" (để thấy nó tự so với mô hình luyện lại)
    if out['hoc_v1'].get('de_xuat'):
        h2 = N.hoc(rows, out['hoc_v1']['de_xuat'])
        h2.pop('thong_ke', None)
        out['hoc_de_xuat'] = dict(tong_dang_dung=h2['tong_dang_dung'], ket_luan=h2['ket_luan'])
    json.dump(out, open(os.path.join(os.path.dirname(__file__), '..', 'evidence', 'r41_vong_hoc.json'), 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    return out


if __name__ == '__main__':
    o = main(*sys.argv[1:5])
    h = o['hoc_v1']
    print(o['so_ma'], 'mã', o['so_mau'], 'mẫu', o['tu'], '→', o['den'])
    for k, x in o['tung_dac_trung'].items():
        print(f"  {k:10s}", ' '.join(f"{n}p IC {x[n]['ic']:+.3f} chênh {x[n]['chenh']:+.2f}%" for n in N.KY if x[n]))
    for n in N.KY:
        a, b = h['tong_dang_dung'][n], h['tong_mo_hinh'][n]
        print(f"{n:2d}p  v1: IC {a['ic']} chênh {a['chenh']}% top>VNI {a['top_thang_pct']}% đúng {a['dung_pct']}% | "
              f"mô hình: IC {b['ic']} chênh {b['chenh']}% top>VNI {b['top_thang_pct']}% đúng {b['dung_pct']}% "
              f"hơn {b['nam_hon']}/{b['so_nam']} năm")
    for y in h['theo_nam']:
        print('  ', y['nam'], {n: ((y['dang_dung'][n] or {}).get('ic'), (y['mo_hinh'].get(n) or {}).get('ic')) for n in N.KY})
    print(h['ket_luan'])
    print('đề xuất:', h['de_xuat'])
