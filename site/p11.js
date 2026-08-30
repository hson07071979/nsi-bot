/* ============================================================================
   LỚP TRỰC TIẾP — trang tự đọc live.json và tự cập nhật, không cần ai bấm gì.

   live.json do workflow "Quét trong phiên" trong repo public ghi ra, mỗi 20 phút
   trong giờ giao dịch. Trang này đọc lại mỗi 60 giây.

   Khi mở file bằng đường dẫn file:// trên máy (không qua web thật) thì không có
   live.json — trang tự lùi về ảnh chụp tối qua và nói rõ điều đó, không báo lỗi.
   ========================================================================== */
const LIVE = {
  data: null,
  server: null,           // bản máy chủ quét (live.json) — giữ riêng để đối chiếu
  rtOn: false,            // lớp real-time có đang chạy không
  seen: new Set(),          // các mã đã kêu chuông rồi, khỏi kêu lại
  timer: null,
  firstLoad: true,
};

const LVNAME = { MUA: 'ĐỦ ĐIỂM MUA', SAP_DU: 'SẮP ĐỦ', DE_MAT: 'ĐỂ MẮT', THEO_DOI: 'ĐANG ĐỘNG ĐẬY' };

function hhmm(iso) {
  if (!iso) return '';
  const m = String(iso).match(/T(\d{2}:\d{2})/);
  return m ? m[1] : '';
}
function ddmm(d) {
  if (!d) return '';
  const p = String(d).split('-');
  return p.length === 3 ? `${p[2]}/${p[1]}` : d;
}

/* ---------- hai tiếng chuông khác nhau, tạo bằng Web Audio ----------
   Chuông MUA kêu hai tiếng cao, dứt khoát — nghe là biết phải hành động.
   Chuông ĐỂ MẮT chỉ một tiếng trầm, nhẹ — để ngó chừng, không phải lệnh.     */
function keng(loai) {
  try {
    const A = new (window.AudioContext || window.webkitAudioContext)();
    const notes = loai === 'mua'
      ? [{ f: 880, t: 0, v: 0.28, d: 0.5 }, { f: 1180, t: 0.18, v: 0.28, d: 0.5 }]
      : [{ f: 560, t: 0, v: 0.15, d: 0.42 }];
    notes.forEach(n => {
      const o = A.createOscillator(), g = A.createGain();
      o.connect(g); g.connect(A.destination);
      o.type = 'sine';
      o.frequency.setValueAtTime(n.f, A.currentTime + n.t);
      g.gain.setValueAtTime(0.0001, A.currentTime + n.t);
      g.gain.exponentialRampToValueAtTime(n.v, A.currentTime + n.t + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, A.currentTime + n.t + n.d);
      o.start(A.currentTime + n.t);
      o.stop(A.currentTime + n.t + n.d + 0.05);
    });
  } catch (e) { /* trình duyệt chặn âm thanh khi chưa ai bấm gì — bỏ qua */ }
}

/* ---------- thanh trạng thái trên đỉnh trang ---------- */
/* ============================================================================
   CẢNH BÁO SỐ LIỆU NỀN ĐÃ CŨ

   Vì sao phải có. Trang này trộn HAI loại số:
     · giá/khối lượng/nến  — tự lấy mới mỗi lần mở trang, không bao giờ cũ
     · ngưỡng, điểm CANSLIM, watchlist, backtest — ảnh chụp, do dây chuyền
       19h30 dựng lại mỗi tối

   Nếu dây chuyền 19h30 chết (hết hạn token, GitHub đổi thứ gì đó, mạng lỗi),
   trang VẪN mở bình thường và giá VẪN nhấp nháy real-time — nhìn y như đang
   chạy tốt. Nhưng ngưỡng thì của tuần trước, và bot sẽ báo mua theo giá cũ.
   Đó là kiểu hỏng nguy hiểm nhất: hỏng mà không ai biết là đang hỏng.

   Nên trang phải tự tố cáo chính nó. Đếm số ngày làm việc từ phiên nền tới nay,
   quá 3 phiên là kêu to.
   ========================================================================== */
