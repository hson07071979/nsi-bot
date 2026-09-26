# -*- coding: utf-8 -*-
"""CHUÔNG BÁO SỚM TRONG PHIÊN — Nguyễn Sơn Invest  (v2, đã sửa lỗi tick cụt)

Vì sao phải có: hệ chỉ ăn tiền nếu KHỚP ĐƯỢC TRONG CHÍNH PHIÊN bắn tín hiệu
(mua sang phiên sau làm Profit Factor rơi 2,62 -> 1,65). Chuông phải báo TỪ GIỮA PHIÊN.

SỬA LỖI QUAN TRỌNG (phát hiện ngày 19/08/2026):
  Endpoint `Markets/IntradayQuotes` của FireAnt trả tick BỊ CẮT CỤT, và cắt nặng nhất
  đúng ở những mã thanh khoản cao — tức đúng nhóm hệ thống muốn mua. Đo thực tế 19/08:
      TDM  0,4% khối lượng thật · POW 13,1% · HDB 11,9% · GMD 51% · FPT 41% · HPG 91%
  Quét bằng tick vì thế bỏ sót tín hiệu ở điều kiện volume và GTGD.
  => Bản này đọc thẳng DÒNG DỮ LIỆU NGÀY của FireAnt (đã là luỹ kế của phiên tính đến
     lúc cào, chính xác 100%), không dùng tick nữa. Nhanh hơn và đúng hơn.

Dự phóng khối lượng cuối phiên: dùng ĐỒNG HỒ (đường cong khối lượng luỹ kế điển hình
của phiên HOSE/HNX), không dùng khối lượng thị trường. Lý do: nếu lấy trung vị
(KL đã khớp / KL TB20) toàn thị trường làm thước đo tiến độ thì không phân biệt được
"phiên mới đi nửa chặng" với "hôm nay là phiên chợ chiều" — cuối phiên 19/08 nó đo ra
62% trong khi phiên đã đóng, làm mọi dự phóng bị thổi lên 1,6 lần.
Chỉ số đó vẫn được giữ lại nhưng đổi vai: `mkt_rel` = thanh khoản hôm nay so với bình thường.
"""
import json, datetime as dt
import numpy as np
import engine2 as E
from engine import risk_gate, canslim_score, as_of
from regime2 import build_regime

LEVELS = ['MUA', 'SAP_DU', 'THEO_DOI', 'CHAN']
ICON = {'MUA': '🔴', 'SAP_DU': '🟠', 'THEO_DOI': '🟡', 'CHAN': '⚠️'}
NAME = {'MUA': 'ĐỦ ĐIỀU KIỆN NGAY BÂY GIỜ — đặt lệnh trước ATC',
        'SAP_DU': 'SẮP ĐỦ — dự phóng sẽ đạt lúc đóng cửa, theo sát',
        'THEO_DOI': 'THEO DÕI — đang động đậy nhưng còn thiếu nhiều',
        'CHAN': 'CHẶN — bắt trần nhưng cổng rủi ro phủ quyết'}

from vithe import phan_bo, tom_tat_danh_muc
from produce2 import PROD as _PROD

# Cac tham so CO VI THE lay THANG tu PROD cua produce2 — mot nguon su that duy
# nhat. Truoc day chung duoc go lai bang tay o day va THIEU max_pos/max_total/
# max_pos_n, nen chuong bao tinh co vi the bang cau hinh mac dinh (max_pos 20%)
# trong khi bo may that chay 50%. Dung bao gio go lai bang tay nua.
# `top_n` phai lay tu PROD, khong duoc go tay — xem ghi chu o dong build_topn ben duoi.
_CO = {k: _PROD[k] for k in ('base_size', 'max_pos', 'max_total', 'max_pos_n', 'size_map', 'top_n')}

# LECH CU DA SUA 21/09/2026: dong nay tung de base_range=0.20 trong khi bo may
# chay 0.18 — lop chuong NOI HON lop backtest, dung cai bay so kien truc ghi ba
# lan. Nay ca hai deu 0.22. Doi mot ben thi phai doi ben kia, khong co ngoai le.
# 25/09/2026: doc THANG tu PROD — khong con go tay mot con so nao o day.
_PM = dict(E.CFG); _PM.update(_PROD)
CFG_LIVE = dict({k: _PM[k] for k in ('base_range', 'use_ordimb', 'ordimb_min', 'score_floor',
                                       'vol_floor', 'gtgd_min', 'volat_min', 'dk5_lo', 'dk5_hi')},
                **_CO)


# Đường cong khối lượng luỹ kế điển hình của một phiên HOSE/HNX (giờ Việt Nam).
# 9h15 ATO · 9h15–11h30 khớp liên tục · nghỉ trưa · 13h00–14h30 · 14h30–14h45 ATC.
VOL_CURVE = [(9.25, 0.02), (9.50, 0.10), (10.00, 0.24), (10.50, 0.34), (11.00, 0.44),
             (11.50, 0.55), (13.00, 0.55), (13.50, 0.67), (14.00, 0.79), (14.25, 0.86),
             (14.50, 0.92), (14.75, 1.00)]


