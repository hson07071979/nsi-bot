# -*- coding: utf-8 -*-
"""Ke hoach ban phien toi (exit_rules.ke_hoach_ban, 03/10/2026) + nut nghien cuu chot 1/3 (R34) mac dinh TAT.
Chay: python tests/test_ke_hoach_ban.py"""
import os, sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import exit_rules as ER
import engine2 as E
from produce2 import PROD

C = dict(E.CFG); C.update(PROD)


def _gain_ok(k, cost, prev, peak, held, b10=0, b20=0, probe=False):
    """Nguong phai KHOP decide(): ngay duoi -> ban, ngay tren -> khong ban."""
    if k['viec'] != 'NGUONG':
        return
    for c, ban in ((k['nguong'] * 0.999, True), (k['nguong'] * 1.001, False)):
        d = ER._ban_tai(C, cost, peak, held, prev, b10, b20, c, probe)
        assert bool(d.get('rule')) == ban, (k, c, d)


def test_khoa_lai():
    k = ER.ke_hoach_ban(C, 100.0, 0.13, 6, [110.0] * 40)
    assert k['viec'] == 'NGUONG' and abs(k['nguong'] - 106.0) < 0.01 and ER.is_lock_reason(k['ly_do'])
    _gain_ok(k, 100.0, [110.0] * 40, 0.13, 6)


def test_momentum_va_ma10():
    k = ER.ke_hoach_ban(C, 100.0, 0.0, 4, [100.0] * 40)
    assert k['viec'] == 'NGUONG' and k['ly_do'].startswith('Momentum')
    _gain_ok(k, 100.0, [100.0] * 40, 0.0, 4)
    k = ER.ke_hoach_ban(C, 100.0, 0.25, 10, [120.0] * 40, b10=1)
    assert k['viec'] == 'NGUONG' and 'MA10' in k['ly_do']
    _gain_ok(k, 100.0, [120.0] * 40, 0.25, 10, b10=1)


def test_lenh_do_va_chua_ban_duoc():
    assert ER.ke_hoach_ban(C, 100.0, 0.0, 3, [100.0] * 40, probe_fail=True)['viec'] == 'BAN'
    assert ER.ke_hoach_ban(C, 100.0, 0.0, 2, [100.0] * 40)['viec'] == 'CHUA_BAN_DUOC'


def test_buoc_gia():
    assert ER.buoc_gia(9000) == 10 and ER.buoc_gia(20000) == 50 and ER.buoc_gia(70000) == 100
    k = ER.ke_hoach_ban(C, 68100.0, 0.113, 15, [75800.0] * 40, fx=1.0)
    assert k['nguong_raw'] % 100 == 0 and k['nguong_raw'] <= k['nguong'] + 100


def test_chot_mot_phan_tat_trong_prod():
    # R34: chot 1/3 khi lai 15/20/25% lam GIAM loi nhuan moi muc -> KHONG vao PROD
    assert PROD.get('tp_part') is None and E.CFG.get('tp_part') is None


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_') and callable(f):
            f(); n += 1; print('ok', k)
    print(f'{n}/{n} test ke hoach ban dat')
