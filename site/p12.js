/* ============================================================================
   MÔ HÌNH DỮ LIỆU CHUNG — mọi trang đọc từ đây, không trang nào tự bịa số.

   Có ĐÚNG BA nguồn nói về "hệ thống đang nắm giữ cái gì":

     1. portfolio.json  — máy chủ tự ghi. Hệ ra tín hiệu MUA là vào sổ, bộ thoát
                          tự bán. Không ai sửa được.
     2. manual.json     — anh Sơn nhập tay ở trang "Sổ tay của tôi" rồi đăng lên.
                          Lệnh anh vào chảy thẳng vào danh mục; mã anh theo dõi
                          chảy vào phần ghim thủ công của Watchlist.
     3. ghim.txt        — danh sách ghim trong repo private, vào qua watchlist.

   Ba nguồn gộp lại thành MỘT danh mục duy nhất mà khách hàng nhìn thấy, mỗi
   dòng có nhãn nguồn. Không có chuyện trang này thấy khác trang kia.

   Thứ tự dự phòng khi thiếu file (mở bằng file:// trên máy chẳng hạn):
        file tải về  ->  ảnh chụp nhúng sẵn trong trang  ->  bản nháp trong máy
   ========================================================================== */
const NSI = {
  pf: null,        // portfolio.json  (máy chủ ghi)
  manual: null,    // manual.json     (anh Sơn đăng)
  cfg: null,       // config.json     (địa chỉ cầu nối real-time, tên repo)
  rt: null,        // giá real-time vừa lấy về qua cầu nối
  rtAt: null,
};

/* trang có đang chạy trên máy chủ thật không (mở bằng file:// thì không) */
function LIVEOK() { return location.protocol === 'http:' || location.protocol === 'https:'; }

/* ---------- đọc ba nguồn, luôn trả về vật thể dùng được ---------- */
function pfData() {
  return NSI.pf || D.portfolio || null;
}
function manualData() {
  // Bản ĐÃ ĐĂNG — thứ khách hàng đọc được. Nháp trong máy anh Sơn không tính ở đây.
  const pick = o => o && typeof o === 'object'
    ? { trades: o.trades || [], watch: o.watch || o.syms || [],
        an: o.an || [], loai: o.loai || [], updated: o.updated || null }
    : null;
  return pick(NSI.manual) || pick(D.manual)
      || { trades: [], watch: [], an: [], loai: [], updated: null };
}
function manualDraft() {
  // Bản NHÁP trong trình duyệt anh Sơn — hiện kèm nhãn "chưa đăng", chỉ mình anh thấy.
  try { return nsiLoad(); } catch (e) { return { trades: [], watch: [], an: [], loai: [] }; }
}
/* gộp đã đăng + nháp, nháp nào chưa có trong bản đăng thì gắn cờ chuaDang */
function manualGop() {
  const pub = manualData(), dr = manualDraft();
  const kT = t => t.sym + '|' + (t.buy_d || '');
  const kW = w => w.sym;
  const coT = new Set(pub.trades.map(kT)), coW = new Set(pub.watch.map(kW));
  const coL = new Set((pub.loai || []).map(kW));
  return {
    updated: pub.updated,
    // Mã anh Sơn ẩn khỏi danh mục. Gộp bản đã đăng với bản nháp: ẩn một mã ở
    // máy anh là thấy hiệu lực NGAY, không phải chờ đăng lên trang mới thấy.
    an: [...new Set([...(pub.an || []), ...(dr.an || [])])],
    trades: pub.trades.map(t => ({ ...t, chuaDang: false }))
      .concat(dr.trades.filter(t => !coT.has(kT(t))).map(t => ({ ...t, chuaDang: true }))),
    watch: pub.watch.map(w => ({ ...w, chuaDang: false }))
      .concat(dr.watch.filter(w => !coW.has(kW(w))).map(w => ({ ...w, chuaDang: true }))),
    // Mã anh Sơn LOẠI — chi phối chính bộ máy (manual.py đọc khoá này), khác
    // hẳn `an` ở trên vốn chỉ giấu khỏi bảng danh mục.
    loai: (pub.loai || []).map(w => ({ ...w, chuaDang: false }))
      .concat((dr.loai || []).filter(w => !coL.has(kW(w))).map(w => ({ ...w, chuaDang: true }))),
  };
}
function cfgData() {
  return NSI.cfg || D.config || {};
}

