# -*- coding: utf-8 -*-
"""Đọc BCTC sâu cho Lọc port (anh Sơn 22/10/2026).

Không chỉ nhìn "lợi nhuận tăng hay giảm", mà trả lời: TĂNG/GIẢM VÌ KHOẢN NÀO, khoản đó là kinh doanh thật (lõi)
hay khoản một lần (dự phòng, tỷ giá, thu nhập khác, đánh giá lại chứng khoán…), và quý sau nó có thể quay lại không.

Nguồn: data/funda_raw2.json mà dây chuyền hằng ngày đã tải từ Vietcap IQ (không cào thêm). Mỗi mã có các quý
`is` (kết quả kinh doanh) và `cf` (lưu chuyển tiền tệ) theo mã dòng của Vietcap:
  doanh nghiệp thường  isa*  (+ cfa3 chi phí dự phòng, cfa4 chênh lệch tỷ giá đánh giá lại, cfa5 lãi/lỗ thanh lý TSCĐ)
  ngân hàng            isb*  (isb40 lợi nhuận trước dự phòng, isb41 trích lập dự phòng tín dụng)
  chứng khoán          iss*  (iss115/iss124 lãi/lỗ tài sản tài chính FVTPL, iss117/iss126 đánh giá lại chưa thực hiện)

Code chỉ tính số và viết câu theo khuôn. Câu chuyện dài cho khách do Claude viết lúc review quý, dựa trên đúng
các con số ở đây — không thêm số nào ngoài bảng này.
"""
from __future__ import annotations

TY = 1e9
SO_QUY = 12


def _n(r: dict, k: str) -> float:
    v = (r or {}).get(k)
    return float(v) / TY if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def _co(r: dict, k: str) -> bool:
    v = (r or {}).get(k)
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0


def nhan(y: int, q: int) -> str:
    return f'Q{q}/{str(y)[2:]}'


def loai_dn(rows: list[dict]) -> str:
    gan = rows[-4:]
    def co(*ks):
        return any(_co(r, k) for r in gan for k in ks)
    if co('isb27', 'isb40', 'isb41'):
        return 'ngan_hang'
    if co('iss115', 'iss42', 'iss120'):
        return 'chung_khoan'
    if co('isi103', 'isi105'):
        return 'bao_hiem'
    return 'thuong'


def _quy(raw: dict) -> list[tuple[tuple[int, int], dict, dict]]:
    """[(năm, quý), dòng KQKD, dòng LCTT] theo thứ tự thời gian, chỉ quý 1–4."""
    def idx(arr):
        out = {}
        for r in arr or []:
            y, q = r.get('yearReport'), r.get('lengthReport')
            if y and q in (1, 2, 3, 4):
                out[(int(y), int(q))] = r
        return out
    i, c = idx(raw.get('is')), idx(raw.get('cf'))
    return [(k, i[k], c.get(k) or {}) for k in sorted(i)]


