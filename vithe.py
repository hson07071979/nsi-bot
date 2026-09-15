# -*- coding: utf-8 -*-
"""CO VI THE — vao bao nhieu phan tram NAV, va VI SAO dung con so do.

Vi sao co file nay: cong thuc chia von nam chon trong `engine2.run()`, lan giua
vong lap backtest. Trang web va chuong bao truoc day chi hien "size_pct" tho
(base_size x den x rui ro), BO MAT ba cai tran — nen con so tren web co luc
khong khop voi con so bo may thuc su dat. File nay la MOT nguon su that duy nhat
cho ca ba noi: `lookup.py` (the tra cuu), `alerts2.py` (chuong bao) va
`thresholds.json` (lop quet trong phien + trinh duyet).

Cong thuc GIU NGUYEN nhu engine2.run(), khong doi mot chu:

    tgt = min( nav*base_size*smul*rmul*bm,     # co nen
               nav*max_pos,                    # tran moi ma
               nav*max_total - dang_cam,       # tran tong von
               nav*max_sector - nganh,         # tran moi nganh
               tien_mat )                      # tien con lai
    neu tgt < nav*min_size  ->  KHONG VAO
    neu da cam du max_pos_n ma ->  KHONG VAO

Doi cong thuc o day thi PHAI doi ca engine2.run(), neu khong web se noi mot dang
va bo may lam mot neo.
"""

# Tran moi nganh dang viet cung trong engine2.run() (`nav*0.30 - sec`).
# De o day de con cho nao doc ra duoc, nhung VAN la 0.30 nhu ben do.
MAX_SECTOR = 0.30

TEN_DEN = {'XANH': 'xanh', 'VANG': 'vàng', 'CAM': 'cam', 'DO': 'đỏ'}


def _so(x):
    """None neu khong phai so that (NaN hay khong doi duoc) — de bo qua tran do.

    Vi sao can: trong engine2, `tot` (tong von dang cam) duoc tinh bang tong gia
    x so co. Neu mot ma dang cam bi ngung giao dich hom do thi gia la NaN va
    `tot` thanh NaN. Ham `min()` cua Python lang le BO QUA gia tri NaN do (moi
    phep so sanh voi NaN deu False), tuc la tran tong von khong ap dung phien do.
    Ham nay tai hien dung hanh vi ay — neu khong, web se bao "khong vao lenh"
    trong khi bo may van vao.
    """
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _pc(x):
    """0.252 -> '25,2%' — dau phay thap phan kieu Viet Nam."""
    return ('%.1f%%' % (x * 100)).replace('.', ',')


