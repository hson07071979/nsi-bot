# -*- coding: utf-8 -*-
"""R38: cac tieu chi xep hang nghien cuu khong duoc doi PROD (rank_mode='score').
Run: python -m unittest tests/test_rank_r38.py -v"""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import engine2 as E


def rows():
    # phien 21/10/2026 (rut gon): ORS 59,3 · DIG 58,8 · VSC 48,9
    return [dict(sym='VSC', sc=48.9, base=0.071, oi=1.42, volr=2.86, rs=60., mom=.05, pct=.0672, fund=30., liq=300e9, sector='VT', _day='2026-10-21'),
            dict(sym='DIG', sc=58.8, base=0.136, oi=2.00, volr=2.88, rs=70., mom=.02, pct=.0647, fund=40., liq=150e9, sector='BDS', _day='2026-10-21'),
            dict(sym='ORS', sc=59.3, base=0.054, oi=1.68, volr=5.33, rs=65., mom=.08, pct=.0693, fund=30., liq=60e9, sector='CK', _day='2026-10-21')]


class Rank(unittest.TestCase):
    def test_prod_van_la_score(self):
        from produce2 import PROD
        self.assertEqual(PROD.get('rank_mode', E.CFG.get('rank_mode')), 'score')
        self.assertEqual([r['sym'] for r in E.rank_rows(rows(), 'score')], ['ORS', 'DIG', 'VSC'])

    def test_tieu_chi_moi(self):
        self.assertEqual(E.rank_rows(rows(), 'volr')[0]['sym'], 'ORS')
        self.assertEqual(E.rank_rows(rows(), 'rs')[0]['sym'], 'DIG')
        self.assertEqual(E.rank_rows(rows(), 'liq')[0]['sym'], 'VSC')
        self.assertEqual(E.rank_rows(rows(), 'rev_score')[0]['sym'], 'VSC')
        self.assertEqual(E.rank_rows(rows(), 'base')[0]['sym'], 'ORS')

    def test_ngau_nhien_lap_lai_duoc(self):
        E._RANK_SEED[0] = 3
        a = [r['sym'] for r in E.rank_rows(rows(), 'random')]
        b = [r['sym'] for r in E.rank_rows(rows(), 'random')]
        self.assertEqual(a, b)
        E._RANK_SEED[0] = 0

    def test_oi_khong_nam_trong_quan_sat_duoc(self):
        for m in E.OBSERVABLE_AT_ATC:
            self.assertNotIn('oi', m.split('_'))


if __name__ == '__main__':
    unittest.main()