/* Giá mới nhất của một mã — real-time trước, rồi tới nến, rồi tới bộ lọc.
   TRẢ VỀ LUÔN LUÔN THEO NGHÌN ĐỒNG (13,85), không bao giờ theo đồng (13850).

   Lỗi đã sửa ở đây: `NSI.rt[sym].price` để theo ĐỒNG vì nó giữ nguyên khuôn của
   cầu nối FireAnt cũ, còn ba nguồn dự phòng phía dưới đều theo NGHÌN ĐỒNG. Nhánh
   đầu tiên vì thế trả về số lớn gấp 1.000 lần ba nhánh kia. Hậu quả trên trang
   Danh mục: giá hiện tại 13850.00, giá trị 1.522 tỷ, lãi +94.566%, tỷ trọng
   24.371% tài khoản — trong khi số thật là 13,85 · 1,52 tỷ · −5,33%.
   Chia ngay tại đây, một chỗ duy nhất, để mọi nơi gọi hàm này đều nhận cùng đơn vị. */
function giaMoiNhat(sym) {
  const r = (NSI.rt || {})[sym];
  if (r && r.price) return r.price / 1000;
  const c = (D.candles || {})[sym];
  if (c && c.bars && c.bars.length) return c.bars[c.bars.length - 1][4];
  const x = (D.lookup || {})[sym];
  if (x && x.price) return x.price;
  const q = (((D.screener || {}).rows) || []).find(y => y.sym === sym);
  return q ? q.price : null;
}
function nganhCua(sym) {
  const x = (D.lookup || {})[sym];
  return (x && x.sector) || '—';
}
function tenCua(sym) {
  const x = (D.lookup || {})[sym];
  return (x && x.name) || '';
}

/* DANH MỤC HỆ THỐNG — xem ghi chú trong danhMuc(): các sổ tách bạch theo book_id. */
function danhMuc() {
  /* AUDIT 23/09/2026 — SỔ TÁCH BẠCH (book_id), không trộn NAV.
     "Đang cầm" = sổ LIVE_PAPER (portfolio.json, vốn 1 tỷ mở 15/09/2026, cỡ lệnh
     tính trên CHÍNH NAV của nó) + sổ MANUAL (lệnh anh Sơn nhập tay, không có NAV).
     Vị thế của BACKTEST (D.open_positions, NAV ~vài tỷ từ 2019) KHÔNG còn chen vào
     bảng hiện tại — xem danhMucBacktest() ở trang nghiên cứu. Một mã có thể nằm ở
     hai sổ cùng lúc: hiện cả hai dòng, mỗi dòng ghi rõ sổ của nó. */
  const out = [];
  const an = new Set((manualGop().an || []).map(s => String(s).toUpperCase()));
  const F = pfData();
  (F && F.open || []).forEach(p => {
    if (an.has(String(p.sym).toUpperCase())) return;
    const px = giaMoiNhat(p.sym) || p.last || (p.entry_px / 1000);
    // giá trị = số cổ × giá trị mỗi cổ gốc (đã quy đổi quyền, xem portfolio.py)
    const k = p.k_adj || 1;
    const val1 = (p.last_val && p.last) ? (p.last_val / 1000) * (px / p.last) : px;
    out.push({
      book_id: 'LIVE_PAPER', sym: p.sym, name: p.name || tenCua(p.sym), sector: p.sector || nganhCua(p.sym),
      entry: p.entry, entry_px: p.entry_px / 1000, last: px, sh: p.sh || null,
      cost_px: (p.cost_px || p.entry_px * (1 + PHI_MUA)) / 1000,
      pnl: ((val1 * (1 - PHI_BAN)) / ((p.cost_px || p.entry_px * (1 + PHI_MUA)) / 1000) - 1) * 100,
      tien: p.sh ? p.sh * val1 * 1000 : null,
      navGoc: (F && F.nav) || null,
      held: p.held, peak: (p.peak || 0) * 100, light: p.light, nguon: 'auto', live: true,
    });
  });
  manualGop().trades.filter(t => !t.sell_px).forEach(t => {
    if (an.has(String(t.sym).toUpperCase())) return;
    const px = giaMoiNhat(t.sym);
    out.push({
      book_id: 'MANUAL', sym: t.sym, name: tenCua(t.sym), sector: nganhCua(t.sym),
      entry: t.buy_d, entry_px: +t.buy_px, last: px, sh: t.sh || null,
      pnl: px ? laiSauPhi(t.buy_px, px) * 100 : null,
      tien: (t.sh && px) ? t.sh * px * 1000 : null,
      held: null, peak: null, light: null, navGoc: null,
      note: t.note || '', nguon: t.chuaDang ? 'nhap' : 'tay',
    });
  });
  out.sort((a, b) => String(b.entry).localeCompare(String(a.entry)));
  return out;
}