# ---------------------------------------------------------------- tách khoản theo loại doanh nghiệp
def khoan(loai: str, r: dict, c: dict) -> list[dict]:
    """Các khoản cộng lại ra lợi nhuận trước thuế (tỷ đồng). `nhom`: loi | tai_chinh | mot_lan | du_phong | khac.
    `phan_du` để tổng các khoản luôn khớp LNTT (phần không tách được)."""
    lntt = _n(r, 'isa16')
    ks: list[dict] = []

    def add(ten, v, nhom, ghi=''):
        ks.append(dict(ten=ten, gia_tri=round(v, 1), nhom=nhom, ghi_chu=ghi))
    if loai == 'ngan_hang':
        add('Thu nhập lãi thuần (cho vay trừ trả lãi tiền gửi)', _n(r, 'isb27'), 'loi')
        add('Lãi thuần từ dịch vụ (phí)', _n(r, 'isb30'), 'loi')
        add('Lãi kinh doanh ngoại hối và vàng', _n(r, 'isb31'), 'tai_chinh')
        add('Lãi mua bán chứng khoán', _n(r, 'isb32') + _n(r, 'isb33'), 'mot_lan',
            'phụ thuộc thị trường trái phiếu/cổ phiếu, khó lặp lại đều')
        add('Thu nhập khác', _n(r, 'isb36'), 'mot_lan',
            'ở ngân hàng thường là tiền thu hồi nợ xấu đã xử lý trước đây — có thì tốt nhưng không đều')
        add('Cổ tức nhận được', _n(r, 'isb37'), 'khac')
        add('Chi phí hoạt động (lương, văn phòng…)', _n(r, 'isb39'), 'loi')
        add('Trích lập dự phòng rủi ro tín dụng', _n(r, 'isb41'), 'du_phong',
            'chi phí trên sổ sách để phòng nợ xấu, không phải tiền chi ra')
    elif loai == 'chung_khoan':
        dg = _n(r, 'iss117') + _n(r, 'iss126')
        add('Tự doanh: lãi/lỗ bán chứng khoán + cổ tức', _n(r, 'iss116') + _n(r, 'iss118') + _n(r, 'iss125')
            + _n(r, 'iss127'), 'tai_chinh')
        add('Tự doanh: đánh giá lại danh mục (chưa bán)', dg, 'mot_lan',
            'lãi/lỗ trên giấy theo giá thị trường cuối quý — giá đổi là đổi chiều')
        add('Cho vay ký quỹ (margin) và phải thu', _n(r, 'iss120'), 'loi')
        add('Lãi tiền gửi/trái phiếu giữ đến hạn', _n(r, 'iss119') + _n(r, 'iss121'), 'loi')
        add('Môi giới (doanh thu trừ chi phí)', _n(r, 'iss42') + _n(r, 'iss133'), 'loi')
        add('Ngân hàng đầu tư (bảo lãnh, tư vấn)', _n(r, 'iss44') + _n(r, 'iss46') + _n(r, 'iss123')
            + _n(r, 'iss134') + _n(r, 'iss135') + _n(r, 'iss138'), 'loi')
        add('Chi phí lãi vay', _n(r, 'iss148'), 'tai_chinh')
        add('Chi phí quản lý', _n(r, 'isa10'), 'loi')
    elif loai == 'thuong':
        add('Lợi nhuận gộp (bán hàng trừ giá vốn)', _n(r, 'isa5'), 'loi')
        add('Chi phí bán hàng', _n(r, 'isa9'), 'loi')
        add('Chi phí quản lý', _n(r, 'isa10'), 'loi')
        fx = -_n(c, 'cfa4')            # LCTT cộng ngược lỗ tỷ giá chưa thực hiện → ảnh hưởng lên lãi = −cfa4
        add('Chi phí lãi vay', _n(r, 'isa8'), 'tai_chinh')
        if abs(fx) >= 0.05:
            add('Chênh lệch tỷ giá đánh giá lại (chưa thực hiện)', fx, 'mot_lan',
                'lãi/lỗ trên giấy khi quy đổi nợ/tiền ngoại tệ theo tỷ giá cuối quý — tỷ giá quay đầu là đổi chiều')
        add('Thu/chi tài chính khác', _n(r, 'isa6') + _n(r, 'isa7') - _n(r, 'isa8') - fx, 'tai_chinh')
        add('Lãi từ công ty liên doanh, liên kết', _n(r, 'isa102') or _n(r, 'isa15'), 'khac')
        add('Thu nhập khác (ngoài kinh doanh chính)', _n(r, 'isa14'), 'mot_lan',
            'thanh lý tài sản, tiền phạt, bồi thường… thường không lặp lại')
    if lntt or ks:
        du = lntt - sum(k['gia_tri'] for k in ks)
        if abs(du) >= max(0.5, abs(lntt) * 0.02):
            add('Phần còn lại (không tách được)', du, 'khac')
    return ks


