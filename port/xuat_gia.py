# -*- coding: utf-8 -*-
"""Xuất bảng giá gọn cho Lọc port (chạy trong dây chuyền hằng ngày, ngay sau fa_prep.py).

Lọc port chạy ở workflow riêng nên không có data/fa.npz (hàng trăm MB). File này cắt ra phần port cần:
giá đóng cửa (thô, để khớp lệnh giả lập), khối lượng (vòng học pool) và giá điều chỉnh (để tính đặc trưng + chấm nhận định, không bị lệch vì
chia cổ tức/tách cổ phiếu) cho các mã đủ thanh khoản, từ 2019. Không tải thêm gì — chỉ đọc dữ liệu đã có.
"""
from __future__ import annotations

import os
import sys

import numpy as np

NGUON = 'data/fa.npz'
DICH = 'data/port_gia.npz'
TU = '2019-01-01'
GTGD_TOI_THIEU = 5e9          # trung bình 60 phiên gần nhất, đồng
LUON_CO = ('FPT', 'VCB', 'MWG', 'HPG', 'IDC', 'CTG', 'CTR', 'POW', 'KDH', 'TNG', 'SSI', 'MSN')


def main() -> int:
    if not os.path.exists(NGUON):
        print(f'không có {NGUON} → bỏ qua (port vẫn chạy bằng nến 240 phiên của trang web)')
        return 0
    z = np.load(NGUON, allow_pickle=True)
    cal = np.array([str(x) for x in z['cal']])
    sym = np.array([str(x) for x in z['sym']])
    keep_t = cal >= TU
    tv = z['TotalValue'][-60:]
    with np.errstate(invalid='ignore'):
        gtgd = np.nanmean(tv, axis=0)
    keep_s = (np.nan_to_num(gtgd) >= GTGD_TOI_THIEU) | np.isin(sym, LUON_CO)
    # khối lượng điều chỉnh theo chia tách/thưởng cổ phiếu: KL × giá thô ÷ giá điều chỉnh (cùng hệ số với giá)
    with np.errstate(invalid='ignore', divide='ignore'):
        vol_dc = z['Volume'] * (z['PriceClose'] / z['AdjClose'])
    out = dict(cal=cal[keep_t], sym=sym[keep_s],
               close=z['PriceClose'][keep_t][:, keep_s].astype(np.float32),
               adj=z['AdjClose'][keep_t][:, keep_s].astype(np.float32),
               vol=vol_dc[keep_t][:, keep_s].astype(np.float32))      # 24/10/2026: cho vòng học pool (siết vol)
    np.savez_compressed(DICH, **out)
    print(f"{DICH}: {len(out['sym'])} mã × {len(out['cal'])} phiên, {os.path.getsize(DICH) / 1e6:.1f} MB")
    return 0


if __name__ == '__main__':
    sys.exit(main())