def _danh_muc():
    """Doc so lenh may chu (data/portfolio.json) de biet con bao nhieu cho trong.

    Workflow tai file nay ve o buoc "Lay so lenh va so tay tu trang web".
    Khong co file thi coi nhu danh muc rong — van dung cho ngay dau, va phan
    giai thich se ghi ro la dang gia dinh.
    """
    for p in ('data/portfolio.json', 'portfolio.json'):
        try:
            P = json.load(open(p, encoding='utf-8'))
            return P.get('open') or [], float(P.get('nav') or 0)
        except Exception:
            continue
    return None, None


def gio_vn():
    """Giờ Việt Nam, KHÔNG phụ thuộc múi giờ của máy đang chạy.

    Máy chủ GitHub Actions chạy theo UTC. Nếu dùng dt.datetime.now() thẳng thì
    lúc 19h30 Việt Nam nó đọc ra 12h30 — tưởng phiên mới đi được nửa chặng nên
    thổi phồng dự phóng khối lượng lên khoảng 1,7 lần. Đúng loại lỗi đã từng
    gặp và đã sửa một lần rồi, đừng để tái diễn.
    """
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).replace(tzinfo=None)
    except Exception:
        return dt.datetime.utcnow() + dt.timedelta(hours=7)


def clock_frac(now=None):
    """Phiên đã đi được bao nhiêu phần khối lượng, tính theo đồng hồ (giờ VN)."""
    now = now or gio_vn()
    if now.weekday() >= 5:
        return 1.0
    t = now.hour + now.minute / 60.0
    if t <= VOL_CURVE[0][0]:
        return 0.02
    if t >= VOL_CURVE[-1][0]:
        return 1.0
    for k in range(1, len(VOL_CURVE)):
        t0, f0 = VOL_CURVE[k - 1]
        t1, f1 = VOL_CURVE[k]
        if t <= t1:
            return f0 + (f1 - f0) * (t - t0) / max(t1 - t0, 1e-9)
    return 1.0


