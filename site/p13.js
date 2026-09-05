/* ============================================================================
   LỚP REAL-TIME KHÔNG CẦN MÁY CHỦ — feed VPS gọi thẳng từ trình duyệt

   VÌ SAO ĐƯỢC. FireAnt trả dữ liệu tốt nhưng không gửi nhãn CORS, nên trình duyệt
   từ chối đọc — đó là lý do trước đây phải dựng Cloudflare Worker đứng giữa.
   Feed bảng giá của VPS thì CÓ gửi nhãn `Access-Control-Allow-Origin: *`, và nhận
   cả trăm mã trong MỘT lần gọi. Nghĩa là trang web tự hỏi giá được, không cần
   máy chủ nào cả, không tốn một đồng nào, và không tốn một token nào của Claude.

       GET https://bgapidatafeed.vps.com.vn/getliststockdata/ACB,BAF,...   (110 mã)

   ĐÁNH ĐỔI PHẢI NÓI THẲNG. Feed VPS không có `BuyCount/SellCount`, nên
   ĐIỀU KIỆN 7 — cỡ lệnh mua so cỡ lệnh bán — KHÔNG tính được từ nguồn này.
   Điều kiện 7 lấy từ `live.json` (máy chủ chạy 10–20 phút một lần, đọc FireAnt).
   Tỷ lệ cỡ lệnh vốn đổi chậm nên trễ 10–20 phút là chấp nhận được, nhưng trang
   phải GHI RÕ nó cũ bao lâu chứ không được giả vờ là số real-time.

   Bù lại, VPS cho một thứ FireAnt không có: ba mức giá mua và ba mức giá bán
   ngay lúc này. Trang tính thêm `tỷ lệ dư mua/dư bán` từ đó — một chỉ báo KHÁC,
   dán nhãn riêng, KHÔNG dùng thay điều kiện 7.
   ========================================================================== */

const VPS = 'https://bgapidatafeed.vps.com.vn/getliststockdata/';
const VPSI = 'https://bgapidatafeed.vps.com.vn/getlistindexdetail/10';   // 10 = HOSE
const RTV = {
  dang: false, loi: 0, timer: null, at: null, n: 0,
  nhip: 15000,          // 15 giây một nhịp — VPS chịu được, và đây là gọi MỘT lần cho cả rổ
  bat: true,            // anh Sơn tắt được ở thanh cài đặt
  amthanh: true,
  thongbao: false,      // chỉ bật sau khi trình duyệt cho phép
  vnindex: null,
  keu: new Set(),       // đã kêu rồi thì thôi, không kêu lại cùng một mã trong phiên
  demat_nghi: 8,        // ĐỂ MẮT: kêu xong thì nghỉ bấy nhiêu PHÚT mới kêu lại cùng mã
};

/* ---------- NHỊP CHUÔNG "ĐỂ MẮT" ------------------------------------------
   Mã trong watchlist tăng ≥ 2,5% là chuyện có thể kéo dài cả phiên. Kêu mỗi
   nhịp quét (15 giây) thì thành tiếng ồn, và tiếng ồn thì bị bỏ qua — đúng cái
   anh Sơn phàn nàn. Nên: kêu MỘT lần, rồi im trong `RTV.demat_nghi` phút; còn
   ≥ 2,5% thì nhắc lại, hết thì thôi. Mỗi mã có đồng hồ riêng.
   `lanCuoi` để thanh trạng thái biết lúc nào nên sáng vàng, lúc nào nên dịu. */
const CHUONG = {
  lan: {},              // mã -> lúc kêu gần nhất (ms)
  lanCuoi: 0,           // lần kêu gần nhất bất kể mã nào
  SANG_MS: 90 * 1000,   // băng vàng trên đỉnh sáng bấy nhiêu lâu sau mỗi lần kêu
};
function _dungLucKeu(sym) {
  const nghi = Math.max(1, +RTV.demat_nghi || 8) * 60000;
  const gio = Date.now();
  if (gio - (CHUONG.lan[sym] || 0) < nghi) return false;
  CHUONG.lan[sym] = gio;
  return true;
}