/* Sổ BACKTEST — ảnh chụp nghiên cứu, NAV riêng (1 tỷ từ 02/01/2019). Không bao giờ
   trộn với sổ hiện tại. */
function danhMucBacktest() {
  const nav = ((D.prod || {}).metrics || {}).final_nav || null;
  return (D.open_positions || []).map(p => {
    const px = giaMoiNhat(p.sym) || p.last;
    return { book_id: 'BACKTEST', sym: p.sym, sector: p.sector, entry: p.entry,
             entry_px: p.entry_px / 1000, last: px, sh: p.shares,
             tien: p.shares ? p.shares * px * 1000 : null, navGoc: nav,
             pnl: laiSauPhi(p.entry_px / 1000, px) * 100, nguon: 'backtest' };
  });
}

/* Tài khoản hiện tại = sổ LIVE_PAPER: NAV, tiền mặt, cổ phiếu — đúng một mẫu số. */
function taiKhoan() {
  const F = pfData() || {};
  const cp = danhMuc().filter(x => x.book_id === 'LIVE_PAPER' && x.tien).reduce((a, x) => a + x.tien, 0);
  const tien = F.cash != null ? F.cash : null;
  return { nav: (tien != null ? tien + cp : F.nav || null), nav0: F.nav0 || 1e9, cp, tien, book_id: 'LIVE_PAPER' };
}

function lichSuThat() {
  const out = [];
  const F = pfData();
  (F && F.closed || []).forEach(c => out.push({
    sym: c.sym, sector: c.sector || nganhCua(c.sym), entry: c.entry, exit: c.exit,
    entry_px: c.entry_px, exit_px: c.exit_px, pnl: c.pnl_pct, pnl_vnd: c.pnl_vnd,
    held: c.held, reason: c.reason, peak: c.peak, nguon: 'auto',
  }));
  manualGop().trades.filter(t => t.sell_px).forEach(t => out.push({
    sym: t.sym, sector: nganhCua(t.sym), entry: t.buy_d, exit: t.sell_d,
    entry_px: +t.buy_px, exit_px: +t.sell_px,
    pnl: laiSauPhi(t.buy_px, t.sell_px) * 100,
    pnl_vnd: t.sh ? Math.round(t.sh * ((+t.sell_px) * 1000 * (1 - PHI_BAN) - (+t.buy_px) * 1000 * (1 + PHI_MUA))) : null,
    held: null, reason: t.note || 'Anh Sơn tự đóng', peak: null,
    nguon: t.chuaDang ? 'nhap' : 'tay',
  }));
  out.sort((a, b) => String(b.exit).localeCompare(String(a.exit)));
  return out;
}

/* mã anh Sơn ghim tay ở Sổ tay — chảy vào Watchlist */
function ghimThuCong() {
  const G = manualGop();
  // Loại thắng ghim: một mã vừa ghim vừa loại thì không được hiện ở mục ghim
  // nữa, đúng như manual.py xử lý phía máy chủ.
  const bo = new Set((G.loai || []).map(w => String(w.sym).toUpperCase()));
  return G.watch.filter(w => !bo.has(String(w.sym).toUpperCase())).map(w => ({
    sym: w.sym, note: w.note || '', added: w.added || '', chuaDang: !!w.chuaDang,
    sector: nganhCua(w.sym), price: giaMoiNhat(w.sym),
    look: (D.lookup || {})[w.sym] || null,
  }));
}

