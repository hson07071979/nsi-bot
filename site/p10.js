/* ============================================================================
   SỔ TAY CỦA TÔI — nơi anh Sơn nhập tay, và là NGUỒN DỮ LIỆU THẬT của trang.

   Khác hẳn bản cũ: sổ tay không còn nằm im trong trình duyệt nữa.

     • Mã anh thêm ở "Mã tôi theo dõi"  ->  chảy vào Watchlist, mục Ghim thủ công
     • Lệnh anh ghi ở "Lệnh của tôi"    ->  chảy vào Danh mục hệ thống đang nắm giữ

   Cách nó chảy: bấm "Đăng lên trang", sổ tay được ghi thành `manual.json` trong
   repo public. Mọi người mở trang đều đọc file đó. Trước khi đăng thì bản nháp
   nằm trong máy anh, chưa ai thấy.

   Phí giao dịch tính tự động: mua 0,15%, bán 0,25% (đã gồm thuế). Con số lãi/lỗ
   hiện ra là tiền THẬT vào túi, không phải chênh lệch giá suông.
   ========================================================================== */
const NSI_KEY = 'nsi_sotay_v1';
const NSI_TOKEN_KEY = 'nsi_gh_token';
const PHI_MUA = 0.0015;      // = fee_buy trong hệ thống
const PHI_BAN = 0.0025;      // = fee_sell trong hệ thống (đã gồm thuế)
let _mem = null;             // bản dự phòng khi trình duyệt chặn bộ nhớ cục bộ
let _storageOK = true;

/* lãi/lỗ SAU PHÍ — dùng chung cho mọi bảng trên trang, không nơi nào tính khác */
function laiSauPhi(buy, sell) {
  if (!buy || !sell) return null;
  return ((+sell) * (1 - PHI_BAN)) / ((+buy) * (1 + PHI_MUA)) - 1;
}

function nsiLoad(){
  const empty = {watch:[], trades:[], an:[]};
  try {
    const raw = window.localStorage.getItem(NSI_KEY);
    _storageOK = true;
    if (!raw) return empty;
    const o = JSON.parse(raw);
    // bản cũ dùng tên `syms`, đọc lại được để không mất dữ liệu anh đã nhập
    return {watch: o.watch || o.syms || [], trades: o.trades || [], an: o.an || []};
  } catch(e){
    _storageOK = false;
    return _mem || empty;
  }
}
function nsiSave(data){
  _mem = data;
  try { window.localStorage.setItem(NSI_KEY, JSON.stringify(data)); _storageOK = true; }
  catch(e){ _storageOK = false; }
}

/* giá đóng cửa gần nhất — real-time nếu có, không thì nến, không nữa thì bộ lọc */
function lastPx(sym){
  if (typeof giaMoiNhat === 'function') { const v = giaMoiNhat(sym); if (v) return v; }
  const c = (D.candles || {})[sym];
  if (c && c.bars && c.bars.length) return c.bars[c.bars.length-1][4];
  const r = ((D.screener || {}).rows || []).find(x => x.sym === sym);
  return r ? r.price : null;
}
const ALLSYMS = Object.keys(D.lookup || {}).sort();

function pnlOf(t){
  const out = t.sell_px ? +t.sell_px : lastPx(t.sym);
  const v = laiSauPhi(t.buy_px, out);
  return v == null ? null : v * 100;
}

/* ---------- đăng sổ tay lên trang khách hàng ---------- */
function soTayJSON(){
  const d = nsiLoad();
  return JSON.stringify({
    v: 1,
    updated: new Date().toISOString().slice(0,19),
    trades: d.trades,
    watch: d.watch,
    // Mã anh Sơn ẩn khỏi Danh mục hệ thống. Phải đi cùng manual.json, không thì
    // ẩn xong chỉ mình máy anh thấy còn khách hàng vẫn thấy mã đó.
    an: d.an || [],
  }, null, 1);
}

