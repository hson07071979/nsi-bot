# -*- coding: utf-8 -*-
"""VU TRU 'VN300' TINH THEO THOI DIEM (point-in-time).

Tai sao KHONG lay danh sach VN30/VN100 cua HOM NAY roi ap nguoc lai 2019:
  do la NHIN TRUOC (survivorship bias). Mot ma lot vao VN30 nam 2025 thi
  nam 2019 no chua chac da thanh khoan. Backtest se dep gia.

Cach dung o day: TAI MOI PHIEN, xep hang toan bo ma theo GTGD binh quan 20 phien
va chi giu TOP N. Danh sach tu dong doi theo thoi gian, dung nhu cach mot bo chi so
duoc co cau lai — va khong he dung thong tin tuong lai.
"""
import numpy as np

def build_topn(I, n=300):
    """Tra ve ma tran bool (ngay x ma): True neu ma nam trong TOP n GTGD binh quan 20 phien."""
    TV = I['tvma20']                      # GTGD binh quan 20 phien
    D, K = TV.shape
    out = np.zeros((D, K), dtype=bool)
    x = np.where(np.isnan(TV), -1.0, TV)
    for i in range(D):
        row = x[i]
        live = row > 0
        k = int(live.sum())
        if k == 0: continue
        m = min(n, k)
        # nguong = gia tri lon thu m
        thr = np.partition(row, -m)[-m]
        out[i] = live & (row >= thr)
    return out