function phienLamViecTu(iso) {
  if (!iso) return 999;
  const a = new Date(iso + 'T00:00:00'), b = new Date();
  let n = 0;
  for (let t = new Date(a); t < b; t.setDate(t.getDate() + 1)) {
    const d = t.getDay();
    if (d !== 0 && d !== 6) n++;
  }
  return n - 1;                       // chính phiên nền không tính là trễ
}

function bangSoLieuCu() {
  const tre = phienLamViecTu(D.asof);
  if (tre <= 3) return '';            // nghỉ lễ dài vẫn có thể trễ 2-3 phiên
  const nang = tre > 7;
  return ``;
}

function renderLiveBar() {
  const el2 = document.getElementById('liveBar');
  if (!el2) return;
  const L = LIVE.data;

  if (!L) {
    el2.className = 'livebar off';
    el2.innerHTML = `<span class="ldot"></span><span>Bản chụp phiên ${ddmm(D.asof)}</span>
      <span class="lmuted">— trang đang mở từ file trên máy nên không có dữ liệu trong phiên</span>`;
    return;
  }

  const mua = L.hits.filter(h => h.level === 'MUA');
  const sap = L.hits.filter(h => h.level === 'SAP_DU');

  if (mua.length) {
    el2.className = 'livebar alert';
    el2.innerHTML = `<span class="ldot"></span>
      <b>${mua.length} mã đủ điểm mua</b>
      <span>${mua.map(h => h.sym).join(' · ')}</span>
      <span class="lmuted">cập nhật ${hhmm(L.asof)}${L.realtime ? ' (real-time)' : ''} · phiên ${ddmm(L.session)}</span>
      <button class="mini" onclick="go('chuong')">Xem chi tiết</button>`;
    return;
  }

  const dm = L.hits.filter(h => h.level === 'DE_MAT');
  if (dm.length) {
    el2.className = 'livebar heads';
    el2.innerHTML = `<span class="ldot"></span>
      <b>${dm.length} mã đang tăng mạnh</b>
      <span>${dm.map(h => `${esc(h.sym)} ${h.pct >= 0 ? '+' : ''}${h.pct}%`).join(' · ')}</span>
      <span class="lmuted">chỉ để mắt, chưa phải lệnh · ${hhmm(L.asof)}</span>
      <button class="mini" onclick="go('chuong')">Xem</button>`;
    return;
  }

  const rt = L.realtime ? ' <b style="color:var(--good)">· real-time</b>' : '';
  const trangthai = (L.open || L.realtime)
    ? `Đang theo dõi phiên ${ddmm(L.session)}${L.frac ? ` · đã đi ${Math.round(L.frac * 100)}%` : ''}${rt}`
    : `Phiên ${ddmm(L.session)} đã đóng cửa${rt}`;
  el2.className = 'livebar ' + (L.open || L.realtime ? 'on' : 'off');
  el2.innerHTML = `<span class="ldot"></span><span>${trangthai}</span>
    <span class="lmuted">quét ${L.scanned}/${L.universe || '—'} mã lúc ${hhmm(L.asof)}${
      sap.length ? ` · ${sap.length} mã sắp đủ` : ' · chưa có mã nào đủ điều kiện'}</span>`;
}