async function dangSoTay(){
  const box = document.getElementById('pubmsg');
  const say = (h, ok) => { if (box) box.innerHTML =
    `<div class="note${ok?' info':''}" style="margin-top:12px">${h}</div>`; };

  const repo  = (cfgData().repo || '').trim();
  const token = (localStorage.getItem(NSI_TOKEN_KEY) || '').trim();

  if (!repo || !token) {
    say(`<b>Chưa nối được với GitHub — dùng cách thủ công.</b>
      Bấm <b>Tải manual.json</b> bên dưới, rồi vào repo trang web trên GitHub,
      bấm <b>Add file → Upload files</b>, thả file vào, bấm <b>Commit changes</b>.
      Khoảng một phút sau khách hàng thấy ngay.
      ${!repo ? '<br>Muốn bấm một nút là xong thì điền <code>repo</code> trong <code>config.json</code> trước.' : ''}
      ${!token ? '<br>Và dán mã truy cập GitHub vào ô bên dưới (chỉ lưu trong máy anh).' : ''}`);
    return;
  }

  say('Đang đăng…');
  try {
    const url = `https://api.github.com/repos/${repo}/contents/manual.json`;
    const H = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };
    let sha = null;
    const cur = await fetch(url, { headers: H, cache: 'no-store' });
    if (cur.ok) sha = (await cur.json()).sha;

    const noi = soTayJSON();
    // btoa không nuốt được tiếng Việt — phải mã hoá UTF-8 trước
    const b64 = btoa(String.fromCharCode(...new TextEncoder().encode(noi)));
    const r = await fetch(url, {
      method: 'PUT', headers: H,
      body: JSON.stringify({
        message: 'Sổ tay ' + new Date().toLocaleString('vi-VN'),
        content: b64, sha: sha || undefined,
      }),
    });
    if (!r.ok) throw new Error((await r.json()).message || r.status);
    NSI.manual = JSON.parse(noi);
    say('<b>Đã đăng.</b> Khách hàng sẽ thấy trong khoảng một phút, sau khi GitHub dựng lại trang. ' +
        'Danh mục và Watchlist trên máy anh đã cập nhật ngay rồi.', true);
    veLaiTrang('danhmuc'); veLaiTrang('watchlist');
  } catch (e) {
    say(`<b>Đăng không được.</b> ${e.message}.
      Thường là mã truy cập hết hạn, sai repo, hoặc chưa cấp quyền <b>Contents: Read and write</b>.
      Cứ dùng cách tải file rồi tải lên tay, kết quả y hệt.`);
  }
}