def co_vi_the(light, rmul=1.0, base_rng=None, cfg=None,
              so_ma_dang_cam=0, tong_dang_cam=0.0, nganh_dang_cam=0.0,
              tien_mat=None):
    """Tra ve co vi the (% NAV) va giai thich tung buoc.

    light           : 'XANH' | 'VANG' | 'CAM' | 'DO' — den thi truong
    rmul            : he so cong rui ro tra ve (1.0 hoac 0.5)
    base_rng        : do rong nen gia, dang ty le (0.09 = nen 9%). None = khong biet.
    cfg             : dict tham so (base_size, max_pos, max_total, max_pos_n,
                      min_size, size_map). Thieu khoa nao thi lay mac dinh PROD.
    so_ma_dang_cam  : so ma dang nam giu
    tong_dang_cam   : ty le NAV dang nam giu (0.62 = 62%)
    nganh_dang_cam  : ty le NAV dang nam giu TRONG CUNG NGANH voi ma nay
    tien_mat        : ty le NAV con la tien mat. None = suy ra 1 - tong_dang_cam.

    Tra ve dict: pct (float, % NAV) · vao (bool) · tran (str) · vi_sao (list)
                 · mot_dong (str) · chi_tiet (dict)
    """
    C = dict(base_size=0.42, max_pos=0.50, max_total=1.0, max_pos_n=12,
             min_size=0.02, max_sector=MAX_SECTOR,
             size_map={'XANH': 1.0, 'VANG': 0.6, 'CAM': 0.35, 'DO': 0.2})
    C.update({k: v for k, v in (cfg or {}).items() if k in C})

    smul = float(C['size_map'].get(light, 0.0))
    rmul = float(rmul if rmul is not None else 1.0)
    bm = 1.2 if (base_rng is not None and base_rng <= 0.10) else 1.0
    tong_dang_cam = _so(tong_dang_cam)
    nganh_dang_cam = _so(nganh_dang_cam)
    tien_mat = _so(tien_mat)
    if tien_mat is None and tong_dang_cam is not None:
        tien_mat = max(0.0, 1.0 - tong_dang_cam)

    co_nen = C['base_size'] * smul * rmul * bm

    # --- tung buoc, de nguoi doc lan lai duoc ---
    vs = ['Cỡ nền của hệ: %s NAV mỗi lệnh.' % _pc(C['base_size'])]

    if smul >= 1.0:
        vs.append('Đèn thị trường %s nên giữ nguyên cỡ (×1,0).' % TEN_DEN.get(light, light))
    elif smul <= 0:
        vs.append('Đèn thị trường %s — hệ KHÔNG mở lệnh mới (×0).' % TEN_DEN.get(light, light))
    else:
        vs.append('Đèn thị trường %s nên cắt còn ×%s → %s.'
                  % (TEN_DEN.get(light, light), str(smul).replace('.', ','), _pc(C['base_size'] * smul)))

    if rmul < 1.0:
        vs.append('Cổng rủi ro gắn cờ vàng (ICR mỏng hoặc CAR sát ngưỡng) nên chia đôi '
                  '×%s → %s.' % (str(rmul).replace('.', ','), _pc(C['base_size'] * smul * rmul)))
    if bm > 1.0:
        vs.append('Nền giá chặt (%s ≤ 10%%) nên thưởng ×1,2 → %s.'
                  % (_pc(base_rng), _pc(co_nen)))
    elif base_rng is not None:
        vs.append('Nền giá %s (trên 10%%) nên không được thưởng ×1,2.' % _pc(base_rng))

    # --- nam cai tran, lay cai thap nhat ---
    ung_vien = [('cỡ nền', co_nen, 'cỡ nền sau khi nhân đèn và rủi ro'),
                ('trần mỗi mã', C['max_pos'],
                 'không mã nào được vượt %s NAV' % _pc(C['max_pos']))]
    if tong_dang_cam is not None:
        ung_vien.append(('trần tổng vốn', max(0.0, C['max_total'] - tong_dang_cam),
                         'tổng vốn đã dùng %s / trần %s'
                         % (_pc(tong_dang_cam), _pc(C['max_total']))))
    if nganh_dang_cam is not None:
        ung_vien.append(('trần mỗi ngành', max(0.0, C['max_sector'] - nganh_dang_cam),
                         ('không ngành nào được vượt %s NAV' % _pc(C['max_sector']))
                         if nganh_dang_cam <= 0 else
                         ('ngành này đã chiếm %s / trần %s'
                          % (_pc(nganh_dang_cam), _pc(C['max_sector'])))))
    if tien_mat is not None:
        ung_vien.append(('tiền mặt còn', max(0.0, tien_mat),
                         'còn %s tiền mặt' % _pc(tien_mat)))
    ten, pct, _ = min(ung_vien, key=lambda t: t[1])

    vao = True
    if smul <= 0:
        vao, pct, ten = False, 0.0, 'đèn chặn'
        vs.append('→ KHÔNG vào lệnh: đèn %s.' % TEN_DEN.get(light, light))
    elif so_ma_dang_cam >= C['max_pos_n']:
        vao, pct, ten = False, 0.0, 'đủ số mã'
        vs.append('→ KHÔNG vào lệnh: đang cầm %d mã, chạm trần %d mã.'
                  % (so_ma_dang_cam, C['max_pos_n']))
    elif pct < C['min_size']:
        vs.append('→ KHÔNG vào lệnh: "%s" chỉ còn %s, dưới cỡ tối thiểu %s — '
                  'vào lệnh bé hơn mức này thì phí ăn hết phần lãi.'
                  % (ten, _pc(pct), _pc(C['min_size'])))
        vao, pct = False, 0.0
    else:
        chat = [t for t in ung_vien if t[0] != 'cỡ nền' and abs(t[1] - pct) < 1e-12]
        if ten == 'cỡ nền':
            vs.append('→ Vào %s NAV. Không chạm trần nào.' % _pc(pct))
        else:
            vs.append('→ Vào %s NAV — bị "%s" cắt xuống (%s).'
                      % (_pc(pct), ten, dict((a, c) for a, b, c in ung_vien)[ten]))
        if chat and ten == 'cỡ nền':
            pass

    mot_dong = ('%s NAV' % _pc(pct)) if vao else 'không vào lệnh'
    if vao and ten != 'cỡ nền':
        mot_dong += ' (bị %s cắt)' % ten

    return dict(
        pct=round(pct * 100, 1), vao=vao, tran=ten, vi_sao=vs, mot_dong=mot_dong,
        chi_tiet=dict(
            base_size=C['base_size'], den=light, den_mul=smul, rui_ro_mul=rmul,
            nen_mul=bm, co_nen=round(co_nen * 100, 1),
            tran_moi_ma=round(C['max_pos'] * 100, 1),
            tran_tong=round(C['max_total'] * 100, 1),
            tran_nganh=round(C['max_sector'] * 100, 1),
            min_size=round(C['min_size'] * 100, 1),
            max_pos_n=C['max_pos_n'],
            dang_cam_n=so_ma_dang_cam,
            dang_cam_pct=(None if tong_dang_cam is None else round(tong_dang_cam * 100, 1)),
            nganh_pct=(None if nganh_dang_cam is None else round(nganh_dang_cam * 100, 1)),
            tien_mat_pct=(None if tien_mat is None else round(tien_mat * 100, 1))))