/* ---------- băng nổi lên: đỏ = mua, vàng = để mắt ---------- */
function bangBao(list, loai) {
  const box = document.getElementById('liveToast');
  if (!box) return;
  const mua = loai === 'mua';
  box.innerHTML = `
    <div class="toastin ${mua ? '' : 'heads'}">
      <div class="tttl">${mua
        ? `🔴 ${list.length} mã vừa đủ điểm mua`
        : `🟡 ${list.length} mã trong watchlist đang tăng mạnh`}</div>
      ${mua ? '' : '<div class="tsub">Chỉ để anh ngó chừng — chưa đủ điều kiện vào lệnh.</div>'}
      ${list.map(h => `<div class="trow"><b>${esc(h.sym)}</b> ${h.price}
        <span class="${h.pct >= 0 ? 'pos' : 'neg'}">${h.pct >= 0 ? '+' : ''}${h.pct}%</span>
        <span class="lmuted">vol ${h.volr}×${mua ? ` · GTGD ${h.gtgd} tỷ` : ''} · điểm ${h.score}${
          h.fa ? ' · chưa đạt cơ bản' : ''}</span></div>`).join('')}
      <div class="tact">
        <button class="btn" onclick="go('chuong');dongToast()">Xem chuông báo</button>
        <button class="btn ghost" onclick="dongToast()">Đóng</button>
      </div>
    </div>`;
  box.classList.add('on');
  keng(loai);
}
function dongToast() {
  const b = document.getElementById('liveToast');
  if (b) b.classList.remove('on');
}

/* ============================================================================
   BỘ NẠP DỮ LIỆU SỐNG — bốn file, một nhịp.

     config.json     địa chỉ cầu nối real-time + tên repo. Đọc một lần.
     live.json       kết quả quét của máy chủ (mỗi 10–20 phút)
     portfolio.json  sổ lệnh máy chủ tự ghi (mỗi phiên một lần)
     manual.json     sổ tay anh Sơn đăng lên

   Thiếu file nào thì lùi về ảnh chụp nhúng sẵn trong trang, KHÔNG báo lỗi đỏ lòm
   cho khách hàng xem. Mở bằng file:// trên máy vẫn đọc được ảnh chụp.
   ========================================================================== */
async function docJSON(ten) {
  try {
    const r = await fetch(ten + '?t=' + Date.now(), { cache: 'no-store' });
    if (!r.ok) return null;
    return await r.json();
  } catch (e) { return null; }
}

/* Đánh dấu một trang là "số liệu đã cũ, phải vẽ lại".
   Lỗi từng gặp: sửa sổ tay ở tab Sổ tay xong bấm sang tab Danh mục thì vẫn thấy
   bảng cũ — vì bộ điều hướng chỉ vẽ một lần rồi thôi. Trang đang mở thì vẽ lại
   ngay; trang đang ẩn thì xoá cờ để lần sau mở tới nó vẽ lại từ đầu. */
function veLaiTrang(id) {
  const s = (typeof secs !== 'undefined') && secs[id];
  if (!s || !s.rendered) return;
  s.node.innerHTML = '';
  if (s.node.classList.contains('on')) s.fn(s.node);
  else s.rendered = false;
}

async function napSo() {
  const [pf, mn] = await Promise.all([docJSON('portfolio.json'), docJSON('manual.json')]);
  if (pf) NSI.pf = pf;
  if (mn) NSI.manual = mn;
  veLaiTrang('danhmuc');
  veLaiTrang('watchlist');
}

/* ---------- nạp live.json ---------- */
async function napLive() {
  const L = await docJSON('live.json');
  if (!L) {
    if (!LIVE.rtOn) { LIVE.data = null; LIVE.firstLoad = false; renderLiveBar(); }
    return;
  }
  LIVE.server = L;
  // Khi lớp real-time đang chạy thì nó mới là nguồn chính. live.json của máy chủ
  // trễ 10–20 phút; để nó ghi đè lên số real-time là bảng nhảy lùi về quá khứ.
  if (LIVE.rtOn) return;
  LIVE.data = L;

  // Mã nào MỚI so với lần nạp trước? Hai loại đếm riêng, chuông đỏ ưu tiên.
  const key = (h, k) => k + ':' + h.sym + ':' + L.session;
  const mua = (L.hits || []).filter(h => h.level === 'MUA');
  const dm  = (L.hits || []).filter(h => h.level === 'DE_MAT');
  const muaMoi = mua.filter(h => !LIVE.seen.has(key(h, 'M')));
  const dmMoi  = dm.filter(h => !LIVE.seen.has(key(h, 'D')));
  mua.forEach(h => LIVE.seen.add(key(h, 'M')));
  dm.forEach(h => LIVE.seen.add(key(h, 'D')));

  // Lần nạp đầu tiên không kêu chuông — tránh giật mình khi vừa mở trang.
  if (!LIVE.firstLoad) {
    if (muaMoi.length) bangBao(muaMoi, 'mua');
    else if (dmMoi.length) bangBao(dmMoi, 'demat');
  }
  LIVE.firstLoad = false;
  renderLiveBar();
  veLaiTrang('chuong');
}

