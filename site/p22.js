/* ============================================================================
   LỆNH HARD — anh Sơn chủ động mua / bán trên DANH MỤC HỆ THỐNG (28/10/2026)

   Chỉ hiện trong Sổ tay (trang quản trị — trang khách bị cổng chặn #sotay).
   Bấm nút → hộp xác nhận → ghi thẳng khoá `hard` của manual.json lên repo trang
   (cùng mã truy cập GitHub của Sổ tay). Không có file nào khác phải tải lên.

   Đi đâu sau khi ghi:
     • Workflow "Báo lệnh Hard" của repo trang bắn Telegram + ntfy ngay (cùng kênh lệnh MUA).
     • Bản dựng tối (nsi-bot) chạy lại bộ máy từ 2019 kèm lệnh này: sổ hệ thống mua/bán đúng
       phiên, đúng giá anh điền; sổ ghi tiến làm theo. Có lệnh mới là bản dựng tự chạy lại,
       kể cả khi trang đã dựng xong phiên đó.
     • Hoàn tác được cho tới khi bản dựng đã xử lý lệnh (id có trong thresholds.hard.seen).

   Luật (anh Sơn chốt 27–28/10, xem hard.py bên nsi-bot):
     Mua: % NAV hiện tại của sổ hệ thống, vẫn bị chặn bởi trần mỗi mã, trần tổng vốn,
          trần ngành, tiền mặt, số mã tối đa. Mã đang cầm thì mua thêm, giá vốn bình quân.
     Bán: 25/50/100% vị thế, làm tròn xuống lô 100 cp, còn dưới 100 cp thì bán hết.
          Hàng chưa về (T+sell_from) thì khoá nút.
     Giá: phải nằm trong biên độ trần/sàn của phiên (tính từ dữ liệu của chính trang — hardBienDo).
     Phiên: từ 8h45 ngày thường là phiên hôm nay; trước 8h45 hoặc cuối tuần là phiên gần nhất
            (lệnh bấm sau giờ đóng cửa tính vào phiên hôm đó).
   ========================================================================== */

const HARD_PHAN = [[0.25, '25%'], [0.5, '50%'], [1, '100%']];

function _hardHomNay() {
  const v = gioVN();
  return v.getFullYear() + '-' + String(v.getMonth() + 1).padStart(2, '0') + '-' + String(v.getDate()).padStart(2, '0');
}

/* Phiên của lệnh bấm lúc này. */
function hardPhien() {
  const v = gioVN(), d = v.getDay(), p = v.getHours() * 60 + v.getMinutes();
  const homNay = _hardHomNay();
  if (d !== 0 && d !== 6 && p >= 8 * 60 + 45) return homNay;
  const lv = (typeof LIVE !== 'undefined' && LIVE.server && LIVE.server.session) ? String(LIVE.server.session) : '';
  const a = String(D.asof || '');
  const ganNhat = lv > a ? lv : a;
  return ganNhat && ganNhat <= homNay ? ganNhat : homNay;
}

/* Số phiên từ ngày mua tới phiên của lệnh (T+n). Phiên sau ngày dựng trang = phiên kế tiếp. */
function hardSoPhien(tu, phien) {
  const ds = (D.prod && D.prod.curve) ? D.prod.curve.map(c => c[0]) : [];
  const vt = x => { let lo = 0, hi = ds.length - 1, k = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (ds[m] <= x) { k = m; lo = m + 1; } else hi = m - 1; } return k; };
  const a = vt(tu);
  if (a < 0) return null;
  if (phien <= String(D.asof || '')) return vt(phien) - a;
  return ds.length - 1 - a + 1;
}

function hardSellFrom() {
  const c = D.cfg_prod || {};
  return +(c.sell_from || c.hs_from || 3);
}

/* Trần / sàn của phiên lệnh — lấy từ CHÍNH dữ liệu của Nguyễn Sơn Invest, không gọi nguồn ngoài:
     1. lớp real-time của trang (NSI.rt — đã có trần/sàn/tham chiếu của phiên đang chạy), nếu phiên
        của lệnh là phiên real-time đang hiện;
     2. không thì khối D.ma_gia của bản dựng (mọi mã HOSE/HNX): tham chiếu = PriceBasic nếu lệnh
        thuộc phiên của bản dựng, = giá đóng cửa phiên đó nếu lệnh thuộc phiên sau; trần/sàn theo
        biên độ sàn (HOSE 7%, HNX 10%) và bước giá của trang (buocGia).
   Mã không có trong dữ liệu (UPCoM, đã huỷ niêm yết…) -> không đặt được. Trả {tran, san, ref} nghìn đồng. */