def build(cfg=None):
    C = dict(E.CFG); C.update(CFG_LIVE); C.update(cfg or {})
    d, I, tls, sect = E.load()
    S = [str(x) for x in d['sym']]; cal = d['cal']
    i = len(cal) - 1          # dòng cuối = phiên hôm nay (luỹ kế tới lúc cào)
    p = max(i - 1, 0)         # dòng hôm qua — dùng cho mọi trung bình, để dữ liệu
                              # dở dang của hôm nay không làm loãng TB20
    AC = d['AdjClose']; MC = d['MarketCap']; TV = d['TotalValue']; V = d['Volume']
    PX = d['PriceClose']; B = d['PriceBasic']; PH = d['PriceHigh']; PLo = d['PriceLow']
    base_rng = (I['base_hi'] - I['base_lo']) / np.where(I['base_lo'] > 0, I['base_lo'], np.nan)
    R = build_regime(d, I, C)
    light = R['light'][i]; smul = C['size_map'][light]
    _mo, _nav = _danh_muc()
    _dm_n, _dm_tong, _dm_nganh, _dm_tien = tom_tat_danh_muc(_mo, _nav) \
        if (_mo is not None and _nav) else (0, 0.0, {}, 1.0)
    # VU TRU: phai DUNG BANG vu tru cua bo may, doc tu PROD.
    # LOI 21/09/2026: dong nay tung go cung `build_topn(I, 110)` trong khi bo may
    # da chuyen sang TOP 120. Chuong se quet hep hon bo may 10 ma — co ma bo may
    # vao lenh ma chuong khong bao giờ keu. Khong chot chan nao bat duoc loi nay
    # vi build van xanh; chi doc ky moi thay. Chu thich cu con ghi "TOP 100",
    # tuc da lech hai lan roi.
    from vn300 import build_topn
    TOPN = build_topn(I, int(C['top_n']))[i]
    try:
        wl = {m['sym'] for m in json.load(open('data/watchlist.json'))['members']}
    except Exception:
        wl = set()

    # anh Son co quyen phu quyet: ma trong loai.txt khong bao gio keu chuong
    from manual import loai as _loai
    LOAI = _loai()

    cand = [j for j, s in enumerate(S)
            if MC[i, j] > C['min_mktcap'] and I['nbars'][i, j] >= C['min_history']
            and I['tvma20'][p, j] >= 2e9 and TOPN[j] and str(s) not in LOAI]

    # --- phiên đã đi được bao nhiêu phần khối lượng?
    # Dùng ĐỒNG HỒ, không dùng khối lượng thị trường: nếu đo bằng khối lượng thì không
    # phân biệt được "phiên mới đi nửa chặng" với "hôm nay là phiên chợ chiều".
    frac = clock_frac()
    # đo thêm: hôm nay là phiên sôi động hay ảm đạm so với bình thường
    fr = []
    for j in cand:
        v20 = float(I['vma20'][p, j])
        if v20 > 0 and V[i, j] == V[i, j] and V[i, j] > 0:
            fr.append(float(V[i, j]) / v20)
    mkt_rel = (float(np.median(fr)) / frac) if (len(fr) >= 10 and frac > 0) else None

    today = dt.date.fromisoformat(str(cal[i]))
    out = []
    for j in cand:
        s = S[j]
        basic = float(B[i, j]); price = float(PX[i, j])
        if not basic or basic <= 0 or price != price:
            continue
        hi, lo = float(PH[i, j]), float(PLo[i, j])
        vol, val = float(V[i, j]), float(TV[i, j])
        pct = price / basic - 1
        v20 = float(I['vma20'][p, j])
        volr = vol / v20 if v20 > 0 else 0.0
        volr_proj = volr / frac
        gtgd_proj = val / frac
        thr = float(I['thr'][j])
        br = float(base_rng[p, j]) if base_rng[p, j] == base_rng[p, j] else 9.9
        volat = float(I['volat20'][p, j]) if I['volat20'][p, j] == I['volat20'][p, j] else 0.0
        # dòng tiền lớn: trong phiên FireAnt CHƯA công bố BuyCount/SellCount -> NaN.
        # Khi thiếu thì BỎ QUA điều kiện (nếu coi là 0 thì không mã nào vào được),
        # nhưng vẫn hiện giá trị phiên trước để anh Sơn có ngữ cảnh.
        oi = float(I['ordimb'][i, j]) if I['ordimb'][i, j] == I['ordimb'][i, j] else None
        oi_prev = float(I['ordimb'][p, j]) if I['ordimb'][p, j] == I['ordimb'][p, j] else None

        static = {
            'Nền 30 phiên ≤ %d%%' % int(C['base_range'] * 100): br <= C['base_range'],
            'Biến động TB20 ≥ 1,5%': volat >= C['volat_min'],
        }
        live_now = {
            'Biên độ tăng giá ≥ %.1f%%' % (thr * 100): pct >= thr,
            'Volume ≥ 2× TB20': volr >= C['vol_floor'],
            'GTGD ≥ 15 tỷ': val >= C['gtgd_min'],
            'Đóng cửa nửa trên nến': price >= (hi + lo) / 2,
        }
        live_proj = dict(live_now)
        live_proj['Volume ≥ 2× TB20'] = volr_proj >= C['vol_floor']
        live_proj['GTGD ≥ 15 tỷ'] = gtgd_proj >= C['gtgd_min']

        tl = tls.get(s); f = as_of(tl, today) if tl else None
        if f is None:
            blk, why, rmul = True, 'Chưa có BCTC', 0.0
        else:
            blk, why, rmul = risk_gate(s, f)
        sc, pts = 0.0, {}
        if f is not None:
            sc, pts = canslim_score(f, I['rs'][p, j], I['mom3'][p, j],
                                    float(AC[i, j] / I['hi52'][p, j] - 1) if I['hi52'][p, j] > 0 else None,
                                    volr_proj, float(I['tvma20'][p, j]))
        # điều kiện 5 của hệ: LNST YoY không nằm trong vùng yếu 0–25%
        npg = f.get('npat_yoy') if f else None
        weak = bool(npg is not None and C.get('dk5_lo', 0.0) <= npg < C.get('dk5_hi', 0.25))
        flow_ok = True if (not C['use_ordimb'] or oi is None) else (oi >= C['ordimb_min'])

        miss = [k for k, v in {**static, **live_now}.items() if not v]
        if weak:
            miss.append('LNST YoY %.1f%% — vùng yếu (0%% ≤ x < 25%%)' % (npg * 100))
        if not flow_ok:
            miss.append('Dòng tiền %.2f < %.2f' % (oi, C['ordimb_min']))
        if sc < C['score_floor']:
            miss.append('Điểm CANSLIM %.1f < %d' % (sc, C['score_floor']))

        ok_now = not miss and not blk
        ok_proj = (not blk and not weak and flow_ok and sc >= C['score_floor']
                   and all(static.values()) and all(live_proj.values()))

        need = []
        if not live_now['Volume ≥ 2× TB20'] and v20 > 0:
            need.append('cần thêm %s cp' % f"{int(max(0, C['vol_floor'] * v20 - vol)):,}".replace(',', '.'))
        if not live_now['GTGD ≥ 15 tỷ']:
            need.append('cần thêm %.1f tỷ GTGD' % ((C['gtgd_min'] - val) / 1e9))
        k_price = 'Biên độ tăng giá ≥ %.1f%%' % (thr * 100)
        if not live_now[k_price]:
            need.append('cần giá ≥ %.2f (nay %.2f)' % (basic * (1 + thr) / 1000, price / 1000))

        # Neu lenh nay duoc vao thi vao bao nhieu % NAV — va vi sao.
        vt = phan_bo(light, rmul=rmul, base_rng=br, cfg=C,
                     so_ma_dang_cam=_dm_n, tong_dang_cam=_dm_tong,
                     nganh_dang_cam=_dm_nganh.get(sect.get(s, 'Khác'), 0.0),
                     tien_mat=_dm_tien)

        rec = dict(sym=s, sector=sect.get(s, 'Khác'), price=round(price / 1000, 2),
                   pct=round(pct * 100, 2), volr=round(volr, 2), volr_proj=round(volr_proj, 2),
                   gtgd=round(val / 1e9, 1), gtgd_proj=round(gtgd_proj / 1e9, 1),
                   base=round(br * 100, 1), score=round(float(sc), 1),
                   ordimb=(round(oi, 2) if oi is not None else None),
                   ordimb_prev=(round(oi_prev, 2) if oi_prev is not None else None),
                   npat_yoy=(round(npg * 100, 1) if npg is not None else None), weak_growth=weak,
                   static=static, live=live_now, proj=live_proj,
                   cond={**live_now, **static},
                   blocked=bool(blk), block=why if blk else '', watchlist=s in wl,
                   missing=miss, need=need,
                   locked=bool(pct >= thr and volr < 0.6),
                   size_pct=vt['pct'], size_tran=vt['tran'],
                   size_1dong=vt['mot_dong'], size_vi_sao=vt['vi_sao'],
                   size_thuc=vt['pct_thuc'], size_vao_duoc=vt['vao_duoc'])
        if live_now[k_price] and blk:
            rec['level'] = 'CHAN'
        elif ok_now:
            rec['level'] = 'MUA'
        elif ok_proj:
            rec['level'] = 'SAP_DU'
        elif (s in wl or pct >= 0.03) and len(miss) <= 2 and not blk:
            rec['level'] = 'THEO_DOI'
        else:
            continue
        out.append(rec)

    out.sort(key=lambda a: (LEVELS.index(a['level']), -a['score']))
    res = dict(asof=gio_vn().isoformat(timespec='seconds'), session=str(cal[i]),
               light=light, size_mul=smul, scanned=len(cand), universe=len(cand),
               session_frac=round(frac, 3), frac_n=len(fr), src='daily-row', alerts=out,
               mkt_rel=(round(mkt_rel, 2) if mkt_rel else None),
               counts={k: sum(1 for a in out if a['level'] == k) for k in LEVELS})

    def cv(o):
        if isinstance(o, dict): return {k: cv(v) for k, v in o.items()}
        if isinstance(o, list): return [cv(x) for x in o]
        if isinstance(o, (np.floating, np.integer)): return float(o)
        if isinstance(o, np.bool_): return bool(o)
        return o
    json.dump(cv(res), open('data/alerts_live.json', 'w'), ensure_ascii=False)
    return res