function pageNotebook(root){
  const co_token = !!(localStorage.getItem(NSI_TOKEN_KEY) || '').trim();
  root.innerHTML = `
  <div class="hero" style="padding-bottom:4px">
    <div class="badge">Trang riêng · không hiện trong menu khách hàng</div>
    <h1 style="font-size:30px">Sổ tay của tôi</h1>
    
  </div>
  <div id="nbwarn"></div>

  <h2>Mã tôi theo dõi <span class="muted" style="font-size:15px;font-weight:400">→ chảy vào Watchlist, mục Ghim thủ công</span></h2>
  <div class="card">
    <div class="frm">
      <input id="sIn" list="symlist" placeholder="Mã, ví dụ HPG" maxlength="8" class="fin" style="width:130px">
      <datalist id="symlist">${ALLSYMS.map(s=>`<option value="${s}">`).join('')}</datalist>
      <input id="sNote" placeholder="Ghi chú (nền đẹp, chờ vol…)" class="fin" style="flex:1;min-width:180px">
      <button class="btn" id="sAdd">Thêm mã</button>
    </div>
    <div id="symbox" style="margin-top:12px"></div>
  </div>

  <h2>Lệnh của tôi <span class="muted" style="font-size:15px;font-weight:400">→ chảy vào Danh mục hệ thống</span></h2>
  <div class="card">
    <div class="frm">
      <input id="tSym" list="symlist" placeholder="Mã" maxlength="8" class="fin" style="width:100px">
      <label class="flab">Ngày mua<input id="tBd" type="date" class="fin"></label>
      <label class="flab">Giá mua<input id="tBp" type="number" step="0.01" placeholder="24.55" class="fin" style="width:100px"></label>
      <label class="flab">Số lượng<input id="tSh" type="number" step="100" placeholder="1000" class="fin" style="width:110px"></label>
      <button class="btn" id="tAdd">Ghi lệnh mua</button>
    </div>
    
    <div class="note info" style="margin-top:12px"><b>Phí tính sẵn, không phải nhẩm.</b>
    Mọi con số lãi/lỗ ở đây đã trừ <b>0,15% mua</b> và <b>0,25% bán (gồm thuế)</b> — đúng bộ phí đang dùng trong backtest.
    Nghĩa là mua 24.55 bán đúng 24.55 thì sổ ghi <b class="neg">−0,40%</b>, chứ không phải hoà vốn.</div>
    <div id="tradebox" style="margin-top:12px"></div>
  </div>

  <div class="grid kpis" id="nbkpi" style="margin-top:16px"></div>

  <h2>Ẩn mã khỏi Danh mục hệ thống <span class="muted" style="font-size:15px;font-weight:400">→ gỡ khỏi trang khách hàng</span></h2>
  <div class="card">
    <p style="margin-top:0">Danh mục khách hàng thấy gộp từ <b>ba nguồn</b>. Hai nguồn đầu —
    <b>sổ chạy của bộ máy</b> và <b>sổ ghi tiến</b> — không nằm trong sổ tay này, nên
    xoá ở mục "Lệnh của tôi" phía trên <b>không gỡ được chúng</b>. Đó là chỗ để gỡ.</p>
    <div class="note info" style="margin:0 0 12px"><b>Ẩn chỉ là giấu khỏi màn hình.</b>
    Nó không sửa một chữ nào trong sổ backtest, không đổi con số hiệu suất, không đổi
    tab Kiểm định. Dùng khi bộ máy ghi đang cầm một mã mà ngoài đời anh không cầm.</div>
    <div class="frm">
      <select id="anSel" class="fin" style="flex:1;min-width:200px"></select>
      <button class="btn" id="anAdd">Ẩn mã này</button>
    </div>
    <div id="anbox" style="margin-top:12px"></div>
  </div>

  <h2>Đăng lên trang khách hàng</h2>
  <div class="card">
    <p style="margin-top:0">Nhập xong thì phải đăng, không thì chỉ mình anh thấy. Đăng tức là ghi
    <code>manual.json</code> vào repo trang web — nơi mọi người đọc.</p>
    <div class="frm">
      <button class="btn" id="pubBtn">Đăng lên trang</button>
      <button class="btn ghost" id="dlBtn">Tải manual.json</button>
    </div>
    <div id="pubmsg"></div>
    <details style="margin-top:14px">
      <summary class="muted" style="cursor:pointer">Bấm một nút là xong — cách cài (làm một lần)</summary>
      <p style="margin:10px 0 6px">Cần hai thứ, cài một lần rồi thôi:</p>
      <ol style="margin:0 0 10px 18px;line-height:1.7">
        <li>Trong repo trang web, sửa <code>config.json</code>, điền <code>"repo": "tên-đăng-nhập/tên-repo"</code>.</li>
        <li>Vào <b>github.com → Settings → Developer settings → Personal access tokens → Fine-grained tokens</b>,
            tạo mã mới, <b>chỉ chọn đúng repo trang web</b>, quyền <b>Contents: Read and write</b>, đặt hạn dùng.
            Dán vào ô dưới.</li>
      </ol>
      <div class="frm">
        <input id="ghTok" type="password" placeholder="${co_token ? '••••••••  (đã có mã, dán mã mới để thay)' : 'Dán mã truy cập GitHub'}" class="fin" style="flex:1;min-width:220px">
        <button class="btn ghost" id="tokSave">Lưu mã</button>
        <button class="btn ghost" id="tokDel">Xoá mã</button>
      </div>
      <div class="note" style="margin-top:12px"><b>Mã này nằm trong trình duyệt của anh, không nằm trong file web.</b>
      Khách hàng mở cùng đường link cũng không thấy nó. Nhưng vẫn nên đặt hạn dùng ngắn và
      chỉ cấp quyền cho đúng một repo — mất mã thì người khác sửa được trang, chứ không đụng
      được vào hệ thống vì hệ thống nằm ở repo riêng.</div>
    </details>
  </div>

  <h2>Ghim và loại thủ công</h2>
  <div class="card">
    <p style="margin-top:0">Hai danh sách này nằm trong <b>repo private</b> dưới dạng hai file văn bản, sửa thẳng
    trên GitHub. Khác với sổ tay ở trên (chảy vào trang ngay khi anh đăng), hai file đó
    <b>chi phối chính bộ máy</b>: chúng quyết định mã nào được vào watchlist tự động và mã nào được phép kêu chuông.</p>
    <div class="two">
      <div>
        <h3 style="margin:0 0 6px"><code>ghim.txt</code> — ${(D.screener.seed || []).length} mã ghim</h3>
        
        <div>${(D.screener.seed || []).map(x => `<span class="tag B" style="margin-left:0;margin-right:6px;font-size:12px;padding:3px 8px">${x}</span>`).join('') || '<span class="muted">trống</span>'}</div>
      </div>
      <div>
        <h3 style="margin:0 0 6px"><code>loai.txt</code> — ${(D.screener.loai || []).length} mã loại</h3>
        
        <div>${(D.screener.loai || []).map(x => `<span class="tag C" style="margin-left:0;margin-right:6px;font-size:12px;padding:3px 8px">${x}</span>`).join('') || '<span class="muted">trống — chưa loại mã nào</span>'}</div>
      </div>
    </div>
    <div class="note" style="margin-top:14px"><b>Sửa thế nào.</b> Vào repo private trên GitHub, bấm vào file
    <code>ghim.txt</code> hoặc <code>loai.txt</code>, bấm biểu tượng cây bút, gõ thêm mã (mỗi dòng một mã),
    bấm <b>Commit changes</b>. Bản quét 19h30 tối nay sẽ áp dụng. Backtest không đổi một con số nào —
    hai file này chỉ chi phối từ hôm nay trở đi, lịch sử phải giữ nguyên si.</div>
  </div>

  <h2>Sao lưu</h2>
  <div class="card">
    <p style="margin-top:0">Bản nháp nằm trong trình duyệt nên <b>xoá cache là mất</b>. Đã đăng lên trang rồi thì
    an toàn (nằm trong GitHub), nhưng thỉnh thoảng vẫn nên giữ một bản.</p>
    <div class="frm">
      <button class="btn ghost" id="expBtn">Tải file sao lưu</button>
      <button class="btn ghost" id="impBtn">Nạp lại từ file</button>
      <input id="impFile" type="file" accept="application/json" style="display:none">
      <button class="btn ghost" id="clrBtn">Xoá sạch</button>
    </div>
  </div>`;

  const render = () => {
    const d = nsiLoad();

    document.getElementById('nbwarn').innerHTML = _storageOK ? '' :
      `<div class="note" style="border-color:var(--critical);margin-bottom:16px"><b>Trình duyệt đang chặn bộ nhớ cục bộ.</b> Anh vẫn nhập được nhưng đóng tab là mất. Thường gặp khi mở file trực tiếp từ máy hoặc dùng chế độ ẩn danh — mở qua đường link web thật thì hết. Nhớ bấm "Đăng lên trang" hoặc "Tải file sao lưu" trước khi đóng.</div>`;

    // ----- mã theo dõi -----
    const sb = document.getElementById('symbox');
    sb.innerHTML = d.watch.length
      ? '<div class="tblwrap"><table><thead><tr><th>Mã</th><th style="text-align:right">Giá gần nhất</th><th>Trạng thái hệ thống</th><th>Ghi chú</th><th>Ngày thêm</th><th style="width:60px"></th></tr></thead><tbody>' +
        d.watch.map((s,i)=>{
          const px = lastPx(s.sym);
          const lk = (D.lookup||{})[s.sym];
          return `<tr><td class="sym">${esc(s.sym)}</td>
            <td style="text-align:right">${px ?? '—'}</td>
            <td>${lk ? `<span class="lkbadge ${lk.state}" style="font-size:11px">${esc(lk.label)}</span>` : '<span class="muted">ngoài vũ trụ</span>'}</td>
            <td class="muted" style="font-size:13px">${esc(s.note) || ''}</td>
            <td class="muted" style="font-size:13px">${s.added}</td>
            <td><button class="mini" data-del="${i}">Bỏ</button></td></tr>`;
        }).join('') + '</tbody></table></div>'
      : '<p class="muted" style="margin:0">Chưa có mã nào. Gõ mã vào ô trên rồi bấm "Thêm mã".</p>';
    sb.querySelectorAll('[data-del]').forEach(b => b.onclick = () => {
      const x = nsiLoad(); x.watch.splice(+b.dataset.del,1); nsiSave(x); render();
    });

    // ----- lệnh -----
    const tb = document.getElementById('tradebox');
    const rows = d.trades.map((t,i)=>{
      const p = pnlOf(t), open = !t.sell_px;
      const out = t.sell_px || lastPx(t.sym);
      const tien = (t.sh && out && t.buy_px)
        ? Math.round(t.sh * ((+out)*1000*(1-PHI_BAN) - (+t.buy_px)*1000*(1+PHI_MUA))) : null;
      return `<tr><td class="sym">${esc(t.sym)}</td>
        <td>${t.buy_d||'—'}</td>
        <td style="text-align:right">${t.buy_px}</td>
        <td style="text-align:right" class="muted">${t.sh ? num(t.sh) : '—'}</td>
        <td>${t.sell_d||'<span class="muted">đang giữ</span>'}</td>
        <td style="text-align:right">${out ?? '—'}${open&&out?'<span class="muted"> (hiện tại)</span>':''}</td>
        <td style="text-align:right;font-weight:660" class="${p==null?'':(p>=0?'pos':'neg')}">${p==null?'—':(p>=0?'+':'')+p.toFixed(2)+'%'}</td>
        <td style="text-align:right" class="${tien==null?'muted':(tien>=0?'pos':'neg')}">${tien==null?'—':(tien>=0?'+':'−')+vnd(Math.abs(tien))}</td>
        <td>${open?`<button class="mini" data-sell="${i}">Bán</button>`:''}
            <button class="mini" data-tdel="${i}">Xoá</button></td></tr>`;
    }).join('');
    tb.innerHTML = d.trades.length
      ? '<div class="tblwrap"><table><thead><tr><th>Mã</th><th>Ngày mua</th><th style="text-align:right">Giá mua</th><th style="text-align:right">SL</th><th>Ngày bán</th><th style="text-align:right">Giá bán</th><th style="text-align:right">Lãi/lỗ sau phí</th><th style="text-align:right">Tiền</th><th style="width:110px"></th></tr></thead><tbody>'+rows+'</tbody></table></div>'
      : '';

    tb.querySelectorAll('[data-tdel]').forEach(b => b.onclick = () => {
      const x = nsiLoad(); x.trades.splice(+b.dataset.tdel,1); nsiSave(x); render(); doiTrang();
    });
    tb.querySelectorAll('[data-sell]').forEach(b => b.onclick = () => {
      const i = +b.dataset.sell, x = nsiLoad(), t = x.trades[i];
      const dd = prompt(`Bán ${esc(t.sym)} — ngày bán (dạng ${D.asof}):`, D.asof);
      if (!dd) return;
      const pp = prompt(`Bán ${esc(t.sym)} — giá bán (nghìn đồng). Phí và thuế hệ tự trừ:`, lastPx(t.sym) ?? '');
      if (!pp) return;
      t.sell_d = dd.trim(); t.sell_px = +pp;
      nsiSave(x); render(); doiTrang();
    });

    // ----- tổng kết -----
    const closed = d.trades.filter(t => t.sell_px);
    const ps = closed.map(pnlOf).filter(x => x != null);
    const w = ps.filter(x => x > 0);
    const opens = d.trades.filter(t => !t.sell_px);
    const avg = ps.length ? ps.reduce((a,b)=>a+b,0)/ps.length : null;
    document.getElementById('nbkpi').innerHTML =
        kpi('Lệnh đã đóng', closed.length, `${opens.length} lệnh đang giữ`)
      + kpi('Tỷ lệ thắng', ps.length ? Math.round(w.length/ps.length*100)+'%' : '—', ps.length?`${w.length} thắng / ${ps.length-w.length} thua`:'chưa có lệnh đóng')
      + kpi('Lãi/lỗ TB mỗi lệnh', avg==null?'—':(avg>=0?'+':'')+avg.toFixed(2)+'%', 'sau phí, trên lệnh đã đóng', avg==null?'':(avg>=0?'pos':'neg'))
      + kpi('Mã đang theo dõi', d.watch.length, 'chảy vào Watchlist');
  };

  // sổ tay đổi thì hai trang kia phải vẽ lại, khỏi phải tải lại trang
  const doiTrang = () => {
    if (typeof veLaiTrang === 'function') { veLaiTrang('danhmuc'); veLaiTrang('watchlist'); }
  };

  /* ----- ẩn mã khỏi Danh mục hệ thống -----
     Ô chọn chỉ liệt kê mã ĐANG THỰC SỰ nằm trong danh mục cộng với mã đã ẩn —
     không đổ cả 694 mã vào, vì ẩn một mã không có trong danh mục là thao tác vô nghĩa. */
  const veAn = () => {
    const d = nsiLoad();
    const daAn = (d.an || []).map(s => String(s).toUpperCase());
    const dang = (typeof danhMuc === 'function' ? danhMuc() : [])
      .filter(x => !daAn.includes(x.sym));
    const sel = document.getElementById('anSel');
    sel.innerHTML = dang.length
      ? dang.map(x => `<option value="${esc(x.sym)}">${esc(x.sym)} — ${x.nguon === 'auto' ? 'Hệ thống' : 'Anh Sơn nhập'}${
          x.entry ? ' · mua ' + ddmm(x.entry) : ''}${x.sh ? ' · ' + x.sh.toLocaleString('vi') + ' cp' : ''}</option>`).join('')
      : '<option value="">(danh mục đang trống)</option>';
    document.getElementById('anAdd').disabled = !dang.length;
    document.getElementById('anbox').innerHTML = !daAn.length
      ? ''
      : `<div class="tblwrap"><table><thead><tr><th>Mã đang ẩn</th><th></th></tr></thead><tbody>
         ${daAn.map((s, i) => `<tr><td class="sym">${s}</td>
           <td style="text-align:right"><button class="btn ghost mini" data-hien="${i}">Hiện lại</button></td></tr>`).join('')}
         </tbody></table></div>`;
    document.getElementById('anbox').querySelectorAll('[data-hien]').forEach(b => b.onclick = () => {
      const x = nsiLoad(); x.an = (x.an || []); x.an.splice(+b.dataset.hien, 1);
      nsiSave(x); veAn(); doiTrang();
    });
  };
  document.getElementById('anAdd').onclick = () => {
    const sym = (document.getElementById('anSel').value || '').trim().toUpperCase();
    if (!sym) return;
    const x = nsiLoad();
    x.an = x.an || [];
    if (!x.an.map(s => String(s).toUpperCase()).includes(sym)) x.an.push(sym);
    nsiSave(x); veAn(); doiTrang();
  };

  // ----- thao tác -----
  document.getElementById('sAdd').onclick = () => {
    const el2 = document.getElementById('sIn');
    const sym = (el2.value||'').trim().toUpperCase();
    if (!sym) return;
    const x = nsiLoad();
    if (x.watch.some(s => s.sym === sym)) { alert(sym + ' đã có trong sổ tay rồi.'); return; }
    x.watch.unshift({sym, note:(document.getElementById('sNote').value||'').trim(), added: D.asof});
    nsiSave(x); el2.value=''; document.getElementById('sNote').value=''; render(); doiTrang();
  };
  document.getElementById('tAdd').onclick = () => {
    const sym = (document.getElementById('tSym').value||'').trim().toUpperCase();
    const bd  = document.getElementById('tBd').value;
    const bp  = document.getElementById('tBp').value;
    const sh  = document.getElementById('tSh').value;
    if (!sym || !bp) { alert('Cần ít nhất mã và giá mua.'); return; }
    const x = nsiLoad();
    x.trades.unshift({sym, buy_d: bd || D.asof, buy_px: +bp, sh: sh? +sh : null, sell_d:null, sell_px:null});
    nsiSave(x);
    document.getElementById('tSym').value=''; document.getElementById('tBp').value='';
    document.getElementById('tSh').value='';
    render(); doiTrang();
  };
  document.getElementById('pubBtn').onclick = dangSoTay;
  document.getElementById('dlBtn').onclick = () => {
    const blob = new Blob([soTayJSON()], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'manual.json';
    a.click(); URL.revokeObjectURL(a.href);
  };
  document.getElementById('tokSave').onclick = () => {
    const v = (document.getElementById('ghTok').value||'').trim();
    if (!v) return;
    try { localStorage.setItem(NSI_TOKEN_KEY, v); } catch(e){}
    document.getElementById('ghTok').value='';
    document.getElementById('pubmsg').innerHTML = '<div class="note info" style="margin-top:12px">Đã lưu mã trong máy anh. Bấm <b>Đăng lên trang</b> để thử.</div>';
  };
  document.getElementById('tokDel').onclick = () => {
    try { localStorage.removeItem(NSI_TOKEN_KEY); } catch(e){}
    document.getElementById('pubmsg').innerHTML = '<div class="note" style="margin-top:12px">Đã xoá mã khỏi máy này.</div>';
  };
  document.getElementById('expBtn').onclick = () => {
    const blob = new Blob([JSON.stringify(nsiLoad(),null,1)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `so-tay-nguyen-son-${D.asof}.json`;
    a.click(); URL.revokeObjectURL(a.href);
  };
  document.getElementById('impBtn').onclick = () => document.getElementById('impFile').click();
  document.getElementById('impFile').onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const rd = new FileReader();
    rd.onload = () => {
      try {
        const o = JSON.parse(rd.result);
        nsiSave({watch:o.watch||o.syms||[], trades:o.trades||[]});
        render(); doiTrang();
      } catch(err){ alert('File không đọc được.'); }
    };
    rd.readAsText(f);
  };
  document.getElementById('clrBtn').onclick = () => {
    if (confirm('Xoá sạch toàn bộ mã theo dõi và lệnh trong sổ tay?')) { nsiSave({watch:[],trades:[],an:[]}); render(); doiTrang(); }
  };

  render();
  veAn();
}

/* ============================================================================
   THANH TRA CỨU MÃ — gõ mã hoặc tên công ty, hiện ngay điều kiện của phiên tới.
   ========================================================================== */
(function(){
  const L = D.lookup || {};
  const KEYS = Object.keys(L);
  if (!KEYS.length) return;
  const inp = document.getElementById('lkIn');
  const sug = document.getElementById('lkSug');
  const out = document.getElementById('lkOut');
  if (!inp) return;

  // bỏ dấu tiếng Việt để tìm theo tên công ty cho dễ
  const nodau = s => (s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
  const IDX = KEYS.map(k => ({k, s:k.toLowerCase(), n:nodau(L[k].name)}));

  const trieu = v => v >= 1e6 ? (v/1e6).toFixed(1)+' triệu cp' : Math.round(v/1000)+ ' nghìn cp';

  function show(sym){
    const x = L[sym];
    if (!x){ out.innerHTML=''; return; }
    const need = x.state === 'chan'
      ? `<span class="lkmiss">${x.block}</span>`
      : `<span class="need">Đóng cửa phiên tới <b style="color:var(--text-primary)">≥ ${x.need_px}</b> · KL <b style="color:var(--text-primary)">≥ ${trieu(x.need_vol)}</b></span>`;
    const tim = x.tim ? `<span class="lkbadge tim" title="${esc(x.tim_vi) || ''}">ĐÈN TÍM</span>` : '';
    const sub = (x.tim ? `<span class="lkmiss" style="color:var(--s7)">đèn tím: ${esc(x.tim_vi)} — lãi kiểu này không lặp lại quý sau</span><br>` : '')
      + ((x.state === 'cho')
      ? `<span class="lkmiss">nền ${x.base}% · điểm ${x.score} · GTGD ${x.gtgd} tỷ — đã qua mọi cổng, chỉ chờ phiên bùng nổ</span>`
      : (x.miss && x.miss.length ? `<span class="lkmiss">còn thiếu: ${x.miss.join(' · ')}</span>` : ''));
    out.innerHTML =
      `<span class="nm">${esc(x.sym)}</span><span>— ${esc(x.name)} (${esc(x.exch)})</span>
       <span class="lkbadge ${x.state}">${esc(x.label)}</span> ${tim} ${need}
       ${sub ? `<div style="flex-basis:100%;margin-top:-4px">${sub}</div>` : ''}`;
    try { localStorage.setItem('nsi_lk', sym); } catch(e){}
  }

  let cur = -1, list = [];
  function search(q){
    const t = q.trim().toLowerCase(), tn = nodau(q.trim());
    if (!t){ sug.classList.remove('on'); return; }
    list = IDX.filter(o => o.s.startsWith(t) || o.n.includes(tn))
              .sort((a,b) => (a.s.startsWith(t)?0:1) - (b.s.startsWith(t)?0:1) || a.s.localeCompare(b.s))
              .slice(0,12);
    if (!list.length){ sug.innerHTML='<div class="lkmiss">Không tìm thấy mã nào</div>'; sug.classList.add('on'); return; }
    cur = -1;
    sug.innerHTML = list.map((o,i)=>`<div data-i="${i}"><b>${o.k}</b> — ${L[o.k].name}</div>`).join('');
    sug.classList.add('on');
    sug.querySelectorAll('[data-i]').forEach(el2 => el2.onclick = () => pick(+el2.dataset.i));
  }
  function pick(i){
    if (!list[i]) return;
    inp.value = list[i].k; sug.classList.remove('on'); show(list[i].k);
  }
  inp.addEventListener('input', e => search(e.target.value));
  inp.addEventListener('keydown', e => {
    if (!sug.classList.contains('on')) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp'){
      e.preventDefault();
      cur = Math.max(0, Math.min(list.length-1, cur + (e.key==='ArrowDown'?1:-1)));
      sug.querySelectorAll('[data-i]').forEach((el2,i)=>el2.classList.toggle('sel', i===cur));
    } else if (e.key === 'Enter'){ e.preventDefault(); pick(cur < 0 ? 0 : cur); }
    else if (e.key === 'Escape'){ sug.classList.remove('on'); }
  });
  document.addEventListener('click', e => { if (!sug.contains(e.target) && e.target !== inp) sug.classList.remove('on'); });

  // mở lại mã đã xem lần trước, không thì lấy mã đầu tiên đang CHỜ ĐIỂM MUA
  let init = null;
  try { init = localStorage.getItem('nsi_lk'); } catch(e){}
  if (!init || !L[init]) init = KEYS.find(k => L[k].state === 'cho') || KEYS[0];
  inp.value = init; show(init);
})();