/* ============================================================================
   LỚP REAL-TIME — trình duyệt tự hỏi thẳng FireAnt, không chờ máy chủ.

   Vì sao phải có cầu nối: FireAnt không gửi kèm nhãn CORS nên trình duyệt bị
   chặn khi gọi thẳng. Cầu nối là một Worker mười mấy dòng trên Cloudflare, nhận
   một danh sách mã, hỏi FireAnt hộ, rồi trả về kèm nhãn cho phép. Đo được: một
   vòng khoảng 1 giây, chạy 45 giây một lần — tức trễ dưới một phút, không phải
   10–20 phút như lịch của GitHub.

   Không có cầu nối thì lớp này tự tắt, trang vẫn chạy bằng live.json như cũ.
   Địa chỉ cầu nối đặt trong config.json để đổi mà không phải dựng lại trang.
   ========================================================================== */
const RT = { timer: null, dang: false, loi: 0 };

function maCanTheoDoi() {
  const L = D.lookup || {};
  const s = new Set();
  Object.keys(L).forEach(k => { if (L[k].state === 'cho' || L[k].state === 'fa') s.add(k); });
  danhMuc().forEach(p => s.add(p.sym));                 // mã đang cầm phải có giá mới
  ((LIVE.data || {}).hits || []).forEach(h => s.add(h.sym));
  return [...s].slice(0, 60);                           // đủ dùng, đừng làm phiền cầu nối
}