/* ---------- phiên có đang mở không (giờ Việt Nam, không phụ thuộc múi giờ máy) ---------- */
function gioVN() {
  const t = new Date();
  return new Date(t.getTime() + (t.getTimezoneOffset() + 420) * 60000);
}
function phienMo() {
  const t = gioVN(), d = t.getDay(), p = t.getHours() * 60 + t.getMinutes();
  if (d === 0 || d === 6) return false;
  return (p >= 9 * 60 && p <= 11 * 60 + 35) || (p >= 13 * 60 && p <= 14 * 60 + 50);
}
/* Phiên đã đi bao nhiêu phần — dùng để dự phóng khối lượng cuối phiên.
   Không tính giờ nghỉ trưa vào, không thì 11h30 nhìn như đã đi 60% phiên. */
function phanPhien() {
  const t = gioVN(), p = t.getHours() * 60 + t.getMinutes();
  const TONG = 150 + 110;                       // 9h00–11h30 và 13h00–14h50
  if (p < 9 * 60) return 0;
  if (p <= 11 * 60 + 30) return (p - 540) / TONG;
  if (p < 13 * 60) return 150 / TONG;
  if (p <= 14 * 60 + 50) return (150 + p - 780) / TONG;
  return 1;
}

/* ---------- danh sách mã cần hỏi: cả rổ, một lần gọi ---------- */
function maHoiVPS() {
  const L = D.lookup || {};
  const s = new Set();
  Object.keys(L).forEach(k => { if (L[k].inuni || L[k].state === 'cho' || L[k].state === 'fa') s.add(k); });
  danhMuc().forEach(p => s.add(p.sym));
  ghimThuCong().forEach(w => s.add(w.sym));
  return [...s].slice(0, 140);
}

/* ---------- đổi một dòng VPS sang đúng khuôn mà tinhLaiTinHieu() đang chờ ----------
   VPS trả giá theo NGHÌN ĐỒNG (22.1), khuôn cũ dùng ĐỒNG (22100). Đổi ở đây một lần,
   để phần tính điều kiện phía dưới không phải biết dữ liệu đến từ đâu. */
function doiKhuonVPS(x) {
  const k = v => { const n = +v; return Number.isFinite(n) ? n * 1000 : 0; };
  const price = k(x.lastPrice), ref = k(x.r);
  if (!price || !ref) return null;
  const vol = (+x.lot || 0) * 10;                 // VPS đếm theo lô 10 cổ phiếu
  const ave = k(x.avePrice) || price;
  // ba mức dư mua (g1–g3) và ba mức dư bán (g4–g6) — chỉ báo BỔ SUNG, không thay ĐK7
  const doc = g => { const a = String(x[g] || '').split('|'); return +a[1] || 0; };
  const duMua = doc('g1') + doc('g2') + doc('g3');
  const duBan = doc('g4') + doc('g5') + doc('g6');
  return {
    d: null, price, ref,
    open: k(x.openPrice) || price,
    hi: k(x.highPrice) || price,
    lo: k(x.lowPrice) || price,
    vol, tv: vol * ave,
    tran: k(x.c), san: k(x.f),
    duMua, duBan,
    sauMua: duBan > 0 ? duMua / duBan : null,     // > 1 = bên mua đang xếp hàng dày hơn
    fmua: +x.fBVol || 0, fban: +x.fSVolume || 0,  // khối ngoại trong phiên
  };
}