/* mã anh Sơn loại tay ở Sổ tay — không bao giờ vào watchlist, không kêu chuông */
function loaiThuCong() {
  return (manualGop().loai || []).map(w => ({
    sym: w.sym, note: w.note || '', added: w.added || '', chuaDang: !!w.chuaDang,
    look: (D.lookup || {})[w.sym] || null,
  }));
}

/* dấu B / S vẽ trên biểu đồ nến — gộp backtest + sổ thật + sổ tay */
function dauMuaBan(sym) {
  const m = [];
  // Vị thế ĐANG MỞ của bộ máy — backtest chỉ ghi dấu cho lệnh đã đóng, nên nếu
  // thiếu chỗ này thì mã đang cầm không có chữ B nào trên biểu đồ. Đúng cái mã
  // quan trọng nhất lại là mã không thấy dấu.
  (D.open_positions || []).forEach(p => {
    if (p.sym === sym) m.push({ t: 'B', d: p.entry, px: (p.entry_px / 1000).toFixed(2) });
  });
  const F = pfData();
  (F && F.open || []).forEach(p => { if (p.sym === sym) m.push({ t: 'B', d: p.entry, px: (p.entry_px / 1000).toFixed(2) }); });
  (F && F.closed || []).forEach(c => {
    if (c.sym !== sym) return;
    m.push({ t: 'B', d: c.entry, px: c.entry_px });
    m.push({ t: 'S', d: c.exit, px: c.exit_px });
  });
  manualGop().trades.forEach(t => {
    if (t.sym !== sym) return;
    if (t.buy_d) m.push({ t: 'B', d: t.buy_d, px: t.buy_px });
    if (t.sell_d) m.push({ t: 'S', d: t.sell_d, px: t.sell_px });
  });
  return m;
}

/* bảng danh mục rút gọn — dùng chung cho trang Hiệu suất và trang Chuông báo,
   để ba trang không bao giờ nói khác nhau về cùng một chuyện */
function bangDanhMucNgan() {
  const dm = danhMuc();
  if (!dm.length) {
    const l = (D.regime[D.regime.length - 1] || {}).light;
    return `<p style="margin:0">Hệ thống đang giữ tiền mặt, không cầm mã nào.
      Đèn thị trường hiện <b style="color:var(${LIGHTVAR[l] || '--text-muted'})">${LIGHTNAME[l] || '—'}</b>.</p>`;
  }
  return `<div class="tblwrap"><table><thead><tr>
      <th>Mã</th><th>Ngành</th><th>Ngày mua</th><th style="text-align:right">Giá vốn</th>
      <th style="text-align:right">Hiện tại</th><th style="text-align:right">Số cổ</th>
      <th style="text-align:right">Giá trị</th><th style="text-align:right">Lãi/lỗ</th>
      <th>Nguồn</th></tr></thead><tbody>
      ${dm.map(p => `<tr><td class="sym">${esc(p.sym)}</td>
        <td class="muted" style="font-size:13px">${(p.sector || '').slice(0, 24)}</td>
        <td>${ddmm(p.entry)}</td>
        <td style="text-align:right">${(+p.entry_px).toFixed(2)}</td>
        <td style="text-align:right">${p.last != null ? (+p.last).toFixed(2) : '—'}</td>
        <td style="text-align:right" class="muted">${p.sh ? num(p.sh) : '—'}</td>
        <td style="text-align:right">${p.tien ? vnd(p.tien) : '—'}</td>
        <td style="text-align:right;font-weight:640" class="${p.pnl == null ? '' : cls(p.pnl)}">${
          p.pnl == null ? '—' : (p.pnl >= 0 ? '+' : '') + p.pnl.toFixed(2) + '%'}</td>
        <td>${nhanNguon(p.nguon)}</td></tr>`).join('')}
    </tbody></table></div>
    `;
}

/* ============================================================================
   TRANG DANH MỤC HỆ THỐNG
   ========================================================================== */