async function napRealtime() {
  const cfg = cfgData();
  if (!cfg.proxy || RT.dang) return;
  const syms = maCanTheoDoi();
  if (!syms.length) return;
  RT.dang = true;
  try {
    const u = cfg.proxy.replace(/\/+$/, '') + '/quotes?syms=' + syms.join(',');
    const r = await fetch(u, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    const j = await r.json();
    NSI.rt = j.rows || {};
    // Giờ trả về là giờ quốc tế. Đổi sang giờ máy người xem rồi mới hiển thị,
    // không thì thanh trạng thái ghi lệch 7 tiếng.
    const t = new Date(j.at || Date.now());
    NSI.rtAt = new Date(t.getTime() - t.getTimezoneOffset() * 60000)
      .toISOString().slice(0, 19);
    LIVE.rtOn = true;
    RT.loi = 0;
    tinhLaiTinHieu();
    renderLiveBar();
    veLaiTrang('danhmuc');
    veLaiTrang('chuong');
  } catch (e) {
    RT.loi++;
    // Cầu nối hỏng bốn nhịp liên tiếp thì thôi, lùi về đọc live.json của máy chủ.
    if (RT.loi >= 4 && RT.timer) {
      clearInterval(RT.timer); RT.timer = null;
      LIVE.rtOn = false;
      if (LIVE.server) { LIVE.data = LIVE.server; renderLiveBar(); veLaiTrang('chuong'); }
    }
  } finally {
    RT.dang = false;
  }
}

/* Tính lại bốn điều kiện của phiên ngay trong trình duyệt, đúng bằng công thức
   máy chủ dùng. Ngưỡng lấy từ ô tra cứu đã nhúng sẵn trong trang (cập nhật mỗi
   tối), nên không cần tải thêm gì.                                            */
function tinhLaiTinHieu() {
  const R = NSI.rt || {};
  const L = D.lookup || {};
  const hits = [];
  Object.keys(R).forEach(sym => {
    const t = L[sym], r = R[sym];
    if (!t || !r || !r.price || !r.ref) return;
    if (t.state !== 'cho' && t.state !== 'fa') return;
    const pct = r.price / r.ref - 1;
    const volr = t.vma20 ? r.vol / t.vma20 : 0;
    // Điều kiện 7 — cỡ lệnh mua so cỡ lệnh bán. Phải có, không thì lớp real-time
    // báo mua những phiên mà bộ máy chín lớp vốn không đụng tới, và Danh mục hệ
    // thống sẽ lệch với sổ chạy của bộ máy.
    const bavg = r.bc > 0 ? r.bq / r.bc : 0;
    const savg = r.sc > 0 ? r.sq / r.sc : 0;
    const oi = savg > 0 ? bavg / savg : 0;
    const oiMin = (LIVE.server && LIVE.server.ordimb_min) || 1.20;
    const cond = {
      'Biên độ tăng giá': pct * 100 >= t.thr,
      'Khối lượng ≥ 2× TB20': r.vol >= t.need_vol,
      'GTGD ≥ 15 tỷ': r.tv >= 15e9,
      'Đóng cửa nửa trên nến': r.hi > r.lo ? r.price >= (r.hi + r.lo) / 2 : true,
      [`Cỡ lệnh mua ≥ ${oiMin.toFixed(2)}× cỡ lệnh bán`]: oi >= oiMin,
    };
    const n = Object.values(cond).filter(Boolean).length;
    const cho = t.state === 'cho';
    let lvl = null;
    if (cho && n === 5) lvl = 'MUA';
    else if (cho && n >= 4) lvl = 'SAP_DU';
    else if (pct * 100 >= (LIVE.data || {}).de_mat_pct || pct * 100 >= 2.5) lvl = 'DE_MAT';
    else if (cho && (volr >= 1.5 || pct * 100 >= t.thr * 0.5)) lvl = 'THEO_DOI';
    if (!lvl) return;
    hits.push({
      sym, name: t.name, level: lvl, fa: t.state === 'fa',
      price: +(r.price / 1000).toFixed(2), ref: +(r.ref / 1000).toFixed(2),
      pct: +(pct * 100).toFixed(2), need_px: t.need_px,
      volr: +volr.toFixed(2), volr_proj: +volr.toFixed(2), need_vol: t.need_vol,
      vol: r.vol, gtgd: +(r.tv / 1e9).toFixed(1), gtgd_proj: +(r.tv / 1e9).toFixed(1),
      score: t.score, base: t.base, ordimb: +oi.toFixed(2), ordimb_min: oiMin, cond,
      miss: Object.keys(cond).filter(k => !cond[k]),
    });
  });
  const order = { MUA: 0, SAP_DU: 1, DE_MAT: 2, THEO_DOI: 3 };
  hits.sort((a, b) => order[a.level] - order[b.level] || b.pct - a.pct);

  const cu = LIVE.server || LIVE.data || {};
  const mau = Object.values(R)[0] || {};
  const ses = mau.d || cu.session || D.asof;
  const truoc = new Set((cu.hits || []).filter(h => h.level === 'MUA').map(h => h.sym));
  LIVE.data = Object.assign({}, cu, {
    hits, session: ses, asof: NSI.rtAt, realtime: true,
    scanned: Object.keys(R).length, universe: cu.universe || Object.keys(L).length,
    n_mua: hits.filter(h => h.level === 'MUA').length,
    n_de_mat: hits.filter(h => h.level === 'DE_MAT').length,
  });
  // chuông cho mã VỪA đủ điểm mua trong nhịp này
  const moi = hits.filter(h => h.level === 'MUA' && !truoc.has(h.sym)
                            && !LIVE.seen.has('M:' + h.sym + ':' + ses));
  hits.filter(h => h.level === 'MUA').forEach(h => LIVE.seen.add('M:' + h.sym + ':' + ses));
  if (!LIVE.firstLoad && moi.length) bangBao(moi, 'mua');
}

function batDauLive() {
  (async () => {
    const c = await docJSON('config.json');
    if (c) NSI.cfg = c;
    await Promise.all([napLive(), napSo()]);
    // Lớp real-time VPS không cần cầu nối nào cả — bật thẳng.
    // Cầu nối Cloudflare (nếu anh Sơn có dựng) giờ chỉ còn dùng để lấy nến
    // cho trang Chi tiết mã, không còn là điều kiện để có giá real-time.
    if (typeof docCaiDat === 'function') docCaiDat();
    if (typeof batRealtimeVPS === 'function') batRealtimeVPS();
  })();
  if (LIVE.timer) clearInterval(LIVE.timer);
  LIVE.timer = setInterval(() => { napLive(); napSo(); }, 120000);
  // quay lại tab thì nạp ngay, khỏi chờ hết chu kỳ
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { napLive(); napSo(); if (typeof napVPS === 'function') napVPS(); }
  });
}