/* ---------- một nhịp real-time ---------- */
async function napVPS() {
  if (RTV.dang || !RTV.bat) return;
  const syms = maHoiVPS();
  if (!syms.length) return;
  RTV.dang = true;
  try {
    const r = await fetch(VPS + syms.join(','), { cache: 'no-store' });
    if (!r.ok) throw new Error('VPS ' + r.status);
    const arr = await r.json();
    if (!Array.isArray(arr) || !arr.length) throw new Error('VPS rỗng');

    const rows = {};
    arr.forEach(x => { const v = doiKhuonVPS(x); if (v) rows[String(x.sym).toUpperCase()] = v; });

    // ĐIỀU KIỆN 7 lấy từ ảnh chụp máy chủ — nguồn khác, tuổi khác, phải nhớ tuổi nó.
    const sv = LIVE.server || {};
    (sv.hits || []).forEach(h => {
      if (rows[h.sym] && h.ordimb != null) { rows[h.sym].oi = h.ordimb; rows[h.sym].oi_at = sv.asof; }
    });

    NSI.rt = rows;
    RTV.n = Object.keys(rows).length;
    RTV.at = new Date();
    NSI.rtAt = new Date(RTV.at.getTime() - RTV.at.getTimezoneOffset() * 60000).toISOString().slice(0, 19);
    LIVE.rtOn = true; LIVE.rtSrc = 'VPS'; RTV.loi = 0;

    tinhLaiTinHieuVPS();
    renderLiveBar();
    veLaiTrang('danhmuc'); veLaiTrang('chuong'); veLaiTrang('bieudo');
    napChiSo();
  } catch (e) {
    RTV.loi++;
    if (RTV.loi >= 5) {                       // hỏng năm nhịp liền thì lùi về live.json
      if (RTV.timer) { clearInterval(RTV.timer); RTV.timer = null; }
      LIVE.rtOn = false;
      if (LIVE.server) { LIVE.data = LIVE.server; renderLiveBar(); veLaiTrang('chuong'); }
      // thử lại sau 5 phút — mạng chập chờn thì đừng bỏ hẳn
      setTimeout(() => { RTV.loi = 0; batRealtimeVPS(); }, 300000);
    }
  } finally { RTV.dang = false; }
}

/* ---------- VN-Index real-time, cùng một nguồn ---------- */
async function napChiSo() {
  try {
    const r = await fetch(VPSI, { cache: 'no-store' });
    const a = await r.json();
    const x = Array.isArray(a) ? a[0] : null;
    if (x) RTV.vnindex = { v: +x.indexValue || +x.index || 0, ch: +x.change || 0, pc: +x.changePercent || 0 };
  } catch (e) { /* chỉ số hỏng thì thôi, không ảnh hưởng chuông */ }
}

/* ---------- tính lại tín hiệu từ số VPS ----------
   Cùng công thức máy chủ dùng. Khác một chỗ và chỉ một chỗ: điều kiện 7 đến từ
   ảnh chụp cũ hơn, nên khi nó THIẾU thì mã KHÔNG được lên mức MUA — chỉ SẮP ĐỦ.
   Thà báo thiếu còn hơn báo mua một phiên mà bộ máy chín lớp vốn không đụng vào. */
