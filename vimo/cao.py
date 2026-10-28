# -*- coding: utf-8 -*-
"""CÀO VĨ MÔ MỖI SÁNG — sổ điểm-thời-gian cho hồ sơ doanh nghiệp và vòng học (28/10/2026).

Chạy 7h05 giờ VN (workflow vi_mo.yml). Mỗi biến có nguồn chính + nguồn dự phòng; lấy được nguồn nào ghi nguồn đó.
Chỉ dùng số liệu có ngày TRƯỚC ngày chạy (phiên đã đóng) — không nhìn trước.

Ghi vào <state>/ (nhánh port-data: port/state/vi_mo/):
  so_vi_mo.csv      mỗi ngày một dòng: ngay + từng biến (giá trị, thay đổi, z). Dòng cũ không bao giờ sửa.
  moi_nhat.json     ảnh chụp hôm nay đầy đủ (nguồn, ngày số liệu, đối chiếu nguồn phụ, xu hướng).
  chuoi/<bien>.csv  lịch sử đầy đủ của từng biến từ nguồn (để vòng học đo độ nhạy của từng mã).

Xu hướng của một biến = thay đổi trong cửa sổ (20 phiên với biến ngày, 3 tháng với biến tháng) chia độ lệch chuẩn của
chính thay đổi đó trong lịch sử (z). |z| < 0,5 → đi ngang; z ≥ 0,5 → tăng; z ≤ −0,5 → giảm. Hồ sơ doanh nghiệp dùng
xu hướng này × chiều tác động để chấm thuận / nghịch / trung tính.

Dùng:  python vimo/cao.py <thư mục state> [--ngay YYYY-MM-DD]
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nguon as NG  # noqa: E402

NGUONG_Z = 0.5

# ten, don vi, kieu ('ngay' | 'thang'), cach do thay doi ('pct' | 'diem'), nguon theo thu tu uu tien
BIEN = {
    # ---- quốc tế: lãi suất, đô la, rủi ro
    'us10y': dict(ten='Lợi suất trái phiếu Mỹ 10 năm', dv='%', kieu='ngay', do='diem', nguon=[('fred', 'DGS10'), ('yahoo', '^TNX')]),
    'us2y': dict(ten='Lợi suất trái phiếu Mỹ 2 năm', dv='%', kieu='ngay', do='diem', nguon=[('fred', 'DGS2')]),
    'fed': dict(ten='Lãi suất qua đêm Fed (hiệu dụng)', dv='%', kieu='ngay', do='diem', nguon=[('fred', 'DFF')]),
    'dxy': dict(ten='Chỉ số đô la Mỹ (DXY)', dv='điểm', kieu='ngay', do='pct', nguon=[('yahoo', 'DX-Y.NYB'), ('stooq', 'dx.f')]),
    'usd_rong': dict(ten='Đô la Mỹ so với rổ rộng (Fed)', dv='điểm', kieu='ngay', do='pct', nguon=[('fred', 'DTWEXBGS')]),
    'usdvnd': dict(ten='Tỷ giá USD/VND', dv='đồng', kieu='ngay', do='pct', nguon=[('yahoo', 'VND=X'), ('stooq', 'usdvnd'), ('vcb', '')]),
    'usdcny': dict(ten='Tỷ giá USD/CNY', dv='nhân dân tệ', kieu='ngay', do='pct', nguon=[('fred', 'DEXCHUS'), ('yahoo', 'CNY=X')]),
    'vix': dict(ten='Chỉ số sợ hãi VIX', dv='điểm', kieu='ngay', do='diem', nguon=[('fred', 'VIXCLS'), ('yahoo', '^VIX')]),
    'spx': dict(ten='S&P 500', dv='điểm', kieu='ngay', do='pct', nguon=[('fred', 'SP500'), ('yahoo', '^GSPC')]),
    # ---- năng lượng, kim loại (ngày)
    'brent': dict(ten='Dầu Brent', dv='USD/thùng', kieu='ngay', do='pct', nguon=[('yahoo', 'BZ=F'), ('fred', 'DCOILBRENTEU')]),
    'wti': dict(ten='Dầu WTI', dv='USD/thùng', kieu='ngay', do='pct', nguon=[('yahoo', 'CL=F'), ('fred', 'DCOILWTICO')]),
    'khi_hh': dict(ten='Khí tự nhiên Henry Hub', dv='USD/MMBtu', kieu='ngay', do='pct', nguon=[('yahoo', 'NG=F'), ('fred', 'DHHNGSP')]),
    'vang': dict(ten='Vàng thế giới', dv='USD/oz', kieu='ngay', do='pct', nguon=[('yahoo', 'GC=F'), ('stooq', 'xauusd')]),
    'dong': dict(ten='Đồng (COMEX)', dv='USD/lb', kieu='ngay', do='pct', nguon=[('yahoo', 'HG=F')]),
    'hrc_my': dict(ten='Thép cuộn cán nóng HRC (Mỹ)', dv='USD/tấn', kieu='ngay', do='pct', nguon=[('yahoo', 'HRC=F')]),
    'quang_sat_ngay': dict(ten='Quặng sắt (SGX)', dv='USD/tấn', kieu='ngay', do='pct', nguon=[('yahoo', 'TIO=F')]),
    # ---- nông sản (ngày)
    'duong': dict(ten='Đường thô', dv='US cent/lb', kieu='ngay', do='pct', nguon=[('yahoo', 'SB=F')]),
    'bong': dict(ten='Bông', dv='US cent/lb', kieu='ngay', do='pct', nguon=[('yahoo', 'CT=F')]),
    'ngo': dict(ten='Ngô (CBOT)', dv='US cent/giạ', kieu='ngay', do='pct', nguon=[('yahoo', 'ZC=F')]),
    'kho_dau': dict(ten='Khô đậu tương (CBOT)', dv='USD/short ton', kieu='ngay', do='pct', nguon=[('yahoo', 'ZM=F')]),
    'sua_bot': dict(ten='Sữa bột gầy (CME)', dv='USD/lb', kieu='ngay', do='pct', nguon=[('yahoo', 'GNF=F')]),
    # ---- hàng hoá IMF (tháng, FRED) — chậm nhưng ổn định, dùng khi không có chuỗi ngày
    'quang_sat': dict(ten='Quặng sắt (IMF, tháng)', dv='USD/tấn', kieu='thang', do='pct', nguon=[('fred', 'PIORECRUSDM')]),
    'than_uc': dict(ten='Than Úc (IMF, tháng)', dv='USD/tấn', kieu='thang', do='pct', nguon=[('fred', 'PCOALAUUSDM')]),
    'lng_nhat': dict(ten='Khí LNG Nhật Bản (IMF, tháng)', dv='USD/MMBtu', kieu='thang', do='pct', nguon=[('fred', 'PNGASJPUSDM')]),
    'cao_su': dict(ten='Cao su (IMF, tháng)', dv='US cent/lb', kieu='thang', do='pct', nguon=[('fred', 'PRUBBUSDM')]),
    'nhom': dict(ten='Nhôm (IMF, tháng)', dv='USD/tấn', kieu='thang', do='pct', nguon=[('fred', 'PALUMUSDM')]),
    'gao': dict(ten='Gạo Thái (IMF, tháng)', dv='USD/tấn', kieu='thang', do='pct', nguon=[('fred', 'PRICENPQUSDM')]),
    'tom': dict(ten='Tôm (IMF, tháng)', dv='USD/kg', kieu='thang', do='pct', nguon=[('fred', 'PSHRIUSDM')]),
    'ca_phe': dict(ten='Cà phê Robusta (IMF, tháng)', dv='US cent/lb', kieu='thang', do='pct', nguon=[('fred', 'PCOFFROBUSDM')]),
    'dau_co': dict(ten='Dầu cọ (IMF, tháng)', dv='USD/tấn', kieu='thang', do='pct', nguon=[('fred', 'PPOILUSDM')]),
    'cpi_my': dict(ten='Lạm phát Mỹ (CPI, tháng)', dv='chỉ số', kieu='thang', do='pct', nguon=[('fred', 'CPIAUCSL')]),
}
CUA_SO = dict(ngay=20, thang=3)          # 20 phiên / 3 tháng
CU_QUA = dict(ngay=10, thang=75)         # số liệu cũ hơn ngần này ngày coi như nguồn chết (vd hợp đồng ngừng giao dịch)


def thay_doi(s: list[tuple[str, float]], n: int, do: str) -> float | None:
    if len(s) <= n:
        return None
    a, b = s[-1 - n][1], s[-1][1]
    if do == 'diem':
        return round(b - a, 4)
    return round((b / a - 1) * 100, 3) if a else None


def z_xu_huong(s: list[tuple[str, float]], n: int, do: str) -> tuple[float | None, str]:
    """z = thay đổi cửa sổ hiện tại ÷ độ lệch chuẩn các thay đổi cửa sổ không chồng nhau trong lịch sử."""
    c = thay_doi(s, n, do)
    if c is None:
        return None, 'thiếu'
    lich = []
    for i in range(len(s) - 1 - n, n - 1, -n):
        a, b = s[i - n][1], s[i][1]
        lich.append((b - a) if do == 'diem' else ((b / a - 1) * 100 if a else 0.0))
        if len(lich) >= 120:
            break
    if len(lich) < 8:
        return None, 'thiếu'
    sd = statistics.pstdev(lich)
    if sd <= 0:                                   # lịch sử không hề đổi: thay đổi nào cũng là bất thường
        return (0.0, 'ngang') if c == 0 else ((9.99, 'tang') if c > 0 else (-9.99, 'giam'))
    z = round(c / sd, 2)
    return z, ('tang' if z >= NGUONG_Z else 'giam' if z <= -NGUONG_Z else 'ngang')


def chup(ngay: str, lay=None) -> tuple[dict, dict]:
    """Ảnh chụp mọi biến tại sáng `ngay` (chỉ số liệu có ngày < ngay). → (anh, chuoi_da_dung)."""
    lay = lay or NG.NGUON
    anh, chuoi = {}, {}
    for k, b in BIEN.items():
        dung, phu = None, []
        for ten, sym in b['nguon']:
            s = [x for x in (lay[ten](sym) or []) if x[0] < ngay]
            if not s or (datetime.fromisoformat(ngay) - datetime.fromisoformat(s[-1][0])).days > CU_QUA[b['kieu']]:
                continue
            if dung is None:
                dung = (ten, sym, s)
            else:
                phu.append((ten, sym, s[-1]))
                break                                  # một nguồn phụ để đối chiếu là đủ
        if dung is None:
            anh[k] = dict(ten=b['ten'], dv=b['dv'], kieu=b['kieu'], gia_tri=None, loi='mọi nguồn đều hỏng')
            continue
        ten, sym, s = dung
        n = CUA_SO[b['kieu']]
        z, xh = z_xu_huong(s, n, b['do'])
        r = dict(ten=b['ten'], dv=b['dv'], kieu=b['kieu'], gia_tri=round(s[-1][1], 4), ngay_so=s[-1][0],
                 nguon=f'{ten}:{sym}' if sym else ten, thay_doi=thay_doi(s, n, b['do']), do=b['do'], cua_so=n, z=z, xu_huong=xh,
                 thay_doi_5=thay_doi(s, 5, b['do']) if b['kieu'] == 'ngay' else None)
        if phu:
            t2, s2, (d2, v2) = phu[0]
            r['doi_chieu'] = dict(nguon=f'{t2}:{s2}' if s2 else t2, ngay_so=d2, gia_tri=round(v2, 4),
                                  lech_pct=round((r['gia_tri'] / v2 - 1) * 100, 2) if v2 else None)
        anh[k] = r
        chuoi[k] = s
    return anh, chuoi


COT = ['ngay'] + [f'{k}{h}' for k in BIEN for h in ('', '_tdoi', '_z')]


def ghi(state: Path, ngay: str, anh: dict, chuoi: dict) -> None:
    state.mkdir(parents=True, exist_ok=True)
    p = state / 'so_vi_mo.csv'
    dong = []
    if p.exists():
        with p.open(encoding='utf-8') as f:
            dong = [r for r in csv.DictReader(f) if r.get('ngay') != ngay]
    moi = {'ngay': ngay}
    for k, r in anh.items():
        moi[k] = '' if r.get('gia_tri') is None else r['gia_tri']
        moi[f'{k}_tdoi'] = '' if r.get('thay_doi') is None else r['thay_doi']
        moi[f'{k}_z'] = '' if r.get('z') is None else r['z']
    dong.append(moi)
    dong.sort(key=lambda r: r['ngay'])
    with p.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COT, extrasaction='ignore')
        w.writeheader()
        w.writerows(dong)
    (state / 'chuoi').mkdir(exist_ok=True)
    for k, s in chuoi.items():
        with (state / 'chuoi' / f'{k}.csv').open('w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['ngay', 'gia_tri'])
            w.writerows(s)
    ok = sum(1 for r in anh.values() if r.get('gia_tri') is not None)
    lech = {k: r['doi_chieu'] for k, r in anh.items() if abs(((r.get('doi_chieu') or {}).get('lech_pct') or 0)) > 3}
    (state / 'moi_nhat.json').write_text(json.dumps(dict(
        ngay=ngay, luc=datetime.now(NG.VN).isoformat(timespec='minutes'), so_bien=len(anh), lay_duoc=ok,
        bien=anh, lech_nguon=lech, loi_nguon=NG.LOI[-40:]), ensure_ascii=False, indent=1), encoding='utf-8')


def main(argv: list[str]) -> int:
    state = Path(argv[1] if len(argv) > 1 else 'port/state/vi_mo')
    ngay = argv[argv.index('--ngay') + 1] if '--ngay' in argv else datetime.now(NG.VN).date().isoformat()
    anh, chuoi = chup(ngay)
    ghi(state, ngay, anh, chuoi)
    ok = [k for k, r in anh.items() if r.get('gia_tri') is not None]
    print(f'vĩ mô {ngay}: lấy được {len(ok)}/{len(anh)} biến')
    for k, r in anh.items():
        if r.get('gia_tri') is None:
            print(f'  ✗ {k}: {r.get("loi")}')
        else:
            dc = r.get('doi_chieu') or {}
            print(f'  {k:15s} {r["gia_tri"]:>12} ({r["ngay_so"]}, {r["nguon"]}) Δ{r["cua_so"]}={r["thay_doi"]} z={r["z"]} {r["xu_huong"]}'
                  + (f' | đối chiếu {dc["nguon"]} lệch {dc["lech_pct"]}%' if dc else ''))
    for e in NG.LOI:
        print('  [nguồn lỗi]', e)
    return 0 if len(ok) >= len(anh) // 2 else 1     # quá nửa biến hỏng thì báo đỏ để anh Sơn thấy


if __name__ == '__main__':
    sys.exit(main(sys.argv))