/* ============================================================================
   TRANG CHUÔNG BÁO — bản trực tiếp, vẽ từ live.json
   ========================================================================== */
function pageLiveTrucTiep(root, L) {
  // Chuan hoa TRUOC khi ve. live.json den tu may chu khac (repo public, workflow
  // rieng) nen co the thieu truong — mot ban live.json cu hoac hong khong duoc
  // phep lam trang trang. Da vap: `h.miss.length` no khi live.json thieu `miss`.
  L = L || {};
  L.hits = (L.hits || []).map(h => Object.assign({
    sym: '?', name: '', level: 'THEO_DOI', price: null, pct: 0, volr: 0, gtgd: 0,
    score: 0, miss: [], need_px: null, need_vol: null, ordimb: null, fa: false,
  }, h || {}));
  const last = D.regime[D.regime.length - 1];
  const mua = L.hits.filter(h => h.level === 'MUA');
  const sap = L.hits.filter(h => h.level === 'SAP_DU');
  const dem = L.hits.filter(h => h.level === 'DE_MAT');
  const theo = L.hits.filter(h => h.level === 'THEO_DOI');
  const smul = { XANH: 1.0, VANG: 0.6, CAM: 0.35, DO: 0.2 }[last.light];

  const bang = (list, tieude, mota) => !list.length ? '' : `
    <h2>${tieude}</h2>
    
    <div class="card tblwrap"><table><thead><tr>
      <th>Mã</th><th>Doanh nghiệp</th><th style="text-align:right">Giá</th>
      <th style="text-align:right">%</th><th style="text-align:right">Cần đạt</th>
      <th style="text-align:right">Vol/TB20</th><th style="text-align:right">GTGD</th>
      <th style="text-align:right" title="Cỡ lệnh mua ÷ cỡ lệnh bán — trên 1,20 là tổ chức đang gom">Dòng tiền</th>
      <th style="text-align:right">Điểm</th><th>Còn thiếu</th></tr></thead><tbody>
      ${list.map(h => `<tr>
        <td class="sym">${esc(h.sym)}</td>
        <td class="muted" style="font-size:13px">${(h.name || '').slice(0, 34)}</td>
        <td style="text-align:right">${h.price}</td>
        <td style="text-align:right;font-weight:660" class="${h.pct >= 0 ? 'pos' : 'neg'}">${h.pct >= 0 ? '+' : ''}${h.pct}%</td>
        <td style="text-align:right" class="muted">≥ ${h.need_px}</td>
        <td style="text-align:right">${h.volr}×${L.open && h.volr_proj !== h.volr ? ` <span class="muted">→${h.volr_proj}×</span>` : ''}</td>
        <td style="text-align:right">${h.gtgd} tỷ</td>
        <td style="text-align:right" class="${h.ordimb == null ? 'muted' : (h.ordimb >= (h.ordimb_min || 1.2) ? 'pos' : 'neg')}">${
          h.ordimb == null ? '—' : h.ordimb.toFixed(2) + '×'}</td>
        <td style="text-align:right;color:var(--text-primary);font-weight:640">${h.score}</td>
        <td class="muted" style="font-size:12.5px">${h.fa ? '<b style="color:var(--warn)">chưa đạt cơ bản — không mua</b> · ' : ''}${h.miss.length ? h.miss.join(' · ') : '—'}</td>
      </tr>`).join('')}
    </tbody></table></div>`;

  root.innerHTML = `
  <h1>Hệ thống hôm nay</h1>
  ${bangSoLieuCu()}
  ${typeof bangDieuKhienChuong === 'function' ? bangDieuKhienChuong() : ''}

  <div class="card" style="display:flex;gap:26px;align-items:center;flex-wrap:wrap;margin-bottom:14px">
    <div><div class="muted" style="text-transform:uppercase;letter-spacing:.06em;font-weight:600;font-size:12px">Đèn thị trường</div>
      <div style="font-size:34px;font-weight:750;color:var(${LIGHTVAR[last.light]})">${LIGHTNAME[last.light].toUpperCase()}</div>
      <div class="muted">Cỡ vị thế ${Math.round(smul * 100)}% — tức ${(42 * smul).toFixed(1)}% NAV mỗi lệnh</div></div>
    <div style="border-left:1px solid var(--line);padding-left:26px;display:grid;gap:6px">
      <div><span class="muted">G1 · chỉ số đều trọng số so MA200</span><br>
        <b class="${last.g1 >= (last.g1ma || 0) ? 'pos' : 'neg'}">${last.g1ma ? (last.g1 >= last.g1ma ? 'trên' : 'dưới') : '—'}</b></div>
      <div><span class="muted">G2 · VN-Index so MA50</span><br>
        <b class="${last.vni >= (last.vma50 || 0) ? 'pos' : 'neg'}">${last.vma50 ? (last.vni >= last.vma50 ? 'trên' : 'dưới') : '—'} ${last.vma50 ? last.vma50.toFixed(0) : ''}</b></div>
      <div><span class="muted">G3 · ngày phân phối / 25 phiên</span><br>
        <b class="${last.dd >= 5 ? 'neg' : last.dd >= 3 ? '' : 'pos'}">${last.dd}</b>
        <span class="muted"> · độ rộng ${pct(last.br50, 0)} số mã trên MA50</span></div>
    </div>
    <div style="border-left:1px solid var(--line);padding-left:26px">
      <div class="muted" style="text-transform:uppercase;letter-spacing:.06em;font-weight:600;font-size:12px">Tín hiệu</div>
      <div style="font-size:34px;font-weight:750;color:${mua.length ? 'var(--critical)' : 'var(--text-muted)'}">${mua.length}</div>
      <div class="muted">${sap.length} sắp đủ · ${dem.length} để mắt · ${theo.length} động đậy</div>
    </div>
  </div>

  ${mua.length ? bang(mua, '🔴 Đủ điểm mua', '')
    : '<h2>🔴 Đủ điểm mua</h2><p class="muted" style="margin-top:0">Chưa có mã nào.</p>'}

  ${bang(sap, '🟠 Sắp đủ', L.open
      ? 'Còn thiếu một bước, hoặc dự phóng cho thấy sẽ đạt lúc đóng cửa. Cột Vol/TB20 hiện <b>giá trị hiện tại → dự phóng cuối phiên</b>.'
      : 'Còn thiếu một bước tại thời điểm đóng cửa.')}

  ${bang(dem, '🟡 Để mắt — đang tăng mạnh',
      `Mã trong watchlist đang tăng từ <b>${L.de_mat_pct || 2.5}%</b> trở lên. Đây <b>chưa phải lệnh</b> — chỉ để anh ngó chừng xem nó có đi tiếp thành phiên bùng nổ không. Nguyên tắc vào lệnh không đổi.`)}

  ${bang(theo, '🟡 Đang động đậy', 'Đã qua mọi cổng nhưng còn xa điểm mua. Để đây theo dõi.')}

  `;
}
