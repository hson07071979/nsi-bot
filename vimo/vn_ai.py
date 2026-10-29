# -*- coding: utf-8 -*-
"""VĨ MÔ VIỆT NAM TỰ ĐỘNG — Gemini rẻ nhất + Google Search (29/10/2026).

Các biến vĩ mô Việt Nam (lãi huy động, tín dụng, CPI, đầu tư công, FDI, GDP…) không có API công khai ổn định, trước đây
Claude cập nhật tay vào port/ho_so/vi_mo_vn.json. File này thay việc tay đó: mỗi sáng sau vimo/cao.py, hỏi MỘT lần model
Gemini rẻ nhất mà key dùng được (ưu tiên flash-lite) có bật Google Search, lấy số mới nhất kèm kỳ, ngày công bố, nguồn.

Chống bịa:
  · bắt buộc có groundingMetadata (model thật sự đã tìm trên web) — không có thì bỏ cả lượt, giữ số cũ;
  · mỗi biến phải có giá trị số trong khoảng hợp lý, ngày công bố không ở tương lai và không cũ quá HAN_CU ngày, có nguồn;
  · xu hướng do code tính khi có số kỳ trước (so giá trị, ngưỡng theo biến); chỉ dùng xu hướng model nói khi chưa có lịch sử;
  · biến hỏng giữ nguyên bản cũ (ghi `loi`), không bao giờ xoá số tốt bằng số hỏng.

Ghi <state>/vn_ai.json (ảnh chụp) và <state>/chuoi/vn_<bien>.csv (lịch sử theo kỳ). Hồ sơ doanh nghiệp (port/ho_so.py)
lấy bản tự động khi nó mới hơn hoặc bằng bản tay trong vi_mo_vn.json.

Dùng:  GEMINI_API_KEY=… python vimo/vn_ai.py <thư mục state> [--ngay YYYY-MM-DD]
Không có key → in thông báo, thoát 0 (không làm đỏ workflow cào vĩ mô).
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

API = 'https://generativelanguage.googleapis.com/v1beta'
VN = timezone(timedelta(hours=7))
HAN_CU = 120                 # ngày: số công bố cũ hơn thế coi như model lấy nhầm bài cũ

# khoá: tên, định nghĩa ĐÚNG một con số, đơn vị, khoảng hợp lý, ngưỡng đổi xu hướng (cùng đơn vị)
BIEN = {
    'ls_huy_dong_vn': dict(ten='Lãi suất huy động VN (12 tháng)', dv='%/năm', lo=2, hi=12, nguong=0.1,
                           dinh_nghia='lãi suất tiết kiệm kỳ hạn 12 tháng phổ biến tại nhóm ngân hàng thương mại lớn (bình quân hoặc mức niêm yết điển hình)'),
    'ls_cho_vay_vn': dict(ten='Lãi suất cho vay VN', dv='%/năm', lo=4, hi=16, nguong=0.1,
                          dinh_nghia='lãi suất cho vay bình quân của ngân hàng thương mại (NHNN hoặc báo chí trích NHNN)'),
    'ls_lien_nh_vn': dict(ten='Lãi suất liên ngân hàng qua đêm VN', dv='%/năm', lo=0, hi=15, nguong=0.3,
                          dinh_nghia='lãi suất bình quân liên ngân hàng kỳ hạn qua đêm VND, phiên gần nhất'),
    'tin_dung_vn': dict(ten='Tăng trưởng tín dụng VN', dv='% từ đầu năm', lo=-5, hi=25, nguong=0.3,
                        dinh_nghia='tăng trưởng tín dụng toàn nền kinh tế so với cuối năm trước, mốc gần nhất NHNN công bố'),
    'dau_tu_cong_vn': dict(ten='Giải ngân đầu tư công VN', dv='% kế hoạch năm', lo=0, hi=110, nguong=1.0,
                           dinh_nghia='tỷ lệ giải ngân vốn đầu tư công lũy kế từ đầu năm so với kế hoạch Thủ tướng giao'),
    'cpi_vn': dict(ten='Lạm phát VN (CPI)', dv='% so cùng kỳ', lo=-3, hi=15, nguong=0.15,
                   dinh_nghia='CPI tháng gần nhất so với cùng kỳ năm trước (Cục Thống kê)'),
    'tieu_dung_vn': dict(ten='Bán lẻ hàng hoá VN', dv='% so cùng kỳ', lo=-20, hi=40, nguong=0.5,
                         dinh_nghia='tổng mức bán lẻ hàng hoá và doanh thu dịch vụ tiêu dùng lũy kế từ đầu năm so cùng kỳ (Cục Thống kê)'),
    'xuat_khau_vn': dict(ten='Xuất khẩu VN', dv='% so cùng kỳ', lo=-30, hi=60, nguong=1.0,
                         dinh_nghia='kim ngạch xuất khẩu hàng hoá lũy kế từ đầu năm so cùng kỳ (Cục Thống kê)'),
    'pmi_vn': dict(ten='PMI sản xuất VN', dv='điểm', lo=30, hi=70, nguong=0.5,
                   dinh_nghia='chỉ số PMI ngành sản xuất Việt Nam của S&P Global, tháng gần nhất'),
    'fdi_vn': dict(ten='Vốn FDI vào VN', dv='tỷ USD giải ngân từ đầu năm', lo=0, hi=40, nguong=0.0,
                   dinh_nghia='vốn FDI thực hiện (giải ngân) lũy kế từ đầu năm, tỷ USD (Cục Đầu tư nước ngoài / Cục Thống kê)',
                   xu='yoy'),
    'gdp_vn': dict(ten='Tăng trưởng GDP VN', dv='% so cùng kỳ', lo=-10, hi=15, nguong=0.2,
                   dinh_nghia='tăng trưởng GDP quý gần nhất so cùng kỳ (Cục Thống kê)'),
    'tpcp_10y_vn': dict(ten='Lợi suất trái phiếu Chính phủ VN 10 năm', dv='%/năm', lo=0.5, hi=10, nguong=0.1,
                        dinh_nghia='lợi suất trái phiếu Chính phủ Việt Nam kỳ hạn 10 năm, phiên/tuần gần nhất'),
    'von_ngoai_vn': dict(ten='Dòng vốn ngoại vào chứng khoán VN', dv='nghìn tỷ đồng (+ mua ròng, − bán ròng)', lo=-150, hi=150,
                         nguong=0.0, dinh_nghia='giá trị mua(+)/bán(−) ròng của khối ngoại trên toàn thị trường chứng khoán VN '
                                                'lũy kế từ đầu tháng hiện tại', xu='dau'),
}

HE_THONG = ('Bạn là chuyên viên số liệu vĩ mô Việt Nam. BẮT BUỘC dùng Google Search để tìm số mới nhất, ưu tiên nguồn chính thức '
            '(Cục Thống kê nso.gov.vn, NHNN sbv.gov.vn, Bộ Tài chính, S&P Global) hoặc báo lớn trích nguồn chính thức (VnEconomy, '
            'CafeF, Vietstock, Báo Chính phủ, Thời báo Tài chính). Không ước đoán, không lấy số dự báo thay cho số đã công bố. '
            'Không tìm được thì để gia_tri null. Chỉ trả về MỘT khối JSON, không giải thích ngoài JSON.')


def chon_model(ten: list[str]) -> list[str]:
    """Rẻ nhất trước: flash-lite (bản số lớn, chính thức trước preview) → flash. Bỏ model ảnh, âm thanh, live, embedding."""
    bo = ('image', 'tts', 'audio', 'live', 'embedding', 'exp', 'thinking')
    rx = re.compile(r'^gemini-(\d+(?:\.\d+)?)-flash(-lite)?(?:-preview(?:-[\w-]+)?)?(?:-\d{2,})?$')
    ok = []
    for n in ten:
        m = rx.match(n)
        if not m or any(b in n for b in bo):
            continue
        ok.append(((0 if m.group(2) else 1, -float(m.group(1)), 'preview' in n, len(n)), n))
    return [n for _, n in sorted(ok)]


def _models(key: str) -> list[str]:
    env = os.environ.get('GEMINI_MODELS_VIMO')
    if env:
        return [x.strip() for x in env.split(',') if x.strip()]
    try:
        r = requests.get(f'{API}/models', params={'key': key, 'pageSize': 1000}, timeout=20)
        have = [m['name'].split('/')[-1] for m in r.json().get('models', [])
                if 'generateContent' in m.get('supportedGenerationMethods', [])]
    except Exception:  # noqa: BLE001
        have = []
    return chon_model(have)[:4] or ['gemini-2.5-flash-lite', 'gemini-2.5-flash']


def _json_long(text: str):
    text = (text or '').strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'\{.*\}', text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def hoi(key: str, prompt: str, post=None) -> tuple[dict | None, dict]:
    """Gọi Gemini có Google Search. → (json, meta: model, so_tim_kiem, loi{model: lý do})."""
    post = post or requests.post
    meta = dict(model=None, so_tim_kiem=0, nguon_web=[], loi={})
    for model in _models(key):
        body = dict(systemInstruction=dict(parts=[dict(text=HE_THONG)]),
                    contents=[dict(role='user', parts=[dict(text=prompt)])],
                    tools=[dict(google_search={})],
                    generationConfig=dict(temperature=0.1, maxOutputTokens=8192))
        for lan in range(3):
            try:
                r = post(f'{API}/models/{model}:generateContent', params={'key': key}, json=body, timeout=240)
            except requests.RequestException as e:
                meta['loi'][model] = f'mạng: {str(e)[:100]}'
                time.sleep(5 * (lan + 1))
                continue
            if r.status_code in (429, 500, 503):
                meta['loi'][model] = f'HTTP {r.status_code}'
                time.sleep(15 * (lan + 1))
                continue
            if r.status_code != 200:
                meta['loi'][model] = f'HTTP {r.status_code}: {r.text[:150]}'
                break
            j = r.json()
            try:
                cand = j['candidates'][0]
                text = ''.join(p.get('text', '') for p in cand['content']['parts'])
            except (KeyError, IndexError, TypeError):
                meta['loi'][model] = 'trả rỗng'
                break
            gm = cand.get('groundingMetadata') or {}
            q = gm.get('webSearchQueries') or []
            web = [(c.get('web') or {}).get('title') for c in gm.get('groundingChunks') or []]
            if not q and not web:
                meta['loi'][model] = 'không tìm trên web (không có groundingMetadata) — bỏ để chống bịa'
                break
            out = _json_long(text)
            if not isinstance(out, dict):
                meta['loi'][model] = 'JSON hỏng'
                break
            meta.update(model=model, so_tim_kiem=len(q), nguon_web=[w for w in web if w][:30])
            return out, meta
    return None, meta


def lap_prompt(ngay: str, cu: dict) -> str:
    dong = []
    for k, b in BIEN.items():
        c = cu.get(k) or {}
        truoc = f" (số đã có: {c.get('gia_tri')} kỳ {c.get('ky')})" if c.get('gia_tri') is not None else ''
        dong.append(f'- {k}: {b["dinh_nghia"]}; đơn vị {b["dv"]}{truoc}')
    return (f'Hôm nay là {ngay}. Tìm con số MỚI NHẤT đã công bố (trước hôm nay) cho từng biến vĩ mô Việt Nam sau:\n' + '\n'.join(dong) +
            '\n\nTrả JSON đúng dạng: {"bien": {"<khoá>": {"gia_tri": số hoặc null, "ky": "kỳ số liệu, vd 09/2026, Q3/2026, 24/10/2026", '
            '"ngay_cong_bo": "YYYY-MM-DD", "xu_huong": "tang"|"giam"|"ngang" (so với kỳ trước), '
            '"ly_do": "1–2 câu tiếng Việt có số cụ thể và so sánh kỳ trước", "nguon": "tên báo/cơ quan + ngày"}}}. '
            'Đủ mọi khoá ở trên; giá trị là số thuần (không ký hiệu %).')


def _so(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace(',', '.').replace('%', '').strip())
    except (TypeError, ValueError):
        return None


def kiem(k: str, r: dict | None, ngay: str, truoc: dict | None) -> tuple[dict | None, str | None]:
    """Kiểm một biến model trả. → (bản ghi sạch, None) hoặc (None, lý do loại)."""
    b = BIEN[k]
    if not isinstance(r, dict):
        return None, 'thiếu'
    v = _so(r.get('gia_tri'))
    if v is None:
        return None, 'không có số'
    if not b['lo'] <= v <= b['hi']:
        return None, f'{v} ngoài khoảng hợp lý {b["lo"]}–{b["hi"]}'
    try:
        d = date.fromisoformat(str(r.get('ngay_cong_bo'))[:10])
    except ValueError:
        return None, 'ngày công bố hỏng'
    h = date.fromisoformat(ngay)
    if d > h:
        return None, f'ngày công bố {d} ở tương lai'
    if (h - d).days > HAN_CU:
        return None, f'số cũ ({d})'
    nguon = str(r.get('nguon') or '').strip()
    if len(nguon) < 3:
        return None, 'không có nguồn'
    ky = str(r.get('ky') or '').strip() or d.isoformat()
    xu = r.get('xu_huong') if r.get('xu_huong') in ('tang', 'giam', 'ngang') else 'ngang'
    xu_tu = 'model'
    t = truoc or {}
    if t.get('gia_tri') is not None and t.get('ky') and t.get('ky') != ky and b.get('xu') is None:
        dv = v - float(t['gia_tri'])
        xu = 'tang' if dv > b['nguong'] else 'giam' if dv < -b['nguong'] else 'ngang'
        xu_tu = 'code (so kỳ trước)'
    elif b.get('xu') == 'dau':                          # dòng vốn: dấu của chính con số
        xu = 'tang' if v > 0 else 'giam' if v < 0 else 'ngang'
        xu_tu = 'code (dấu)'
    return dict(ten=b['ten'], dv=b['dv'], gia_tri=round(v, 3), ky=ky, ngay=d.isoformat(), xu_huong=xu, xu_huong_tu=xu_tu,
                ly_do=str(r.get('ly_do') or '')[:400], nguon=nguon[:200]), None


def gop(cu: dict, moi: dict | None, ngay: str) -> tuple[dict, dict]:
    """Gộp kết quả model vào bản cũ, biến hỏng giữ bản cũ. → (bien, loai{k: lý do})."""
    bien, loai = {}, {}
    mb = (moi or {}).get('bien') if isinstance(moi, dict) else None
    for k in BIEN:
        rec, ly = kiem(k, (mb or {}).get(k), ngay, cu.get(k)) if mb is not None else (None, 'lượt hỏng')
        if rec:
            c = cu.get(k) or {}
            if c.get('ky') == rec['ky'] and c.get('gia_tri') == rec['gia_tri']:
                rec['xu_huong'], rec['xu_huong_tu'] = c.get('xu_huong', rec['xu_huong']), c.get('xu_huong_tu', rec['xu_huong_tu'])
            bien[k] = rec
        else:
            loai[k] = ly
            if cu.get(k):
                bien[k] = dict(cu[k], loi=f'{ngay}: {ly} — giữ số cũ')
    return bien, loai


def ghi(state: Path, ngay: str, bien: dict, loai: dict, meta: dict) -> None:
    state.mkdir(parents=True, exist_ok=True)
    (state / 'vn_ai.json').write_text(json.dumps(dict(
        ngay=ngay, luc=datetime.now(VN).isoformat(timespec='minutes'), model=meta.get('model'), so_tim_kiem=meta.get('so_tim_kiem'),
        nguon_web=meta.get('nguon_web'), loi_model=meta.get('loi'), loai=loai, bien=bien), ensure_ascii=False, indent=1), encoding='utf-8')
    (state / 'chuoi').mkdir(exist_ok=True)
    for k, r in bien.items():
        if r.get('loi'):
            continue
        p = state / 'chuoi' / f'vn_{k}.csv'
        dong = []
        if p.exists():
            with p.open(encoding='utf-8') as f:
                dong = [x for x in csv.DictReader(f) if x.get('ky') != r['ky']]
        dong.append(dict(ky=r['ky'], ngay=r['ngay'], gia_tri=r['gia_tri'], nguon=r['nguon']))
        dong.sort(key=lambda x: x['ngay'])
        with p.open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['ky', 'ngay', 'gia_tri', 'nguon'])
            w.writeheader()
            w.writerows(dong)


def main(argv: list[str]) -> int:
    state = Path(argv[1] if len(argv) > 1 else 'port/state/vi_mo')
    ngay = argv[argv.index('--ngay') + 1] if '--ngay' in argv else datetime.now(VN).date().isoformat()
    key = os.environ.get('GEMINI_API_KEY', '')
    if not key:
        print('vĩ mô VN tự động: chưa có secret GEMINI_API_KEY trong repo nsi-bot — bỏ qua, hồ sơ dùng bản tay vi_mo_vn.json')
        return 0
    try:
        cu = (json.loads((state / 'vn_ai.json').read_text(encoding='utf-8')) or {}).get('bien') or {}
    except (OSError, json.JSONDecodeError):
        cu = {}
    out, meta = hoi(key, lap_prompt(ngay, cu))
    bien, loai = gop(cu, out, ngay)
    ghi(state, ngay, bien, loai, meta)
    print(f'vĩ mô VN {ngay}: model {meta.get("model")}, {meta.get("so_tim_kiem")} lượt tìm, '
          f'{len(BIEN) - len(loai)}/{len(BIEN)} biến mới')
    for k, r in bien.items():
        print(f'  {k:15s} {r["gia_tri"]:>8} {r["dv"]:<22s} kỳ {r["ky"]:<12s} {r["xu_huong"]:<5s} {r["nguon"][:60]}'
              + (f'  ⚠ {r["loi"]}' if r.get('loi') else ''))
    for k, ly in loai.items():
        print(f'  ✗ {k}: {ly}')
    for m, e in (meta.get('loi') or {}).items():
        print(f'  [model {m}] {e}')
    return 0                                      # không làm đỏ workflow: vĩ mô quốc tế vẫn phải được ghi


if __name__ == '__main__':
    sys.exit(main(sys.argv))