function tinhLaiTinHieuVPS() {
  const R = NSI.rt || {}, L = D.lookup || {}, hits = [];
  const oiMin = (LIVE.server && LIVE.server.ordimb_min) || 1.20;
  const f = phanPhien(), mo = phienMo();

  Object.keys(R).forEach(sym => {
    const t = L[sym], r = R[sym];
    if (!t || !r || !r.price || !r.ref) return;
    if (t.state !== 'cho' && t.state !== 'fa') return;

    const pct = r.price / r.ref - 1;
    const volr = t.vma20 ? r.vol / t.vma20 : 0;
    // Dự phóng cuối phiên: khối lượng hiện tại chia phần phiên đã đi.
    // Sau 14h50 thì thôi dự phóng, số thật rồi.
    const volr_proj = (mo && f > 0.12 && f < 0.98) ? volr / f : volr;
    const gtgd_proj = (mo && f > 0.12 && f < 0.98) ? r.tv / f : r.tv;

    const coOI = r.oi != null;
    const cond = {
      'Biên độ tăng giá': pct * 100 >= t.thr,
      'Khối lượng ≥ 2× TB20': r.vol >= t.need_vol,
      'GTGD ≥ 15 tỷ': r.tv >= 15e9,
      'Đóng cửa nửa trên nến': r.hi > r.lo ? r.price >= (r.hi + r.lo) / 2 : true,
    };
    cond[`Cỡ lệnh mua ≥ ${oiMin.toFixed(2)}× cỡ lệnh bán`] = coOI ? r.oi >= oiMin : false;

    const n4 = ['Biên độ tăng giá', 'Khối lượng ≥ 2× TB20', 'GTGD ≥ 15 tỷ', 'Đóng cửa nửa trên nến']
                 .filter(k => cond[k]).length;
    const du5 = n4 === 4 && coOI && r.oi >= oiMin;
    const cho = t.state === 'cho';

    let lvl = null;
    if (cho && du5) lvl = 'MUA';
    else if (cho && n4 === 4) lvl = 'SAP_DU';               // đủ 4, chờ xác nhận dòng tiền
    else if (cho && n4 >= 3) lvl = 'SAP_DU';
    else if (pct * 100 >= ((LIVE.data || {}).de_mat_pct || 2.5)) lvl = 'DE_MAT';
    else if (cho && (volr >= 1.5 || pct * 100 >= t.thr * 0.5)) lvl = 'THEO_DOI';
    if (!lvl) return;

    const miss = Object.keys(cond).filter(k => !cond[k]);
    hits.push({
      sym, name: t.name, level: lvl, fa: t.state === 'fa',
      price: +(r.price / 1000).toFixed(2), ref: +(r.ref / 1000).toFixed(2),
      pct: +(pct * 100).toFixed(2), need_px: t.need_px,
      volr: +volr.toFixed(2), volr_proj: +volr_proj.toFixed(2), need_vol: t.need_vol, vol: r.vol,
      gtgd: +(r.tv / 1e9).toFixed(1), gtgd_proj: +(gtgd_proj / 1e9).toFixed(1),
      score: t.score, base: t.base,
      ordimb: coOI ? +r.oi.toFixed(2) : null, ordimb_min: oiMin, ordimb_at: r.oi_at || null,
      sauMua: r.sauMua == null ? null : +r.sauMua.toFixed(2),
      fnet: r.fmua - r.fban,
      // BA thứ khác nhau, trước đây bị gộp làm một tên `tran` nên sinh lỗi so sánh
      // kiểu dữ liệu ở dưới. Tách rõ:
      gia_tran: r.tran || null,          // giá trần phiên nay, theo đồng
      da_tran: !!(r.tran && r.price >= r.tran - 1),   // đã chạm trần chưa
      nguong_pct: t.thr,                 // biên độ % cần đạt để tính là phiên bùng nổ
      cond, miss,
    });
  });

  const bac = { MUA: 0, SAP_DU: 1, DE_MAT: 2, THEO_DOI: 3 };
  hits.sort((a, b) => bac[a.level] - bac[b.level] || b.pct - a.pct);

  const cu = LIVE.server || {};
  const ses = cu.session || D.asof;
  LIVE.data = Object.assign({}, cu, {
    hits, session: ses, asof: NSI.rtAt, realtime: true, rtSrc: 'VPS',
    open: mo, frac: f,
    scanned: RTV.n, universe: Object.keys(L).length,
    n_mua: hits.filter(h => h.level === 'MUA').length,
    n_de_mat: hits.filter(h => h.level === 'DE_MAT').length,
  });

  // ---- CHUÔNG ----
  const moi = hits.filter(h => h.level === 'MUA' && !RTV.keu.has('M:' + h.sym + ':' + ses));
  moi.forEach(h => RTV.keu.add('M:' + h.sym + ':' + ses));
  if (moi.length && !LIVE.firstLoad) reoChuong(moi, 'mua');

  // Mã SẮP ĐỦ đã đi được 80% quãng đường tới ngưỡng bùng nổ.
  //
  // LỖI ĐÃ SỬA: dòng này từng viết `h.pct >= h.tran * 0.8`, mà `tran` khi đó là
  // một giá trị ĐÚNG/SAI (đã chạm trần hay chưa). JavaScript đổi true thành 1 và
  // false thành 0, nên điều kiện thật sự chạy là "tăng ≥ 0,8%" hoặc "tăng ≥ 0%" —
  // gần như mọi mã xanh đều lọt. Ngưỡng coi như không tồn tại. So sánh đúng phải
  // là với NGƯỠNG PHẦN TRĂM (5,8% HOSE · 8,8% HNX), không phải với một cờ nhị phân.
  // ---- CHUÔNG ĐỂ MẮT: mã watchlist đang tăng ≥ 2,5% ----
  // Không dùng `RTV.keu` như chuông đỏ (chuông đỏ kêu đúng một lần mỗi phiên vì
  // đủ điểm mua là việc dứt khoát). Ở đây mã có thể lên xuống quanh ngưỡng cả
  // phiên nên dùng đồng hồ nghỉ theo từng mã.
  const dematMoi = hits.filter(h => h.level === 'DE_MAT' && _dungLucKeu(h.sym));
  if (dematMoi.length && !LIVE.firstLoad && !moi.length) reoChuong(dematMoi, 'demat');

  const sapMoi = hits.filter(h => h.level === 'SAP_DU'
                                  && h.nguong_pct > 0
                                  && h.pct >= h.nguong_pct * 0.8
                                  && !RTV.keu.has('S:' + h.sym + ':' + ses));
  if (sapMoi.length) sapMoi.forEach(h => RTV.keu.add('S:' + h.sym + ':' + ses));
}