def du_phong_dn(c: dict) -> float:
    """Doanh nghiệp thường: chi phí dự phòng (cfa3, dương = trích thêm, âm = hoàn nhập). Nằm sẵn trong các dòng
    giá vốn/chi phí — chỉ dùng để giải thích, không cộng thêm vào cầu nối."""
    return _n(c, 'cfa3')


def cot_loi(ks: list[dict]) -> float:
    return sum(k['gia_tri'] for k in ks if k['nhom'] == 'loi')


def mot_lan(ks: list[dict]) -> float:
    return sum(k['gia_tri'] for k in ks if k['nhom'] == 'mot_lan')


def _pct(a: float, b: float):
    return round((a / b - 1) * 100, 1) if b and b > 0 else None


def _ty(x: float) -> str:
    s = f'{abs(x):,.0f}'.replace(',', '.') if abs(x) >= 10 else f'{abs(x):.1f}'.replace('.', ',')
    return ('−' if x < 0 else '') + s + ' tỷ'


def _thay_doi(p, a: float | None = None, b: float | None = None) -> str:
    if a is not None and b is not None:
        if b > 0 > a:
            return 'chuyển từ lãi sang lỗ'
        if b <= 0 < a:
            return 'chuyển từ lỗ sang lãi'
    if p is None:
        return 'cùng kỳ lỗ hoặc không có số nên không so được %'
    return ('tăng ' if p >= 0 else 'giảm ') + f'{abs(p):.0f}%'


def _ta(x: dict) -> str:
    """Tả một khoản trong cầu nối bằng lời thường: khoản chi phí thì nói 'tăng/giảm' theo chiều chi phí."""
    ten, ch = x['ten'], x['chenh']
    la_chi = x['nay'] <= 0 and x['cung_ky'] <= 0 and (x['nay'] or x['cung_ky'])
    t = ten[0].lower() + ten[1:]
    if la_chi:
        if not t.startswith(('chi phí', 'trích lập')):
            t = 'lỗ ' + t                   # khoản ± (tỷ giá, tài chính khác…) đang âm ở cả hai kỳ
        return f"{t} {'giảm' if ch > 0 else 'tăng'} {_ty(abs(ch))}"
    return f"{t} {'tăng' if ch > 0 else 'giảm'} {_ty(abs(ch))}"