def tom_tat_danh_muc(vi_the, nav):
    """Tu so lenh dang mo, rut ra trang thai can cho co_vi_the().

    Nhan duoc ca hai kieu ban ghi dang dung trong he:
      site_data2 open_positions : {'sym','sector','shares','last'}   last = nghin dong
      portfolio.json  ['open']  : {'sym','sector','sh','last','entry_px'}

    Tra ve: (so_ma, tong_ty_le, {nganh: ty_le}, tien_mat_ty_le)
    """
    try:
        nav = float(nav)
    except (TypeError, ValueError):
        nav = 0.0
    if nav <= 0:
        return 0, None, {}, None
    tong = 0.0
    nganh = {}
    for p in (vi_the or []):
        try:
            sh = float(p.get('shares', p.get('sh', 0)) or 0)
            gia = p.get('last')
            gia = float(gia) * 1000.0 if gia else float(p.get('entry_px') or 0)
        except (TypeError, ValueError):
            continue
        gt = sh * gia
        if gt != gt:            # NaN
            continue
        tong += gt
        k = p.get('sector') or 'Khác'
        nganh[k] = nganh.get(k, 0.0) + gt
    return (len(vi_the or []), tong / nav,
            {k: v / nav for k, v in nganh.items()},
            max(0.0, 1.0 - tong / nav))


def phan_bo(light, rmul=1.0, base_rng=None, cfg=None,
            so_ma_dang_cam=0, tong_dang_cam=0.0, nganh_dang_cam=0.0, tien_mat=None):
    """CO LENH CHUAN cua tin hieu nay + ghi chu ve so lenh dang chay.

    Vi sao tach lam hai con so: cau hoi "neu lenh nay duoc vao thi vao bao nhieu
    phan tram" la hoi ve CO LENH CUA TIN HIEU, khong phai hoi so lenh mo phong
    hom nay con bao nhieu tien. Tai khoan mo phong 1 ty thuong xuyen day von, neu
    chi tra ve con so thuc te thi ma nao cung hien 0% — dung ky thuat nhung vo
    dung voi nguoi doc, va con sai voi tai khoan that cua anh Son.

    Nen:
      pct       = co lenh chuan, tinh nhu so lenh con trong (cai anh Son can)
      pct_thuc  = con so bo may thuc su dat duoc hom nay voi so lenh hien tai
    Neu hai con so lech nhau thi NOI RO o dong cuoi phan giai thich.
    """
    chuan = co_vi_the(light, rmul=rmul, base_rng=base_rng, cfg=cfg)
    thuc = co_vi_the(light, rmul=rmul, base_rng=base_rng, cfg=cfg,
                     so_ma_dang_cam=so_ma_dang_cam, tong_dang_cam=tong_dang_cam,
                     nganh_dang_cam=nganh_dang_cam, tien_mat=tien_mat)

    vs = list(chuan['vi_sao'])
    if abs(thuc['pct'] - chuan['pct']) > 0.05:
        if thuc['vao']:
            vs.append('Sổ lệnh hiện tại chỉ còn chỗ cho %s — bị %s giới hạn.'
                      % (_pc(thuc['pct'] / 100.0), thuc['tran']))
        else:
            vs.append('Nhưng sổ lệnh hiện tại KHÔNG còn chỗ (%s) nên phiên này '
                      'hệ chưa vào được.' % thuc['tran'])

    return dict(pct=chuan['pct'], tran=chuan['tran'], vi_sao=vs,
                mot_dong=chuan['mot_dong'], vao=chuan['vao'],
                pct_thuc=thuc['pct'], vao_duoc=thuc['vao'], tran_thuc=thuc['tran'],
                chi_tiet=chuan['chi_tiet'])