/* ---------- chuông: âm thanh + thông báo trình duyệt + nhấp nháy tiêu đề ---------- */
let _titleGoc = null, _titleTimer = null;
function reoChuong(list, loai) {
  const mua = loai === 'mua';
  // Hai loại chuông, hai câu chữ. Trước đây mọi thông báo đều ghi "mã đủ điểm
  // mua" kể cả khi chỉ là nhắc để mắt — đọc trên điện thoại là hiểu nhầm ngay.
  const tieude = mua ? `🔴 ${list.length} mã đủ điểm mua`
                     : `🟡 ${list.length} mã watchlist đang tăng mạnh`;
  CHUONG.lanCuoi = Date.now();
  if (typeof bangBao === 'function') bangBao(list, loai);      // toast sẵn có
  if (RTV.amthanh && typeof keng === 'function') keng(loai);

  // Thông báo hệ điều hành — thứ DUY NHẤT kêu được khi anh Sơn đang ở tab khác.
  if (RTV.thongbao && 'Notification' in window && Notification.permission === 'granted') {
    try {
      const n = new Notification(tieude, {
        body: list.map(h => `${esc(h.sym)} ${h.price} ${h.pct >= 0 ? '+' : ''}${h.pct}% · vol ${h.volr}× · điểm ${h.score}`).join('\n')
              + (mua ? '' : '\nChỉ để ngó chừng — chưa đủ điều kiện vào lệnh.'),
        tag: mua ? 'nsi-mua' : 'nsi-demat', renotify: true, requireInteraction: mua,
      });
      n.onclick = () => { window.focus(); if (typeof go === 'function') go('chuong'); n.close(); };
    } catch (e) { /* vài trình duyệt chặn, bỏ qua */ }
  }

  // Nhấp nháy tiêu đề tab — cách nhắc rẻ nhất khi thông báo bị từ chối.
  // Chỉ chuông ĐỎ mới được nháy tiêu đề tab. Nhắc "để mắt" mà cũng nháy thì
  // cả phiên tiêu đề chớp liên tục, chẳng còn ai phân biệt được cái nào gấp.
  if (!mua) return;
  if (_titleGoc === null) _titleGoc = document.title;
  clearInterval(_titleTimer);
  let on = false, dem = 0;
  _titleTimer = setInterval(() => {
    document.title = (on = !on) ? `🔴 ${list.length} MÃ ĐỦ ĐIỂM MUA` : _titleGoc;
    if (++dem > 40) { clearInterval(_titleTimer); document.title = _titleGoc; }
  }, 900);
  document.addEventListener('visibilitychange', function xoa() {
    if (!document.hidden) {
      clearInterval(_titleTimer); document.title = _titleGoc;
      document.removeEventListener('visibilitychange', xoa);
    }
  });
}