# ---------------------------------------------------------------- phân tích một mã
def phan_tich(sym: str, raw: dict) -> dict | None:
    qs = _quy(raw)
    if len(qs) < 5:
        return None
    loai = loai_dn([r for _, r, _ in qs])
    idx = {k: (r, c) for k, r, c in qs}
    bang = []
    for (y, q), r, c in qs[-SO_QUY:]:
        ks = khoan(loai, r, c)
        bang.append(dict(q=nhan(y, q), cong_bo=str(r.get('publicDate') or '')[:10],
                         lntt=round(_n(r, 'isa16'), 1), lnst_me=round(_n(r, 'isa22') or _n(r, 'isa20'), 1),
                         doanh_thu=round(_n(r, 'isa3') or _n(r, 'isb38'), 1), loi=round(cot_loi(ks), 1),
                         mot_lan=round(mot_lan(ks), 1),
                         du_phong=round(du_phong_dn(c), 1) if loai == 'thuong' else round(-_n(r, 'isb41'), 1),
                         cfo=round(_n(c, 'cfa18'), 1) if c else None, khoan=ks))
    (y, q), r, c = qs[-1]
    cu = idx.get((y - 1, q))
    nay = bang[-1]
    out = dict(ma=sym, loai=loai, quy=bang, moi_nhat=nay['q'], cong_bo=nay['cong_bo'])
    if not cu:
        out['cau_chuyen'] = [f'{nay["q"]}: chưa có số cùng kỳ năm trước để so.']
        return out
    r0, c0 = cu
    ks1, ks0 = khoan(loai, r, c), khoan(loai, r0, c0)
    m0 = {k['ten']: k['gia_tri'] for k in ks0}
    cau = []
    for k in ks1:
        a, b = k['gia_tri'], m0.get(k['ten'], 0.0)
        cau.append(dict(ten=k['ten'], nhom=k['nhom'], nay=a, cung_ky=round(b, 1), chenh=round(a - b, 1),
                        ghi_chu=k['ghi_chu']))
    cau.sort(key=lambda x: -abs(x['chenh']))
    lntt1, lntt0 = _n(r, 'isa16'), _n(r0, 'isa16')
    np1, np0 = (_n(r, 'isa22') or _n(r, 'isa20')), (_n(r0, 'isa22') or _n(r0, 'isa20'))
    loi1, loi0 = cot_loi(ks1), cot_loi(ks0)
    ml1 = mot_lan(ks1)
    q0 = nhan(y - 1, q)
    out.update(so_voi=q0, cau_noi=cau, lntt=round(lntt1, 1), lntt_cung_ky=round(lntt0, 1),
               lnst_me=round(np1, 1), lnst_me_cung_ky=round(np0, 1), lnst_yoy=_pct(np1, np0),
               loi=round(loi1, 1), loi_cung_ky=round(loi0, 1), loi_yoy=_pct(loi1, loi0),
               mot_lan_ty=round(ml1, 1), mot_lan_pct_lntt=round(ml1 / lntt1 * 100, 1) if lntt1 > 0 else None,
               lntt_bo_mot_lan=round(lntt1 - ml1, 1))
    # ---- câu theo khuôn: số trước, lời sau, không đoán
    cc = []
    cc.append(f'{nay["q"]} lãi sau thuế (phần công ty mẹ) {_ty(np1)}, {_thay_doi(_pct(np1, np0), np1, np0)} so với {q0} '
              f'({_ty(np0)}).' if np1 >= 0 else
              f'{nay["q"]} lỗ sau thuế {_ty(-np1)} (cùng kỳ {q0}: {"lãi " + _ty(np0) if np0 >= 0 else "lỗ " + _ty(-np0)}).')
    # lãi trước thuế và phần của công ty mẹ đi ngược nhau → phần chia cho cổ đông thiểu số đổi
    p_lntt, p_np = _pct(lntt1, lntt0), _pct(np1, np0)
    if p_lntt is not None and p_np is not None and (p_lntt < 0 <= p_np or p_np < 0 <= p_lntt):
        ts1, ts0 = _n(r, 'isa21'), _n(r0, 'isa21')
        cc.append(f'Lưu ý: lãi trước thuế {_thay_doi(p_lntt)} ({_ty(lntt0)} → {_ty(lntt1)}) nhưng phần của cổ đông công ty mẹ '
                  f'{_thay_doi(p_np)}, vì phần lãi chia cho cổ đông thiểu số {"giảm" if abs(ts1) < abs(ts0) else "tăng"} từ '
                  f'{_ty(abs(ts0))} còn {_ty(abs(ts1))} (và thuế thay đổi). Muốn biết công ty kinh doanh tốt lên hay không thì nhìn lãi trước thuế.')
    ten_loi = {'ngan_hang': 'Phần kinh doanh cốt lõi (thu lãi + phí − chi phí hoạt động)',
               'chung_khoan': 'Phần kinh doanh đều (margin, môi giới, lãi tiền gửi − chi phí quản lý)',
               'thuong': 'Phần kinh doanh cốt lõi (lãi gộp − chi phí bán hàng và quản lý)'}.get(loai, 'Phần cốt lõi')
    cc.append(f'{ten_loi}: {_ty(loi1)}, {_thay_doi(_pct(loi1, loi0), loi1, loi0)} (cùng kỳ {_ty(loi0)}).')
    len_ = [x for x in cau if x['chenh'] > 0][:2]
    xuong = [x for x in cau if x['chenh'] < 0][:2]
    if len_:
        cc.append('Kéo lợi nhuận lên nhiều nhất: ' + '; '.join(_ta(x) for x in len_) + '.')
    if xuong:
        cc.append('Kéo lợi nhuận xuống nhiều nhất: ' + '; '.join(_ta(x) for x in xuong) + '.')
    # công ty con chuyển sang liên kết: lãi liên kết tăng mạnh trong khi doanh thu/chi phí hợp nhất cùng co lại
    if loai == 'thuong' and lntt0 > 0:
        jv = next((x for x in cau if x['ten'].startswith('Lãi từ công ty liên doanh')), None)
        gop = next((x for x in cau if x['ten'].startswith('Lợi nhuận gộp')), None)
        cp = [x for x in cau if x['ten'] in ('Chi phí bán hàng', 'Chi phí quản lý')]
        if (jv and gop and jv['chenh'] >= 0.15 * lntt0 and gop['chenh'] < 0
                and sum(x['chenh'] for x in cp) > 0.5 * abs(gop['chenh']) * 0.5):
            cc.append('Dấu hiệu đổi cách hợp nhất: lãi từ công ty liên kết tăng mạnh đúng lúc lãi gộp và chi phí bán hàng, '
                      'quản lý cùng co lại — thường xảy ra khi một công ty con chuyển thành công ty liên kết (không còn cộng '
                      'doanh thu, chi phí; chỉ ghi phần lãi được chia). Nếu đúng vậy thì phần kinh doanh chính không so '
                      'thẳng được với cùng kỳ — cần đọc thuyết minh BCTC để xác nhận.')
            out['can_doc_thuyet_minh'] = True
    # khoản tài chính/liên kết tăng đột biến: thường là lãi bán khoản đầu tư hoặc đổi cách hợp nhất — phải đọc thuyết minh
    for x in cau:
        if x['nhom'] in ('tai_chinh', 'khac') and x['chenh'] > 0 and lntt1 > 0 and x['chenh'] >= 0.30 * lntt1:
            cc.append(f"Cần đọc thuyết minh: {x['ten'][0].lower() + x['ten'][1:]} tăng {_ty(x['chenh'])}, bằng "
                      f"{x['chenh'] / lntt1 * 100:.0f}% lợi nhuận trước thuế. Khoản tăng đột biến cỡ này thường là lãi bán "
                      'khoản đầu tư/công ty con hoặc đổi cách hợp nhất — nếu đúng vậy thì không lặp lại.')
            out['can_doc_thuyet_minh'] = True
    # khoản một lần đáng kể
    nguong = max(abs(lntt1), abs(lntt0), 1.0) * 0.10
    ml = [x for x in cau if x['nhom'] == 'mot_lan' and abs(x['nay']) >= nguong]
    for x in ml:
        cc.append(f"Khoản một lần: {x['ten'].lower()} {_ty(x['nay'])} trong quý này — {x['ghi_chu']}.")
    if ml and lntt1:
        cc.append(f'Bỏ các khoản một lần ra thì lợi nhuận trước thuế là {_ty(lntt1 - ml1)} '
                  f'thay vì {_ty(lntt1)} — đây là con số nên dùng để so các quý.')
    # dự phòng
    if loai == 'ngan_hang':
        dp1, dp0 = -_n(r, 'isb41'), -_n(r0, 'isb41')
        ppop1, ppop0 = _n(r, 'isb40'), _n(r0, 'isb40')
        cc.append(f'Lợi nhuận trước khi trích lập dự phòng {_ty(ppop1)} ({_thay_doi(_pct(ppop1, ppop0), ppop1, ppop0)}); '
                  f'trích lập dự phòng {_ty(dp1)} (cùng kỳ {_ty(dp0)}).')
        if ppop1 > 0 and dp1 > 0:
            cc.append(f'Dự phòng ăn mất {dp1 / ppop1 * 100:.0f}% lợi nhuận trước dự phòng. Trích lập là chi phí '
                      'trên sổ sách: nếu nợ xấu thu hồi được, phần này có thể được hoàn nhập ở các quý sau — chưa chắc chắn.')
        out['ty_le_du_phong'] = round(dp1 / ppop1 * 100, 1) if ppop1 > 0 else None
    elif loai == 'thuong':
        dp1 = du_phong_dn(c)
        lich = [b['du_phong'] for b in bang[:-1]]
        hn = sum(1 for v in lich if v < -0.05)
        if abs(dp1) >= nguong:
            if dp1 > 0:
                cc.append(f'Trong quý trích lập dự phòng {_ty(dp1)} (nằm trong giá vốn/chi phí). Đây là chi phí trên '
                          'sổ sách, không phải tiền chi ra: nếu khoản phải thu thu được hoặc giá hàng tồn hồi lại thì có '
                          f'thể hoàn nhập ở quý sau. {len(lich)} quý trước có {hn} quý hoàn nhập.')
            else:
                cc.append(f'Trong quý hoàn nhập dự phòng {_ty(-dp1)} — phần này cộng vào lợi nhuận nhưng không lặp lại.')
        # dòng tiền 4 quý
        cf4 = [b['cfo'] for b in bang[-4:] if b['cfo'] is not None]
        np4 = sum(b['lnst_me'] for b in bang[-4:])
        if len(cf4) == 4 and np4 > 0:
            tl = sum(cf4) / np4 * 100
            out['tien_that_4q_pct'] = round(tl, 0)
            if sum(cf4) < 0:
                cc.append(f'Tiền từ kinh doanh 4 quý gần nhất âm {_ty(-sum(cf4))} dù lãi {_ty(np4)}: tiền đang bị giữ ở '
                          'khoản phải thu, hàng tồn kho hoặc dự án dở dang — cần xem kỹ.')
            else:
                cc.append(f'Tiền thật thu về từ kinh doanh 4 quý gần nhất {_ty(sum(cf4))}, bằng {tl:.0f}% lợi nhuận cùng kỳ'
                          + (' — lợi nhuận đang về bằng tiền.' if tl >= 80 else
                             ' — phần lớn lợi nhuận còn nằm ở khoản phải thu/hàng tồn, cần xem kỹ.' if tl < 50 else '.'))
    # lỗ: vì đâu
    if lntt1 < 0:
        am = sorted([x for x in ks1 if x['gia_tri'] < 0 and x['nhom'] != 'loi'], key=lambda x: x['gia_tri'])
        if loi1 > 0 and am:
            cc.append(f'Kinh doanh cốt lõi vẫn có lãi {_ty(loi1)}; lỗ đến từ ' +
                      ', '.join(f"{x['ten'].lower()} ({_ty(x['gia_tri'])})" for x in am[:2]) + '.')
        elif loi1 <= 0:
            cc.append('Lỗ từ chính hoạt động kinh doanh cốt lõi — đây là lỗ thật, không phải do khoản một lần.')
    thue_hl = _n(r, 'isa18')
    if abs(thue_hl) >= nguong:
        cc.append(f'Thuế hoãn lại {_ty(thue_hl)}: khoản kế toán, không phải tiền nộp trong quý.')
    out['cau_chuyen'] = cc
    out['co_bat_thuong'] = bool(ml) or (loai == 'thuong' and abs(du_phong_dn(c)) >= nguong)
    return out


def phan_tich_nhieu(raw_all: dict, syms) -> dict:
    out = {}
    for s in syms:
        if s in (raw_all or {}):
            try:
                x = phan_tich(s, raw_all[s])
            except (TypeError, ValueError, ZeroDivisionError) as e:      # một mã hỏng không làm hỏng cả gói
                x = dict(ma=s, loi_doc=f'không đọc được BCTC: {type(e).__name__}')
            if x:
                out[s] = x
    return out
