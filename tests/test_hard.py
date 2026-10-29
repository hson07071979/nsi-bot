# -*- coding: utf-8 -*-
"""Lệnh Hard (28/10/2026): khuôn lệnh, và — khi có data/fa.npz — bộ máy xử lý đúng.

  python tests/test_hard.py
Các phần cần dữ liệu tự bỏ qua khi không có data/fa.npz (như các test bộ máy khác).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import hard as HD  # noqa: E402

OK = []


def kiem(dk, ten):
    assert dk, ten
    OK.append(ten)


# ---------------- 1. khuôn lệnh ----------------
x, e = HD.chuan(dict(id='a', loai='mua', sym='hpg', ngay='2026-10-28', gia='26.55', pct_nav=10))
kiem(x and x['sym'] == 'HPG' and x['gia'] == 26.55 and x['pct_nav'] == 10.0, 'chuẩn hoá lệnh mua')
kiem(HD.chuan(dict(id='a', loai='mua', sym='HPG', ngay='2026-10-28', gia=26, pct_nav=0))[0] is None, '% NAV = 0 bị loại')
kiem(HD.chuan(dict(id='a', loai='mua', sym='HPG', ngay='2026-10-28', gia=26, pct_nav=101))[0] is None, '% NAV > 100 bị loại')
kiem(HD.chuan(dict(id='a', loai='ban', sym='HPG', ngay='2026-10-28', gia=26, phan=0.3))[0] is None, 'phần bán lạ bị loại')
kiem(HD.chuan(dict(id='a', loai='ban', sym='HPG', ngay='2026-10-28', gia=26, phan=0.25))[0]['phan'] == 0.25, 'bán 25%')
kiem(HD.chuan(dict(id='a', loai='xx', sym='HPG', ngay='2026-10-28', gia=26))[0] is None, 'loại lệnh lạ bị loại')
kiem(HD.chuan(dict(id='a', loai='mua', sym='HPG', ngay='28/10/2026', gia=26, pct_nav=5))[0] is None, 'ngày sai khuôn bị loại')
kiem(HD.chuan(dict(id='a', loai='mua', sym='HPG', ngay='2026-10-28', gia=-1, pct_nav=5))[0] is None, 'giá âm bị loại')

with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, 'manual.json')
    json.dump(dict(hard=[
        dict(id='b', loai='mua', sym='HPG', ngay='2026-10-28', gia=26, pct_nav=5, luc='2026-10-28T10:00'),
        dict(id='a', loai='ban', sym='FPT', ngay='2026-10-27', gia=60, phan=1, luc='2026-10-27T10:00'),
        dict(id='c', loai='mua', sym='VCB', ngay='2026-10-28', gia=60, pct_nav=5, huy='2026-10-28T11:00'),
        dict(id='a', loai='mua', sym='SSI', ngay='2026-10-28', gia=20, pct_nav=5),
        'rac']), open(p, 'w'))
    H, loi = HD.doc(p)
    kiem([o['id'] for o in H] == ['a', 'b'], 'bỏ lệnh huỷ, xếp theo ngày')
    kiem(len(loi) == 2, 'báo id trùng + lệnh hỏng khuôn')
    kiem(len(HD.doc(p, ke_ca_huy=True)[0]) == 3, 'đọc được cả lệnh đã huỷ khi cần')
    json.dump({'v': 1}, open(p, 'w'))
    kiem(HD.doc(p) == ([], []), 'manual.json chưa có khoá hard')
    open(p, 'w').write('{hỏng')
    kiem(HD.doc(p) == ([], []), 'manual.json hỏng -> không lệnh nào')

# ---------------- 2. bộ máy (cần data/fa.npz) ----------------
if not os.path.exists('data/fa.npz'):
    print(f'test_hard: {len(OK)} kiểm tra khuôn đạt — bỏ qua phần bộ máy (không có data/fa.npz)')
    sys.exit(0)

import produce2 as P2  # noqa: E402
import engine2 as E  # noqa: E402

d, _, _, _ = E.load()
cal = [str(c) for c in d['cal']]
S = [str(s) for s in d['sym']]


def gia(sym, ngay, f='PriceClose'):
    return float(d[f][cal.index(ngay), S.index(sym)]) / 1000


def chay(lenh):
    r = E.run(dict(P2.PROD, hard_orders=lenh), log=False)
    return r, {f['id']: f for f in r['hard']['fills']}, r['hard']['pending']


r0 = E.run(dict(P2.PROD), log=False)
r1 = E.run(dict(P2.PROD, hard_orders=[]), log=False)
kiem(len(r0['trades']) == len(r1['trades']) and r0['nav'] == r1['nav'], 'không có lệnh Hard = PROD y hệt')

# chọn một mã thanh khoản không nằm trong sổ ở phiên mua thử
D1 = cal[-6]
ung = [s for s in ('HPG', 'VNM', 'FPT', 'MWG', 'VCB', 'SSI', 'GAS') if s in S and s not in r0['pos']
       and not any(t['sym'] == s and t['entry'] <= D1 <= t['exit'] for t in r0['trades'])]
m = ung[0]
lenh = [dict(id='m1', loai='mua', sym=m, ngay=D1, gia=gia(m, D1), pct_nav=7.0, luc='1'),
        dict(id='m2', loai='mua', sym=m, ngay='2099-01-01', gia=gia(m, cal[-1]), pct_nav=1.0, luc='2')]
r, F, P = chay(lenh)
kiem(F['m1']['ok'] and F['m1']['sh'] >= 100, 'Hard Buy khớp')
kiem(abs(F['m1']['pct_thuc'] - 7.0) < 0.5, 'Hard Buy đúng ~% NAV anh nhập')
kiem([x['id'] for x in P] == ['m2'] and 'm2' not in F, 'lệnh phiên chưa có dữ liệu -> chờ, chưa khớp')
tr = [t for t in r['trades'] if t['sym'] == m and t['entry'] == D1]
po = r['pos'].get(m)
kiem(bool(tr) or (po is not None and po.hard == 'mua'), 'vị thế Hard Buy nằm trong sổ hệ thống')
kiem(all(t.get('hard') == 'mua' for t in tr), 'lệnh bán của vị thế Hard Buy mang nhãn Hard')

# bán trước T+3 bị từ chối; giá ngoài biên độ bị từ chối
D2 = cal[cal.index(D1) + 1]
r, F, _ = chay([dict(id='m1', loai='mua', sym=m, ngay=D1, gia=gia(m, D1), pct_nav=7.0, luc='1'),
                dict(id='b1', loai='ban', sym=m, ngay=D2, gia=gia(m, D2), phan=1.0, luc='2'),
                dict(id='x1', loai='mua', sym=ung[1], ngay=D1, gia=round(gia(ung[1], D1, 'PriceBasic') * 1.2, 2),
                     pct_nav=5.0, luc='3')])
kiem(not F['b1']['ok'] and 'chưa về' in F['b1']['ly_do'], 'Hard Sell trước T+3 bị chặn')
kiem(not F['x1']['ok'] and 'biên độ' in F['x1']['ly_do'], 'giá ngoài trần/sàn bị chặn')

# bán đủ T+3: đúng giá anh điền, nhãn Hard Sell
D4 = cal[cal.index(D1) + 3]
r, F, _ = chay([dict(id='m1', loai='mua', sym=m, ngay=D1, gia=gia(m, D1), pct_nav=7.0, luc='1'),
                dict(id='b2', loai='ban', sym=m, ngay=D4, gia=gia(m, D4), phan=0.5, luc='2')])
if F['b2']['ok']:
    t = [t for t in r['trades'] if t.get('hard_id') == 'b2'][0]
    kiem(t['reason'] == HD.LY_DO_BAN and t['hard'] == 'ban', 'Hard Sell ghi lý do + nhãn')
    kiem(abs(t['exit_raw'] - gia(m, D4) * 1000) < 1, 'Hard Sell khớp đúng giá anh điền')
    kiem(t['sh'] % 100 == 0 and t['sh'] >= 100, 'Hard Sell làm tròn lô 100')
else:
    kiem('bot đã bán' in F['b2']['ly_do'], 'bot đã bán trước -> Hard Sell báo rõ lý do')

# trần: muốn 100% NAV -> bị chặn bởi trần (mã / ngành / tiền mặt)
r, F, _ = chay([dict(id='g1', loai='mua', sym=m, ngay=D1, gia=gia(m, D1), pct_nav=100.0, luc='1')])
kiem(F['g1']['ok'] and F['g1']['pct_thuc'] <= 100 * P2.PROD['max_pos'] + 0.1 and F['g1']['rang_buoc'], 'Hard Buy vẫn chịu trần')

# ngày không giao dịch -> phiên kế tiếp
import datetime as _dt  # noqa: E402
k = next(i for i in range(len(cal) - 30, len(cal) - 1)
         if (_dt.date.fromisoformat(cal[i + 1]) - _dt.date.fromisoformat(cal[i])).days > 1)
nghi = (_dt.date.fromisoformat(cal[k]) + _dt.timedelta(days=1)).isoformat()
r, F, _ = chay([dict(id='h1', loai='mua', sym=m, ngay=nghi, gia=gia(m, cal[k + 1]), pct_nav=3.0, luc='1')])
kiem(F['h1']['phien'] == cal[k + 1], 'ngày nghỉ -> phiên giao dịch kế tiếp')

# 30/10/2026 (ca ORS 29/10): Hard Sell cùng phiên với lệnh thoát của bot -> lệnh tay thắng, khớp giá anh điền
tb = next(t for t in reversed(r0['trades']) if not t.get('hard') and t['held'] >= 3 and t.get('frac', 1) >= 1
          and not str(t.get('reason', '')).startswith('Cond9'))
gb = round(gia(tb['sym'], tb['exit'], 'PriceHigh') if 'PriceHigh' in d else gia(tb['sym'], tb['exit']), 2)
r, F, _ = chay([dict(id='o1', loai='ban', sym=tb['sym'], ngay=tb['exit'], gia=gb, phan=1.0, luc='1')])
kiem(F['o1']['ok'], 'Hard Sell cùng phiên bot thoát -> lệnh tay khớp (không bị bot ghi đè)')
cung = [t for t in r['trades'] if t['sym'] == tb['sym'] and t['exit'] == tb['exit']]
kiem(len(cung) == 1 and cung[0].get('hard') == 'ban' and abs(cung[0]['exit_raw'] - gb * 1000) < 1,
     'phiên đó chỉ còn lệnh Hard Sell, đúng giá anh điền')

print(f'test_hard: {len(OK)} kiểm tra đạt')