/* ---------- xin quyền thông báo ---------- */
async function xinQuyenThongBao() {
  if (!('Notification' in window)) { alert('Trình duyệt này không hỗ trợ thông báo.'); return; }
  const q = await Notification.requestPermission();
  RTV.thongbao = (q === 'granted');
  luuCaiDat();
  veLaiTrang('chuong');
  if (RTV.thongbao) new Notification('Nguyễn Sơn Invest', { body: 'Chuông báo đã bật. Khi có mã đủ điểm mua, thông báo sẽ hiện ở đây kể cả khi anh đang ở tab khác.' });
}

/* ---------- nhớ lựa chọn của anh Sơn giữa các lần mở trang ---------- */
function luuCaiDat() {
  try {
    localStorage.setItem('nsi_rt', JSON.stringify({
      bat: RTV.bat, amthanh: RTV.amthanh, thongbao: RTV.thongbao, nhip: RTV.nhip,
      demat_nghi: RTV.demat_nghi,
    }));
  } catch (e) { /* chế độ riêng tư chặn, chạy bằng mặc định */ }
}
function docCaiDat() {
  try {
    const s = JSON.parse(localStorage.getItem('nsi_rt') || '{}');
    if (typeof s.bat === 'boolean') RTV.bat = s.bat;
    if (typeof s.amthanh === 'boolean') RTV.amthanh = s.amthanh;
    if (+s.demat_nghi >= 1) RTV.demat_nghi = +s.demat_nghi;
    if (typeof s.nhip === 'number') RTV.nhip = s.nhip;
    RTV.thongbao = ('Notification' in window) && Notification.permission === 'granted' && s.thongbao !== false;
  } catch (e) { /* đọc không được thì dùng mặc định */ }
}