function hardBienDo(sym, phien) {
  phien = phien || hardPhien();
  // mã phải có trong dữ liệu của bộ máy — không có thì bản dựng tối cũng từ chối
  const g = (D.ma_gia || {})[sym];
  if (!g) throw new Error(sym + ' không có trong dữ liệu Nguyễn Sơn Invest (chỉ có mã HOSE, HNX đang giao dịch)');
  let r = null; try { r = NSI.rt ? NSI.rt[sym] : null; } catch (e) { r = null; }
  const rtCuaPhien = (phien > String(D.asof || '')) ? rtPhienMoi() : !rtPhienMoi();
  if (r && r.tran > 0 && r.san > 0 && r.ref > 0 && rtCuaPhien)
    return { tran: r.tran / 1000, san: r.san / 1000, ref: r.ref / 1000, nguon: 'real-time của trang' };
  const ref = (phien <= String(D.asof || '') && g[0] > 0 ? g[0] : g[1]) * 1000, ex = g[2];
  const b = { HNX: 0.10, UPCOM: 0.15 }[String(ex || '').toUpperCase()] || 0.07;
  const hi = ref * (1 + b), lo = ref * (1 - b);
  const tran = Math.floor(+(hi / buocGia(hi, ex)).toFixed(6)) * buocGia(hi, ex);
  const san = Math.ceil(+(lo / buocGia(lo, ex)).toFixed(6)) * buocGia(lo, ex);
  return { tran: tran / 1000, san: san / 1000, ref: ref / 1000, nguon: 'bản dựng ' + ddmm(D.asof) };
}

/* Đọc manual.json đang ở repo (KHÔNG dùng bản nháp trong máy), sửa khoá hard, ghi lại. */
async function hardGhi(sua, moTa) {
  const repo = (cfgData().repo || '').trim();
  const token = (localStorage.getItem(NSI_TOKEN_KEY) || '').trim();
  if (!repo || !token) throw new Error('chưa nối GitHub — dán mã truy cập ở mục "Đăng lên trang khách hàng" bên dưới (một lần trên tên miền này)');
  const url = `https://api.github.com/repos/${repo}/contents/manual.json`;
  const H = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };
  for (let lan = 0; lan < 3; lan++) {
    const cur = await fetch(url + '?t=' + Date.now(), { headers: H, cache: 'no-store' });
    let sha, M = { v: 1, trades: [], watch: [], an: [], loai: [] };
    if (cur.ok) {
      const j = await cur.json(); sha = j.sha;
      const txt = new TextDecoder().decode(Uint8Array.from(atob(String(j.content || '').replace(/\s/g, '')), c => c.charCodeAt(0)));
      try { M = JSON.parse(txt); } catch (e) { throw new Error('manual.json trên repo đang hỏng — không ghi đè'); }
    } else if (cur.status !== 404) {
      throw new Error('đọc manual.json lỗi ' + cur.status);
    }
    M.hard = sua(Array.isArray(M.hard) ? M.hard.slice() : []);
    M.updated = new Date().toISOString().slice(0, 19);
    const noi = JSON.stringify(M, null, 1);
    const b64 = btoa(String.fromCharCode(...new TextEncoder().encode(noi)));
    const r = await fetch(url, { method: 'PUT', headers: H,
      body: JSON.stringify({ message: moTa + ' · ' + new Date().toLocaleString('vi-VN'), content: b64, sha: sha || undefined }) });
    if (r.ok) { NSI.manual = M; return M; }
    if (r.status === 409 || r.status === 422) continue;   // vừa có người ghi trước — đọc lại rồi ghi
    let m = r.status; try { m = (await r.json()).message || m; } catch (e) {}
    throw new Error(m + ' — thường là mã truy cập hết hạn hoặc thiếu quyền Contents: Read and write');
  }
  throw new Error('repo đang bận (ghi trùng) — thử lại sau vài giây');
}