if __name__ == '__main__':
    r = build()
    print(f"CHUÔNG SỚM {r['asof']} | phiên {r['session']} | đèn {r['light']} (size ×{r['size_mul']})")
    mr = r.get('mkt_rel')
    print(f"Quét {r['scanned']} mã từ dòng dữ liệu ngày · phiên đã đi ~{r['session_frac']*100:.0f}% (theo đồng hồ)"
          + (f" · thanh khoản hôm nay ~{mr:.2f}× phiên bình thường" if mr else ""))
    print('Tổng:', ', '.join(f"{ICON[k]} {k} {v}" for k, v in r['counts'].items() if v) or 'không có gì')
    for lv in LEVELS:
        rows = [a for a in r['alerts'] if a['level'] == lv]
        if not rows:
            continue
        print(f"\n{ICON[lv]} {NAME[lv]}")
        for a in rows[:12]:
            if a['level'] == 'SAP_DU':
                tail = ' | ' + '; '.join(a['need'][:2])
            elif a['level'] == 'CHAN':
                tail = ' | ' + a['block']
            else:
                tail = ' | thiếu: ' + ', '.join(a['missing'][:2]) if a['missing'] else ''
            lk = ' [TRẦN CỨNG - khó khớp]' if a['locked'] else ''
            print(f"  {a['sym']:5s} {a['pct']:+6.2f}%  vol {a['volr']:.2f}× (dự phóng {a['volr_proj']:.2f}×)  "
                  f"GTGD {a['gtgd']:.0f}→{a['gtgd_proj']:.0f} tỷ  điểm {a['score']:.0f}{lk}{tail}")