/* ---------- bảng điều khiển chuông, cắm vào trang Chuông báo ---------- */
function bangDieuKhienChuong() {
  const cho = ('Notification' in window) ? Notification.permission : 'khong-ho-tro';
  const tuoiOI = (LIVE.server && LIVE.server.asof) ? hhmm(LIVE.server.asof) : '—';
  return `
  <div class="card rtbox">
    <div class="rtrow">
      <div>
        <div style="font-weight:660;color:var(--text-primary)">Chuông báo real-time</div>
        <div class="muted" style="font-size:12.5px">
          ${LIVE.rtOn
            ? `Đang hỏi giá <b>${RTV.n} mã</b> mỗi <b>${RTV.nhip / 1000} giây</b> thẳng từ bảng giá VPS —
               không qua máy chủ nào, không tốn phí. Cập nhật lúc <b>${RTV.at ? RTV.at.toLocaleTimeString('vi') : '—'}</b>.`
            : 'Chưa nối được bảng giá. Trang đang đọc ảnh chụp của máy chủ.'}
        </div>
      </div>
      <label class="sw"><input type="checkbox" ${RTV.bat ? 'checked' : ''}
        onchange="RTV.bat=this.checked;luuCaiDat();this.checked?batRealtimeVPS():dungRealtimeVPS()"><span></span></label>
    </div>
    <div class="rtrow">
      <div><div style="font-weight:660;color:var(--text-primary)">Âm thanh</div>
        <div class="muted" style="font-size:12.5px">Hai tiếng cao khi có mã đủ điểm mua, một tiếng trầm khi mã watchlist đang tăng mạnh.</div></div>
      <label class="sw"><input type="checkbox" ${RTV.amthanh ? 'checked' : ''}
        onchange="RTV.amthanh=this.checked;luuCaiDat()"><span></span></label>
    </div>
    <div class="rtrow">
      <div><div style="font-weight:660;color:var(--text-primary)">Thông báo hệ điều hành</div>
        <div class="muted" style="font-size:12.5px">Thứ duy nhất kêu được khi anh đang ở tab khác.
          ${cho === 'granted' ? 'Đã bật.' : cho === 'denied'
            ? 'Trình duyệt đang chặn — mở khoá ở biểu tượng 🔒 cạnh thanh địa chỉ.'
            : 'Chưa xin quyền.'}</div></div>
      ${cho === 'granted'
        ? `<label class="sw"><input type="checkbox" ${RTV.thongbao ? 'checked' : ''}
             onchange="RTV.thongbao=this.checked;luuCaiDat()"><span></span></label>`
        : `<button class="btn" onclick="xinQuyenThongBao()" ${cho === 'denied' ? 'disabled' : ''}>Bật</button>`}
    </div>
    <div class="rtrow">
      <div><div style="font-weight:660;color:var(--text-primary)">Nhắc lại chuông "để mắt"</div>
        <div class="muted" style="font-size:12.5px">Mã watchlist tăng ≥ 2,5% thì kêu một lần, rồi im bấy nhiêu lâu
          mới nhắc lại nếu nó vẫn còn tăng. Chuông đỏ (đủ điểm mua) không bị ảnh hưởng — vẫn kêu ngay.</div></div>
      <select class="fin" style="width:120px" onchange="RTV.demat_nghi=+this.value;luuCaiDat()">
        ${[[5, '5 phút'], [8, '8 phút'], [10, '10 phút'], [15, '15 phút']].map(
          ([v, l]) => `<option value="${v}"${+RTV.demat_nghi === v ? ' selected' : ''}>${l}</option>`).join('')}
      </select>
    </div>
    <div class="rtrow">
      <div><div style="font-weight:660;color:var(--text-primary)">Nhịp hỏi giá</div>
        <div class="muted" style="font-size:12.5px">Nhanh hơn thì hao pin hơn. 15 giây là đủ cho một hệ vào lệnh cuối phiên.</div></div>
      <select class="fin" style="width:120px" onchange="RTV.nhip=+this.value;luuCaiDat();batRealtimeVPS()">
        ${[[10000, '10 giây'], [15000, '15 giây'], [30000, '30 giây'], [60000, '1 phút']].map(
          ([v, l]) => `<option value="${v}"${RTV.nhip === v ? ' selected' : ''}>${l}</option>`).join('')}
      </select>
    </div>
    <div class="note info" style="margin:10px 0 0"><b>Một chỗ trung thực phải nói rõ.</b>
      Giá, khối lượng, GTGD ở trên là <b>real-time</b>. Nhưng <b>điều kiện 7 — cỡ lệnh mua so cỡ lệnh bán</b>
      thì bảng giá VPS không có; nó lấy từ ảnh chụp máy chủ lúc <b>${tuoiOI}</b> (làm mới 10–20 phút một lần).
      Vì vậy mã nào chưa có số đó thì <b>không</b> được lên mức đủ điểm mua — chỉ đứng ở mức sắp đủ.
      Thà báo thiếu còn hơn báo mua một phiên mà bộ máy chín lớp vốn không đụng vào.</div>
  </div>`;
}

/* ---------- bật / dừng ---------- */
function batRealtimeVPS() {
  if (RTV.timer) clearInterval(RTV.timer);
  if (!RTV.bat) return;
  napVPS();
  RTV.timer = setInterval(() => { if (phienMo() || RTV.loi === 0) napVPS(); }, RTV.nhip);
}
function dungRealtimeVPS() {
  if (RTV.timer) { clearInterval(RTV.timer); RTV.timer = null; }
  LIVE.rtOn = false;
  if (LIVE.server) { LIVE.data = LIVE.server; renderLiveBar(); veLaiTrang('chuong'); }
}

/* Ghi đè bộ real-time cũ (chạy qua Cloudflare Worker). Bản VPS không cần gì cả,
   nên nó là mặc định. Cầu nối cũ vẫn dùng được cho biểu đồ nến ở trang Chi tiết mã. */
napRealtime = napVPS;