/* Đọc manual.json qua API GitHub (tươi) — bản raw mà trang tải về bị đệm tới 5 phút, mở lại
   trang ngay sau khi đặt lệnh sẽ không thấy lệnh vừa đặt. Không có mã truy cập thì thôi. */
async function hardNapMoi() {
  const repo = (cfgData().repo || '').trim();
  let token = ''; try { token = (localStorage.getItem(NSI_TOKEN_KEY) || '').trim(); } catch (e) {}
  if (!repo || !token) return;
  try {
    const r = await fetch(`https://api.github.com/repos/${repo}/contents/manual.json?t=${Date.now()}`,
      { headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' }, cache: 'no-store' });
    if (!r.ok) return;
    const j = await r.json();
    const txt = new TextDecoder().decode(Uint8Array.from(atob(String(j.content || '').replace(/\s/g, '')), c => c.charCodeAt(0)));
    NSI.manual = JSON.parse(txt); NSI._manualTuApi = true;
    veHard();
  } catch (e) { /* giữ bản đang có */ }
}

function _hardId(sym) {
  const v = gioVN(), z = n => String(n).padStart(2, '0');
  return 'H' + v.getFullYear() + z(v.getMonth() + 1) + z(v.getDate()) + 'T' + z(v.getHours()) + z(v.getMinutes()) + z(v.getSeconds()) + '-' + sym;
}
function _hardLuc() {
  const v = gioVN(), z = n => String(n).padStart(2, '0');
  return v.getFullYear() + '-' + z(v.getMonth() + 1) + '-' + z(v.getDate()) + 'T' + z(v.getHours()) + ':' + z(v.getMinutes()) + ':' + z(v.getSeconds()) + '+07:00';
}

/* Các lệnh đang có + trạng thái theo bản dựng đang đăng. */
function hardDanhSach() {
  const tho = ((NSI.manual || D.manual || {}).hard) || [];
  const H = D.hard || {};
  const seen = new Set(H.seen || []);
  const fill = {}; (H.fills || []).forEach(f => fill[f.id] = f);
  const cho = {}; (H.pending || []).forEach(f => cho[f.id] = f);
  return tho.map(o => ({ o, f: fill[o.id] || null, seen: seen.has(o.id), cho: cho[o.id] || null }))
    .sort((a, b) => String(b.o.luc).localeCompare(String(a.o.luc)));
}

async function hardKhoaHoanTac(id) {
  // bản dựng mới nhất có thể vừa đăng sau khi trang này mở — hỏi lại thresholds.json
  const T = await docJSON('thresholds.json');
  return !!(T && T.hard && (T.hard.seen || []).includes(id));
}

function hardBao(h, ok) {
  const el = document.getElementById('hardmsg');
  if (el) el.innerHTML = `<div class="note${ok ? ' info' : ''}" style="margin-top:12px">${h}</div>`;
}

function veHard() {
  const box = document.getElementById('hardbox');
  if (!box) return;
  // Trang tự tải lại sổ mỗi 2 phút (napSo) và gọi lại hàm này — giữ nguyên chữ anh đang gõ dở
  // và dòng thông báo, không thì đang nhập giá thì ô bị xoá trắng.
  const giu = {};
  box.querySelectorAll('input,select').forEach(e => {
    const k = e.id || (e.dataset.hsp ? 'p:' + e.dataset.hsp : e.dataset.hsg ? 'g:' + e.dataset.hsg : '');
    if (k) giu[k] = e.value;
  });
  const _msg = (document.getElementById('hardmsg') || {}).innerHTML || '';
  const _f = document.activeElement && box.contains(document.activeElement)
    ? (document.activeElement.id || (document.activeElement.dataset.hsg ? 'g:' + document.activeElement.dataset.hsg : '')) : '';
  const phien = hardPhien(), sf = hardSellFrom();
  const B = D.book || {};
  const nav = +B.nav || ((D.prod || {}).metrics || {}).final_nav || 0;
  const op = (D.open_positions || []).slice().sort((a, b) => a.sym < b.sym ? -1 : 1);
  const bookPos = {}; (B.positions || []).forEach(q => bookPos[q.sym] = q);
  const ds = hardDanhSach();
  const choBan = new Set(ds.filter(x => !x.seen && !x.o.huy && x.o.loai === 'ban').map(x => x.o.sym));

  const dongBan = op.map(p => {
    const n = hardSoPhien(p.entry, phien);
    const bp = bookPos[p.sym] || {};
    const adds = (bp.adds || []).filter(a => { const k = hardSoPhien(a[0], phien); return k == null || k < sf; });
    const chuaVe = adds.reduce((s, a) => s + (+a[1] || 0), 0);
    const ve = n != null && n >= sf;
    const gt = bp.value != null ? bp.value : (p.shares && p.last ? p.shares * p.last : null);
    const tt = nav && gt ? gt / nav * 100 : null;
    const khoa = !ve ? `hàng về từ T+${sf} (đang T+${n == null ? '?' : n})` : '';
    return `<tr><td class="sym">${esc(p.sym)}${p.hard ? ' <span class="tag C" style="font-size:10.5px;padding:1px 6px">Hard</span>' : ''}</td>
      <td>${ddmm(p.entry)}</td>
      <td style="text-align:right">${p.shares ? num(p.shares) : '—'}${chuaVe ? `<div class="muted" style="font-size:11px">${num(chuaVe)} cp chưa về</div>` : ''}</td>
      <td style="text-align:right">${tt == null ? '—' : dec(tt, 1) + '%'}</td>
      <td style="text-align:right">${dec(lastPx(p.sym) || p.last / 1000)}</td>
      <td style="text-align:right" class="${p.pnl >= 0 ? 'pos' : 'neg'}">${p.pnl >= 0 ? '+' : ''}${dec(p.pnl)}%</td>
      <td><select class="fin" data-hsp="${esc(p.sym)}" style="width:76px">${HARD_PHAN.map(([v, t]) => `<option value="${v}"${v === 1 ? ' selected' : ''}>${t}</option>`).join('')}</select></td>
      <td><input class="fin" type="number" step="0.01" data-hsg="${esc(p.sym)}" placeholder="giá" style="width:92px"></td>
      <td>${khoa ? `<span class="muted" style="font-size:12px">${esc(khoa)}</span>` : `<button class="btn" data-hsb="${esc(p.sym)}">Hard Sell</button>${choBan.has(p.sym) ? '<div class="muted" style="font-size:11px">có lệnh bán đang chờ</div>' : ''}`}</td></tr>`;
  }).join('');

  const nhanTT = x => {
    if (x.o.huy) return '<span class="muted">đã hoàn tác</span>';
    if (x.f) return x.f.ok
      ? `<b class="pos">${x.o.loai === 'mua' ? 'đã mua' : 'đã bán'}</b> phiên ${ddmm(x.f.phien)}${x.f.sh ? ' · ' + num(x.f.sh) + ' cp' : ''}${x.f.pct_thuc != null ? ' · ' + dec(x.f.pct_thuc, 1) + '% NAV' : ''}${x.f.rang_buoc ? ' <span class="muted">(chặn bởi ' + esc(x.f.rang_buoc) + ')</span>' : ''}`
      : `<b class="neg">từ chối</b> — ${esc(x.f.ly_do)}`;
    if (x.cho) return `<span class="muted">chờ dữ liệu phiên ${ddmm(x.o.ngay)}</span>`;
    return '<span class="muted">chờ bản dựng tối</span>';
  };
  const dongLenh = ds.map(x => `<tr>
      <td>${esc(String(x.o.luc || '').replace('T', ' ').slice(0, 16))}</td>
      <td><b class="${x.o.loai === 'mua' ? 'pos' : 'neg'}">${x.o.loai === 'mua' ? 'HARD BUY' : 'HARD SELL'}</b></td>
      <td class="sym">${esc(x.o.sym)}</td><td>${ddmm(x.o.ngay)}</td>
      <td style="text-align:right">${dec(+x.o.gia)}</td>
      <td style="text-align:right">${x.o.loai === 'mua' ? dec(+x.o.pct_nav, 1) + '% NAV' : Math.round(+x.o.phan * 100) + '% vị thế'}</td>
      <td>${nhanTT(x)}</td>
      <td>${(!x.seen && !x.o.huy) ? `<button class="mini" data-hht="${esc(x.o.id)}">Hoàn tác</button>` : ''}</td></tr>`).join('');

  box.innerHTML = `
  <h2>Lệnh Hard <span class="muted" style="font-size:15px;font-weight:400">→ mua / bán thẳng trên danh mục hệ thống, không chờ tín hiệu</span></h2>
  <div class="card">
    <p class="muted" style="margin-top:0">Phiên của lệnh bấm lúc này: <b>${ddmm(phien)}</b> · NAV sổ hệ thống ≈ <b>${nav ? vnd(nav) : '—'}</b> (bản dựng ${ddmm(D.asof)}).
    Giá phải nằm trong trần/sàn của phiên. Phí 0,15% mua, 0,25% bán như lệnh thường.</p>
    <h3 style="margin:6px 0">Hard Buy</h3>
    <div class="frm">
      <input id="hbSym" list="symlist" placeholder="Mã" maxlength="8" class="fin" style="width:100px">
      <label class="flab">% NAV<input id="hbPct" type="number" step="0.5" min="0.5" max="100" placeholder="10" class="fin" style="width:84px"></label>
      <label class="flab">Giá<input id="hbGia" type="number" step="0.01" placeholder="26.55" class="fin" style="width:100px"></label>
      <input id="hbNote" placeholder="Ghi chú (không bắt buộc)" class="fin" style="flex:1;min-width:160px">
      <button class="btn" id="hbBtn">Hard Buy</button>
    </div>
    <p class="muted" style="font-size:12.5px;margin:8px 0 0">Vẫn bị chặn bởi trần mỗi mã ${dec(100 * ((D.cfg_prod || {}).max_pos || 0.5), 0)}%, tổng vốn, ngành ${dec(100 * ((D.cfg_prod || {}).sector_cap || 0.3), 0)}%, tiền mặt, tối đa ${(D.cfg_prod || {}).max_pos_n || 12} mã. Mã đang cầm thì mua thêm (giá vốn bình quân). Sau khi mua, bot quản lý điểm bán như lệnh thường.</p>
    <h3 style="margin:16px 0 6px">Hard Sell</h3>
    ${op.length ? `<div class="tblwrap"><table><thead><tr><th>Mã</th><th>Mua</th><th style="text-align:right">Số cp</th><th style="text-align:right">% NAV</th><th style="text-align:right">Giá</th><th style="text-align:right">Lãi/lỗ</th><th>Bán</th><th>Giá bán</th><th></th></tr></thead><tbody>${dongBan}</tbody></table></div>`
      : '<p class="muted" style="margin:0">Danh mục hệ thống đang trống.</p>'}
    <div id="hardmsg"></div>
    <h3 style="margin:16px 0 6px">Lệnh đã bấm</h3>
    ${ds.length ? `<div class="tblwrap"><table><thead><tr><th>Lúc bấm</th><th>Lệnh</th><th>Mã</th><th>Phiên</th><th style="text-align:right">Giá</th><th style="text-align:right">Khối lượng</th><th>Trạng thái</th><th></th></tr></thead><tbody>${dongLenh}</tbody></table></div>`
      : '<p class="muted" style="margin:0">Chưa có lệnh Hard nào.</p>'}
    <p class="muted" style="font-size:12.5px;margin:8px 0 0">Hoàn tác được cho tới khi bản dựng tối xử lý lệnh. Sau đó muốn sửa thì bấm lệnh ngược lại (tính phí như lệnh thật).</p>
  </div>`;

  document.getElementById('hbBtn').onclick = () => hardMua().catch(e => hardBao('<b>Chưa đặt được lệnh.</b> ' + esc(e.message)));
  box.querySelectorAll('[data-hsb]').forEach(b => b.onclick = () => hardBan(b.dataset.hsb).catch(e => hardBao('<b>Chưa đặt được lệnh.</b> ' + esc(e.message))));
  box.querySelectorAll('[data-hht]').forEach(b => b.onclick = () => hardHoanTac(b.dataset.hht).catch(e => hardBao('<b>Chưa hoàn tác được.</b> ' + esc(e.message))));
  // điền sẵn giá mới nhất cho ô giá bán, rồi trả lại những gì anh đã gõ
  box.querySelectorAll('[data-hsg]').forEach(i => { const g = lastPx(i.dataset.hsg); if (g) i.value = (+g).toFixed(2); });
  box.querySelectorAll('input,select').forEach(e => {
    const k = e.id || (e.dataset.hsp ? 'p:' + e.dataset.hsp : e.dataset.hsg ? 'g:' + e.dataset.hsg : '');
    if (k && giu[k] != null && giu[k] !== '') e.value = giu[k];
  });
  const m = document.getElementById('hardmsg'); if (m && _msg) m.innerHTML = _msg;
  if (_f) { const e = document.getElementById(_f) || box.querySelector(`[data-hsg="${_f.slice(2)}"]`); if (e) e.focus(); }
}

async function _hardKiemGia(sym, gia) {
  const b = hardBienDo(sym, hardPhien());
  if (!(gia >= b.san - 1e-9 && gia <= b.tran + 1e-9))
    throw new Error(`giá ${dec(gia)} ngoài biên độ phiên của ${sym}: sàn ${dec(b.san)} – trần ${dec(b.tran)} (tham chiếu ${dec(b.ref)})`);
  return b;
}

async function hardMua() {
  const sym = (document.getElementById('hbSym').value || '').trim().toUpperCase();
  const pct = +document.getElementById('hbPct').value;
  const gia = +document.getElementById('hbGia').value;
  const note = (document.getElementById('hbNote').value || '').trim();
  if (!/^[A-Z0-9]{3,10}$/.test(sym)) throw new Error('mã không hợp lệ');
  if (!(pct > 0 && pct <= 100)) throw new Error('% NAV phải lớn hơn 0 và không quá 100');
  if (!(gia > 0)) throw new Error('chưa nhập giá');
  hardBao('Đang kiểm giá…', true);
  const b = await _hardKiemGia(sym, gia);
  const phien = hardPhien();
  const nav = +((D.book || {}).nav) || 0;
  const dang = (D.open_positions || []).find(p => p.sym === sym);
  if (!confirm(`HARD BUY ${sym}\n\nPhiên ${ddmm(phien)} · giá ${dec(gia)} (sàn ${dec(b.san)} – trần ${dec(b.tran)})\n` +
      `${dec(pct, 1)}% NAV${nav ? ' ≈ ' + vnd(nav * pct / 100) : ''}${dang ? '\nĐang cầm ' + sym + ' → mua thêm, tính lại giá vốn bình quân' : ''}\n\n` +
      `Bị chặn bởi trần mỗi mã / tổng vốn / ngành / tiền mặt / số mã tối đa nếu vượt.\nĐặt lệnh?`)) { hardBao('Đã huỷ, chưa ghi gì.', true); return; }
  const o = { id: _hardId(sym), loai: 'mua', sym, ngay: phien, gia: +gia.toFixed(2), pct_nav: +pct.toFixed(2),
              tran: b.tran, san: b.san, luc: _hardLuc(), ghi_chu: note, huy: null };
  hardBao('Đang ghi lệnh…', true);
  await hardGhi(h => (h.push(o), h), `Hard Buy ${sym}`);
  ['hbSym', 'hbPct', 'hbGia', 'hbNote'].forEach(k => { const e = document.getElementById(k); if (e) e.value = ''; });
  veHard();
  hardBao(`<b>Đã đặt HARD BUY ${esc(sym)}</b> — phiên ${ddmm(phien)}, giá ${dec(gia)}, ${dec(pct, 1)}% NAV. Điện thoại sẽ nhận tin trong ít phút; sổ hệ thống cập nhật ở bản dựng tối.`, true);
}

async function hardBan(sym) {
  const sel = document.querySelector(`[data-hsp="${sym}"]`), inp = document.querySelector(`[data-hsg="${sym}"]`);
  const phan = +(sel ? sel.value : 1), gia = +(inp ? inp.value : 0);
  if (!HARD_PHAN.some(([v]) => Math.abs(v - phan) < 1e-9)) throw new Error('phần bán phải là 25/50/100%');
  if (!(gia > 0)) throw new Error('chưa nhập giá bán');
  const p = (D.open_positions || []).find(x => x.sym === sym);
  if (!p) throw new Error('hệ thống không cầm ' + sym);
  const phien = hardPhien(), sf = hardSellFrom(), n = hardSoPhien(p.entry, phien);
  if (n == null || n < sf) throw new Error(`${sym} chưa về hàng (mua ${ddmm(p.entry)}, bán được từ T+${sf})`);
  hardBao('Đang kiểm giá…', true);
  const b = await _hardKiemGia(sym, gia);
  const sh = p.shares || 0;
  let ban = phan >= 1 ? sh : Math.floor(sh * phan / 100) * 100;
  if (sh - ban < 100) ban = sh;
  if (ban < 100) throw new Error('không đủ 1 lô 100 cp để bán ' + Math.round(phan * 100) + '%');
  // cổ phiếu mua THÊM (nhồi / Hard) chưa về tài khoản thì chưa bán được — bộ máy cũng chặn y như vậy
  const bp = ((D.book || {}).positions || []).find(q => q.sym === sym) || {};
  const chuaVe = (bp.adds || []).filter(a => { const k = hardSoPhien(a[0], phien); return k == null || k < sf; })
    .reduce((s, a) => s + (+a[1] || 0), 0);
  if (ban > sh - chuaVe) throw new Error(`${num(chuaVe)} cp mua thêm của ${sym} chưa về tài khoản — chọn phần bán nhỏ hơn (tối đa ${num(sh - chuaVe)} cp) hoặc chờ hàng về`);
  if (((NSI.manual || {}).hard || []).some(o => o.sym === sym && o.loai === 'ban' && !o.huy && !((D.hard || {}).seen || []).includes(o.id)))
    if (!confirm(`Đã có một lệnh Hard Sell ${sym} đang chờ bản dựng. Vẫn đặt thêm lệnh nữa?`)) { hardBao('Đã huỷ, chưa ghi gì.', true); return; }
  if (!confirm(`HARD SELL ${sym}\n\nPhiên ${ddmm(phien)} · giá ${dec(gia)} (sàn ${dec(b.san)} – trần ${dec(b.tran)})\n` +
      `${Math.round(phan * 100)}% vị thế ≈ ${num(ban)}/${num(sh)} cp${ban === sh && phan < 1 ? ' (phần còn lại dưới 100 cp → bán hết)' : ''}\n\nĐặt lệnh?`)) { hardBao('Đã huỷ, chưa ghi gì.', true); return; }
  const o = { id: _hardId(sym), loai: 'ban', sym, ngay: phien, gia: +gia.toFixed(2), phan,
              tran: b.tran, san: b.san, luc: _hardLuc(), ghi_chu: '', huy: null };
  hardBao('Đang ghi lệnh…', true);
  await hardGhi(h => (h.push(o), h), `Hard Sell ${sym}`);
  veHard();
  hardBao(`<b>Đã đặt HARD SELL ${esc(sym)}</b> — phiên ${ddmm(phien)}, giá ${dec(gia)}, ${Math.round(phan * 100)}% vị thế. Điện thoại sẽ nhận tin trong ít phút; sổ hệ thống cập nhật ở bản dựng tối.`, true);
}

async function hardHoanTac(id) {
  const x = hardDanhSach().find(z => z.o.id === id);
  if (!x) throw new Error('không thấy lệnh');
  if (x.seen || await hardKhoaHoanTac(id)) { veHard(); hardBao('<b>Không hoàn tác được.</b> Bản dựng đã xử lý lệnh này — muốn sửa thì bấm lệnh ngược lại.'); return; }
  if (!confirm(`Hoàn tác ${x.o.loai === 'mua' ? 'HARD BUY' : 'HARD SELL'} ${x.o.sym} (phiên ${ddmm(x.o.ngay)}, giá ${dec(+x.o.gia)})?`)) return;
  hardBao('Đang hoàn tác…', true);
  const luc = _hardLuc();
  await hardGhi(h => h.map(o => o.id === id ? Object.assign({}, o, { huy: luc }) : o), `Hoàn tác ${x.o.sym}`);
  veHard();
  hardBao(`<b>Đã hoàn tác</b> lệnh ${esc(x.o.sym)}.`, true);
}