const tyd = x => (x / 1e9).toFixed(3).replace('.', ',') + ' tỷ';

function nhanNguon(n) {
  if (n === 'auto') return '<span class="tag B" style="margin-left:6px" title="Sổ LIVE_PAPER — portfolio.json">Sổ live (paper)</span>';
  if (n === 'backtest') return '<span class="tag A" style="margin-left:6px">Backtest</span>';
  if (n === 'nhap') return '<span class="tag A" style="margin-left:6px" title="Mới nhập trong máy anh, khách hàng chưa thấy — nhớ bấm Đăng lên trang">Chưa đăng</span>';
  return '<span class="tag C" style="margin-left:6px">Anh Sơn nhập</span>';
}

function pageSoLenh(root) {
  const F = pfData();
  const dm = danhMuc();
  const ls = lichSuThat();
  const M2 = manualData();
  const chuaDang = danhMuc().filter(x => x.nguon === 'nhap').length
                 + ghimThuCong().filter(x => x.chuaDang).length;
  const TK = taiKhoan();
  const nav = TK.nav;
  const nav0 = TK.nav0;
  const lai = nav ? nav / nav0 - 1 : null;
  const thang = ls.filter(c => c.pnl > 0);
  const thua = ls.filter(c => c.pnl <= 0);
  const tbT = thang.length ? thang.reduce((a, c) => a + c.pnl, 0) / thang.length : 0;
  const tbL = thua.length ? thua.reduce((a, c) => a + c.pnl, 0) / thua.length : 0;
  const nTay = dm.filter(x => x.nguon === 'tay').length;

  const bangMo = !dm.length
    ? `<div class="card"><p style="margin:0">Hệ thống đang giữ tiền mặt, không cầm mã nào.
       ${LIVEOK() ? '' : '<span class="muted">(Trang đang mở từ file trên máy nên chỉ thấy ảnh chụp tối qua.)</span>'}</p></div>`
    : `<div class="card tblwrap"><table><thead><tr>
        <th>Mã</th><th>Doanh nghiệp</th><th>Ngày mua</th><th style="text-align:right">Giá vốn</th>
        <th style="text-align:right">Hiện tại</th><th style="text-align:right">Số cổ</th>
        <th style="text-align:right">Giá trị</th><th style="text-align:right">% tài khoản</th>
        <th style="text-align:right">Lãi/lỗ</th>
        <th title="Luật thoát đã được dịch thành một việc phải làm">Việc cần làm</th>
        <th>Nguồn</th></tr></thead><tbody>
        ${dm.map(p => `<tr>
          <td class="sym">${esc(p.sym)}${((D.lookup||{})[p.sym]||{}).tim
            ? ` <span title="Đèn tím — ${((D.lookup||{})[p.sym]||{}).tim_vi||''}" style="color:var(--s7)">●</span>` : ''}</td>
          <td class="muted" style="font-size:13px">${(p.name || '').slice(0, 30)}</td>
          <td>${ddmm(p.entry)}</td>
          <td style="text-align:right">${(+p.entry_px).toFixed(2)}</td>
          <td style="text-align:right">${p.last != null ? (+p.last).toFixed(2) : '—'}</td>
          <td style="text-align:right" class="muted">${p.sh ? num(p.sh) : '—'}</td>
          <td style="text-align:right;font-weight:640">${p.tien ? vnd(p.tien) : '—'}</td>
          <td style="text-align:right" class="muted" title="${
            p.navGoc ? escA('Tính trên NAV của sổ sinh ra vị thế này: ' + tyd(p.navGoc)) : ''}">${
            (p.tien && p.navGoc) ? Math.round(100 * p.tien / p.navGoc) + '%' : '—'}</td>
          <td style="text-align:right;font-weight:660" class="${p.pnl == null ? '' : cls(p.pnl)}">${
            p.pnl == null ? '—' : (p.pnl >= 0 ? '+' : '') + p.pnl.toFixed(2) + '%'}</td>
          <td>${(() => { const v = vieccanlam(p);
            return `<span class="vclpill" style="color:var(${VCLMAU[v.m]});border-color:color-mix(in srgb,var(${VCLMAU[v.m]}) 45%,transparent)"
              title="${escA(v.ly)}">${v.v}</span>`; })()}</td>
          <td>${nhanNguon(p.nguon)}</td></tr>`).join('')}
      </tbody></table></div>
      `;

  const bangDong = !ls.length ? '' : `
    <h2>Vừa đóng</h2>
    
    <div class="card tblwrap"><table><thead><tr>
      <th>Mã</th><th>Mua</th><th>Bán</th><th style="text-align:right">Giá vốn</th>
      <th style="text-align:right">Giá bán</th><th style="text-align:right">Lãi/lỗ</th>
      <th style="text-align:right">Giữ</th><th>Lý do bán</th><th>Nguồn</th></tr></thead><tbody>
      ${ls.map(c => `<tr>
        <td class="sym">${esc(c.sym)}</td><td>${ddmm(c.entry)}</td><td>${ddmm(c.exit)}</td>
        <td style="text-align:right">${(+c.entry_px).toFixed(2)}</td>
        <td style="text-align:right">${(+c.exit_px).toFixed(2)}</td>
        <td style="text-align:right;font-weight:660" class="${cls(c.pnl)}">${c.pnl >= 0 ? '+' : ''}${c.pnl.toFixed(2)}%</td>
        <td style="text-align:right" class="muted">${c.held == null ? '—' : c.held + ' phiên'}</td>
        <td class="muted" style="font-size:12.5px">${esc(c.reason)}</td>
        <td>${nhanNguon(c.nguon)}</td></tr>`).join('')}
    </tbody></table></div>`;

  const nhatKy = !(F && F.log && F.log.length) ? '' : `
    <h2>Nhật ký</h2>
    
    <div class="card">${F.log.slice(0, 25).map(d => `
      <div style="display:flex;gap:14px;padding:8px 0;border-bottom:1px solid var(--line)">
        <b style="min-width:64px">${ddmm(d.date)}</b>
        <div>${(d.items || []).map(x => `<div>${x}</div>`).join('')}</div>
      </div>`).join('')}</div>`;

  root.innerHTML = `
  <h1>Danh mục hệ thống</h1>
  <p class="lead" style="margin-top:-4px">Sổ <b>LIVE_PAPER</b> (portfolio.json — sổ ghi tiến, vốn ${tyd(nav0)} từ ${ddmm((F && F.stats && F.stats.since) || '')}) + lệnh anh nhập tay.
    Vị thế của backtest dùng NAV khác nên <b>không</b> nằm trong bảng này.${
    (F && F.checks) ? (F.checks.ok ? ' <span class="tag B">Đối soát sổ: đạt</span>' : ' <span class="tag A">Đối soát sổ: TRƯỢT</span>') : ''}</p>

  <div class="grid kpis">
    ${kpi('Đang nắm giữ', `${dm.length} mã`, nTay ? `${dm.length - nTay} do hệ thống · ${nTay} anh nhập` : 'toàn bộ do hệ thống vào')}
    ${kpi('Giá trị cổ phiếu', TK.cp ? vnd(TK.cp) : '—', nav ? `${Math.round(100 * TK.cp / nav)}% tài khoản` : '')}
    ${nav != null ? kpi('Giá trị tài khoản', tyd(nav), `sổ LIVE_PAPER · xuất phát ${tyd(nav0)}`) : ''}
    ${nav != null ? kpi('Tiền mặt', tyd(TK.tien), `${Math.round(100 * TK.tien / nav)}% tài khoản`) : ''}
    ${lai != null ? kpi('Lãi/lỗ tổng', (lai >= 0 ? '+' : '') + (lai * 100).toFixed(1) + '%', 'sổ LIVE_PAPER', cls(lai)) : ''}
    ${kpi('Đèn thị trường', LIGHTNAME[(D.regime[D.regime.length - 1] || {}).light] || '—', 'phiên gần nhất')}
  </div>

  ${chuaDang ? `` : ''}

  ${ls.length ? `` : ''}

  <h2>Đang nắm giữ</h2>
  ${bangMo}
  ${bangDong}
  ${nhatKy}

  `;
}
