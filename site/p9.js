/* ============================================================================
   TRANG KHÁCH HÀNG — Hiệu suất · Lịch sử lệnh
   ========================================================================== */

/* ============================ TRANG HIỆU SUẤT ============================ */
/* 03/10/2026 (anh Sơn): bỏ bảng "Lợi suất theo tháng"; "Top tín hiệu 6 tháng" thay bằng
   LỊCH SỬ LỆNH đầy đủ (lọc + sắp xếp + KPI chạy theo bộ lọc); tab Lịch sử lệnh bỏ khỏi menu. */
function pageHome(root){
  root.innerHTML = `
  ${typeof bangSoLieuCu === 'function' ? bangSoLieuCu() : ''}
  <div class="hero">
    <div class="badge">Dữ liệu real-time · nguồn FireAnt · chỉ giao dịch TOP ${cpTop()} mã thanh khoản nhất</div>
    <h1>Hiệu suất thật,<br>đo trên ${dec(dates.length/250,1)} năm dữ liệu.</h1>
  </div>
  <div class="grid kpis" id="hkpi"></div>

  <h2>Đường vốn — Hệ thống so với VN-Index</h2>
  <div class="card"><div class="legend">
    <span><i style="background:var(--s1)"></i>Hệ thống Nguyễn Sơn</span>
    <span><i style="background:var(--s2)"></i>VN-Index</span></div><div id="heq"></div></div>

  <h2 id="lichsulenh">Lịch sử lệnh</h2>
  <div class="lslloc">
    <input type="search" id="lq" placeholder="Tìm mã, ngành…">
    <select id="lky"></select>
    <select id="lr"><option value="">Mọi lý do bán</option></select>
    <select id="lw"><option value="">Thắng &amp; thua</option><option value="w">Chỉ thắng</option><option value="l">Chỉ thua</option></select>
    <select id="ll"><option value="">Mọi đèn</option><option value="XANH">Đèn Xanh</option><option value="VANG">Đèn Vàng</option><option value="CAM">Đèn Cam</option><option value="DO">Đèn Đỏ</option></select>
    <button class="mini" id="lxoa">Xoá lọc</button>
  </div>
  <div class="grid kpis" id="lkpi" style="margin-bottom:14px"></div>
  <div class="card tblwrap"><table id="ltab" class="lsl"><thead><tr>
    <th data-k="sym">Mã</th><th data-k="sector">Ngành</th>
    <th data-k="entry">Ngày mua</th><th data-k="exit">Ngày bán</th>
    <th data-k="held" class="r">Giữ</th><th data-k="gm" class="r">Giá mua</th><th data-k="gb" class="r">Giá bán</th>
    <th data-k="pnl_pct" class="r">Lãi/lỗ</th><th data-k="tk" class="r">% tài khoản</th><th data-k="peak" class="r">Đỉnh lãi</th>
    <th data-k="reason">Lý do bán</th><th data-k="light">Đèn</th><th></th></tr></thead>
    <tbody id="lbody"></tbody></table></div>
  <div class="muted" id="ldem" style="font-size:12.5px;margin-top:6px"></div>

  <h2>Danh mục hệ thống đang cầm</h2>
  <div class="card" id="hopen"></div>
  `;

  document.getElementById('hkpi').innerHTML =
      kpi('Tổng lợi nhuận', sg(M.total_return), `${dec(dates.length/250,1)} năm · VN-Index ${sg(BM.total)}`, cls(M.total_return))
    + kpi('Lợi nhuận mỗi năm', sg(M.cagr), `VN-Index ${sg(BM.cagr)}`, cls(M.cagr))
    + kpi('Sụt giảm tối đa', '−'+(M.maxdd*100).toFixed(2).replace('.',',')+'%', `VN-Index −${pct(BM.mdd)}`, 'neg')
    + kpi('Profit Factor', dec(M.pf), 'lãi gộp / lỗ gộp')
    + kpi('Số deal', (P.deal_metrics||{}).deals ?? M.trades, (P.deal_metrics||{}).deals
        ? `${dec((P.deal_metrics||{}).deals/(dates.length/250),1)} deal mỗi năm`
        : `${M.per_year} lệnh mỗi năm`)
    + kpi('Tỷ lệ thắng', pct((P.deal_metrics||{}).winrate ?? M.winrate), `lãi TB +${dec((P.deal_metrics||{}).avg_win ?? M.avg_win)}% · lỗ TB ${dec((P.deal_metrics||{}).avg_loss ?? M.avg_loss)}%`)
    + kpi('Lãi / Lỗ', dec((P.deal_metrics||{}).rr ?? M.rr), 'mỗi đồng rủi ro đổi lấy')
    + kpi('Sharpe', dec(M.sharpe), 'trên chuỗi NAV ngày');

  document.getElementById('hopen').innerHTML = bangDanhMucNgan();

  lineChart(document.getElementById('heq'), {h:330, series:[
    {name:'Hệ thống Nguyễn Sơn', color:'--s1', v:botCurve, fill:true},
    {name:'VN-Index',       color:'--s2', v:benchCurve}],
    labels:dates, xticks, fmtY:v=>v.toFixed(2), fmtV:v=>v.toFixed(3)+'×'});

  lichSuLenh();
}

/* ---------- LỊCH SỬ LỆNH (trên trang Hiệu suất) ---------- */
function lsDuLieu(){
  const cur = P.curve || [];
  const navCuoi = cur.length ? cur[cur.length-1][1] : 1;
  const nav0 = (M.final_nav && navCuoi) ? M.final_nav / navCuoi : 1e9;
  const navNgay = {}; cur.forEach(c => navNgay[c[0]] = c[1]);
  const navTruoc = d => { // NAV cuoi phien lien truoc ngay d (luc dat lenh)
    let lo = 0, hi = cur.length - 1, k = -1;
    while (lo <= hi){ const m = (lo+hi)>>1; if (cur[m][0] < d){ k = m; lo = m+1; } else hi = m-1; }
    return (k >= 0 ? cur[k][1] : (cur[0]||[0,1])[1]) * nav0;
  };
  const gia = (raw, adj, phi) => raw ? raw/1000 : (adj ? adj/1000/(1+phi) : null);
  return (P.trades || []).map(t => Object.assign({}, t, {
    gm: gia(t.entry_raw, t.entry_px, PHI_MUA), gb: gia(t.exit_raw, t.exit_px, 0),
    tk: t.pnl_vnd != null ? t.pnl_vnd / navTruoc(t.entry) * 100 : null,
  }));
}
function lsKy(v){ // khoang thoi gian theo NGAY MUA -> [tu, den]
  const asof = D.asof || dates[dates.length-1];
  if (!v) return [dates[0], asof];
  if (v[0] === 'm'){ const n = +v.slice(1); const [y,m] = asof.split('-').map(Number);
    let yy = y, mm = m - n; while (mm <= 0){ mm += 12; yy--; }
    return [`${yy}-${String(mm).padStart(2,'0')}-01`, asof]; }
  return [v + '-01-01', v + '-12-31'];
}
function lsDoiTK(tu, den){ // % thay doi tai khoan va VN-Index trong [tu, den]
  const doi = (arr) => {
    const a = arr.filter(x => x[0] < tu), b = arr.filter(x => x[0] <= den);
    const s = a.length ? a[a.length-1][1] : (arr.find(x => x[0] >= tu) || [0,null])[1];
    const e = b.length ? b[b.length-1][1] : null;
    return (s && e) ? e/s - 1 : null;
  };
  return [doi(P.curve || []), doi(D.bench || [])];
}
function lichSuLenh(){
  const R = lsDuLieu();
  const $ = id => document.getElementById(id);
  const years = [...new Set(R.map(t => t.entry.slice(0,4)))].sort().reverse();
  $('lky').innerHTML = `<option value="">Tất cả từ ${dates[0].slice(0,4)}</option>
    <option value="m6">6 tháng gần nhất</option><option value="m12">12 tháng gần nhất</option>` +
    years.map(y => `<option value="${y}">Năm ${y}</option>`).join('');
  const reasons = [...new Set(R.map(t => t.reason))].sort();
  $('lr').innerHTML += reasons.map(r => `<option value="${esc(r)}">${esc(r)}</option>`).join('');
  let sk = 'entry', sd = -1;
  const p2 = x => x == null ? '—' : (+x).toFixed(2).replace('.', ',');
  const pc = (x, d=1) => x == null ? '—' : (x >= 0 ? '+' : '') + (+x).toFixed(d).replace('.', ',') + '%';
  const ngay = d => d ? d.split('-').reverse().join('/') : '—';

  function render(){
    const Q = $('lq').value.trim().toLowerCase(), ky = $('lky').value;
    const [tu, den] = lsKy(ky);
    const rows = R.filter(t => {
      if (t.entry < tu || t.entry > den) return false;
      if ($('lr').value && t.reason !== $('lr').value) return false;
      if ($('ll').value && t.light !== $('ll').value) return false;
      if ($('lw').value === 'w' && !(t.pnl_pct > 0)) return false;
      if ($('lw').value === 'l' && t.pnl_pct > 0) return false;
      if (Q && !(t.sym + ' ' + (t.sector||'')).toLowerCase().includes(Q)) return false;
      return true;
    });
    rows.sort((a, b) => {
      const x = a[sk], y = b[sk];
      if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
      const c = (x > y ? 1 : x < y ? -1 : 0) * sd;
      return c || (a.entry < b.entry ? 1 : a.entry > b.entry ? -1 : 0);
    });
    $('lbody').innerHTML = rows.length ? rows.map(t => `<tr>
      <td class="sym">${esc(t.sym)}</td><td class="muted lsn">${esc(t.sector||'')}</td>
      <td>${ngay(t.entry)}</td><td>${ngay(t.exit)}</td>
      <td class="r">${t.held} phiên</td><td class="r">${p2(t.gm)}</td><td class="r">${p2(t.gb)}</td>
      <td class="r ${cls(t.pnl_pct)}" style="font-weight:660">${pc(t.pnl_pct, 2)}</td>
      <td class="r ${t.tk==null?'':cls(t.tk)}">${pc(t.tk, 2)}</td>
      <td class="r">${t.peak ? '+' + String(t.peak).replace('.', ',') + '%' : '—'}</td>
      <td class="muted" style="font-size:13px">${esc(t.reason)}${t.frac && t.frac < 1 ? ' (bán 1 phần)' : ''}</td>
      <td><span class="pill ${t.light}">${LIGHTNAME[t.light] || t.light || ''}</span></td>
      <td><button class="mini" onclick="openChart('${esc(t.sym)}')">Nến</button></td></tr>`).join('')
      : '<tr><td colspan="13" class="muted">Không có lệnh nào khớp bộ lọc.</td></tr>';

    // KPI — dem theo DEAL (gop cac lan ban tung phan cung ma + ngay mua)
    const g = {};
    rows.forEach(t => { const k = t.sym + '|' + t.entry;
      (g[k] = g[k] || { sym: t.sym, entry: t.entry, w: 0, p: 0 });
      const w = t.pnl_pct ? Math.abs(t.pnl_vnd / (t.pnl_pct/100)) : 0;
      g[k].w += w; g[k].p += t.pnl_pct * w; g[k].n = (g[k].n||0) + 1; g[k].p1 = t.pnl_pct; });
    const deals = Object.values(g).map(d => ({ sym: d.sym, entry: d.entry, pnl: d.w ? d.p / d.w : d.p1 }));
    const thang = deals.filter(d => d.pnl > 0), thua = deals.filter(d => d.pnl <= 0);
    const tot = deals.slice().sort((a, b) => b.pnl - a.pnl)[0];
    const [tk, vni] = lsDoiTK(tu, den);
    const locThem = Q || $('lr').value || $('ll').value || $('lw').value;
    const dongGop = rows.reduce((s, t) => s + (t.tk || 0), 0);
    const tenKy = ky === '' ? 'từ ' + dates[0].slice(0,4) : ky[0] === 'm' ? ky.slice(1) + ' tháng gần nhất' : 'năm ' + ky;
    const tb = a => a.length ? a.reduce((s, d) => s + d.pnl, 0) / a.length : null;
    $('lkpi').innerHTML =
        kpi('Số giao dịch', deals.length, `${thang.length} thắng · ${thua.length} thua`)
      + kpi('Tỷ lệ thắng', deals.length ? pct(thang.length / deals.length, 0) : '—', tenKy)
      + kpi('Giá trị tài khoản', tk == null ? '—' : sg(tk), (vni == null ? '' : `VN-Index ${sg(vni)} cùng kỳ`)
            + (locThem ? `<br>các lệnh đang lọc: ${pc(dongGop, 1)} tài khoản` : ''), tk == null ? '' : cls(tk))
      + kpi('Deal tốt nhất', tot ? `${esc(tot.sym)} ${pc(tot.pnl)}` : '—', tot ? ngay(tot.entry) : '')
      + kpi('Lãi TB · lỗ TB', `<span class="pos">${pc(tb(thang))}</span> · <span class="neg">${pc(tb(thua))}</span>`, 'mỗi lệnh thắng · thua');
    $('ldem').textContent = `${rows.length} / ${R.length} lệnh`;
    document.querySelectorAll('#ltab thead th[data-k]').forEach(th => {
      th.classList.toggle('sorted', th.dataset.k === sk);
      th.dataset.dir = th.dataset.k === sk ? (sd < 0 ? '▼' : '▲') : '';
    });
  }
  document.querySelectorAll('#ltab thead th[data-k]').forEach(th => th.onclick = () => {
    const k = th.dataset.k;
    if (k === sk) sd = -sd; else { sk = k; sd = (k === 'sym' || k === 'sector' || k === 'reason' || k === 'light') ? 1 : -1; }
    render();
  });
  ['lq', 'lky', 'lr', 'lw', 'll'].forEach(id => { $(id).oninput = render; $(id).onchange = render; });
  $('lxoa').onclick = () => { ['lq', 'lky', 'lr', 'lw', 'll'].forEach(id => $(id).value = ''); sk = 'entry'; sd = -1; render(); };
  render();
}

/* ============================ TRANG BIỂU ĐỒ ============================ */
let _chartSym = null;
function openChart(sym){
  _chartSym = sym;
  // trang Chi tiet ma da ve roi thi phai ve lai cho ma moi (truoc day bam "Nen" lan hai van ra ma cu)
  try { if (secs.bieudo && secs.bieudo.rendered) { secs.bieudo.rendered = false; secs.bieudo.node.innerHTML = ''; } } catch (e) {}
  go('bieudo');
}

function pageChart(root){
  const L = D.lookup || {};
  const FS = D.funda || {};
  const cur = (_chartSym && (L[_chartSym] || D.candles[_chartSym])) ? _chartSym
            : ((danhMuc()[0] || {}).sym || (D.watchlist.members || [])[0] && D.watchlist.members[0].sym
               || Object.keys(D.candles || {})[0]);

  // dải mã bấm nhanh: đang cầm + watchlist + sổ tay
  const nhanh = [...new Set([
    ...danhMuc().map(x => x.sym),
    ...(D.watchlist.members || []).filter(m => m.status === 'đạt').map(m => m.sym),
    ...ghimThuCong().map(w => w.sym),
  ])].slice(0, 22);

  root.innerHTML = `
  <div class="ctdau">
    <div class="muted" style="font-size:12px;letter-spacing:.06em;font-weight:700">ĐANG THEO DÕI</div>
    <div id="ctChips" class="ctchips"></div>
  </div>
  <div class="ctbar">
    <input id="ctIn" list="ctList" class="fin" placeholder="Nhập mã rồi Enter…" maxlength="8" style="width:210px">
    <datalist id="ctList">${Object.keys(L).map(x => `<option value="${x}">`).join('')}</datalist>
    <div id="ctTen"></div>
  </div>
  <div id="ctBanner"></div>

  <div class="ctgrid">
    <div class="card" style="padding:12px 14px;min-width:0">
      <div class="tvhead">
        <div id="ctHead" class="ohlc"></div>
        <div class="cttools">
          <div class="seg tvseg">
            ${[['3M','3 tháng'],['1Y','1 năm'],['3Y','3 năm'],['5Y','5 năm'],['ALL','Tất cả']]
              .map(([k,l])=>`<button data-range="${k}"${k==='1Y'?' class="on"':''} title="${l}">${k}</button>`).join('')}
          </div>
          <div class="seg tvseg">
            <button data-ind="ma"  class="on" title="Đường trung bình 20/50/200 phiên">MA</button>
            <button data-ind="vol" class="on" title="Khối lượng khớp lệnh">KL</button>
            <button data-ind="bot" class="on" title="Phiên bot vào và thoát lệnh">Dấu bot</button>
          </div>
        </div>
      </div>
      <div id="tvWrap" class="tvwrap"><div id="tvBox"></div><div id="tvLoad" class="tvload">Đang lấy nến…</div></div>
      <div id="tvNote" class="muted" style="font-size:12px;margin-top:8px"></div>
    </div>
    <div class="card" id="ctBen" style="min-width:0"></div>
  </div>

  <h2 style="margin-top:26px">Tài chính — 12 quý gần nhất</h2>
  <div class="two">
    <div class="card"><h3 style="margin:0 0 4px">Tăng trưởng cùng kỳ</h3>
      <div class="legend" style="margin:0 0 4px"><span><i style="background:var(--s1)"></i>%YoY Doanh thu</span><span><i style="background:var(--s5)"></i>%YoY LNST</span></div>
      <div id="fc1"></div>
      
      <div id="fn1"></div></div>
    <div class="card"><h3 style="margin:0 0 4px">Quy mô</h3>
      <div class="legend" style="margin:0 0 4px"><span><i style="background:var(--s1)"></i>Doanh thu</span><span><i style="background:var(--s5)"></i>LNST</span></div>
      <div id="fc2"></div>
      <div id="fn2"></div></div>
  </div>
  <div class="two" style="margin-top:14px">
    <div class="card"><h3 style="margin:0 0 4px">ROE theo quý</h3><div id="fc3"></div><div id="fn3"></div></div>
    <div class="card"><h3 style="margin:0 0 4px">Định giá</h3>
      <div class="legend" style="margin:0 0 4px"><span><i style="background:var(--s1)"></i>P/E</span><span><i style="background:var(--s5)"></i>P/B</span></div>
      <div id="fc4"></div>
      </div>
  </div>

  <h2 style="margin-top:26px">Bảng số liệu quý</h2>
  <div id="ctBang"></div>
  `;

  const ve = sym => {
    _chartSym = sym;
    // Đổi mã ở đây thì thanh tra cứu trên đỉnh phải đổi theo, không thì hai chỗ
    // trên cùng một màn hình nói hai mã khác nhau (lỗi 18/09).
    if (typeof nsiChonMa === 'function') nsiChonMa(sym, 'trang');
    const x = L[sym], F = FS[sym];
    document.getElementById('ctTen').innerHTML = x
      ? `<b style="font-size:20px">${sym}</b> <span class="muted">— ${esc(x.name)} · ${esc(x.sector)} · ${esc(x.exch)}</span>`
      : `<b style="font-size:20px">${sym}</b> <span class="muted">— ngoài vũ trụ theo dõi</span>`;

    // ---- băng trạng thái + đèn tím ----
    let bn = '';
    if (x) bn += `<div class="ctstate ${x.state}"><b>${esc(x.label)}</b>` +
      (x.state === 'cho' ? ` <span class="muted">— đóng cửa phiên tới ≥ <b style="color:var(--text-primary)">${x.need_px}</b> · KL ≥ <b style="color:var(--text-primary)">${(x.need_vol/1e6).toFixed(1)} triệu cp</b></span>`
       : (x.miss && x.miss.length ? ` <span class="muted">— còn thiếu: ${x.miss.join(' · ')}</span>` : '')) + `</div>`;
    // Ma da nam giu: noi thang ra, keo doc dong trang thai o tren thanh "he thong
    // cham truot". Nguong o tren la cua PHIEN KE TIEP va danh cho mot lenh MUA MOI.
    if (F && F.tim && F.tim[F.tim.length - 1]) {
      bn += `<div class="ctstate tim"><b>ĐÈN TÍM — lãi đến từ hoạt động bất thường</b>
        <span class="muted">— ${F.vi[F.vi.length - 1]} (${F.q[F.q.length - 1]}).
        Lãi kiểu này không lặp lại ở quý sau, đừng chấm điểm doanh nghiệp bằng nó.</span></div>`;
    }
    if (x) bn += bangKiem(x, F);
    if (typeof obsDetail === 'function') bn += obsDetail(sym);   // lop quan sat R27A — chi doc
    document.getElementById('ctBanner').innerHTML = bn;

    // ---- biểu đồ nến tương tác ----
    // Zoom bằng con lăn, kéo ngang bằng chuột, chạm hai ngón trên điện thoại,
    // rê tới đâu đọc số tới đó. Nến lấy thẳng từ máy chủ dữ liệu VPS nên mã nào
    // cũng xem được, không phụ thuộc mã đó có nằm trong danh mục TradingView hay không.
    document.getElementById('ctBen').innerHTML = benPhai(sym, null);
    moBieuDo(sym);

    // ---- bốn biểu đồ cơ bản ----
    if (!F) {
      ['fc1','fc2','fc3','fc4'].forEach(k => document.getElementById(k).innerHTML =
        '<p class="muted" style="margin:0">Chưa có báo cáo tài chính cho mã này.</p>');
      document.getElementById('ctBang').innerHTML = '';
      ['fn1','fn2','fn3'].forEach(k => document.getElementById(k).innerHTML = '');
      return;
    }
    const q = F.q;
    cotKep(document.getElementById('fc1'), q,
      [{ name: '%YoY Doanh thu', color: '--s1', v: F.ry }, { name: '%YoY LNST', color: '--s5', v: F.ny }],
      { cap: 150, fmt: v => v.toFixed(0) + '%', fmtV: v => v.toFixed(1) + '%' });
    cotKep(document.getElementById('fc2'), q,
      [{ name: 'Doanh thu', color: '--s1', v: F.rev }, { name: 'LNST', color: '--s5', v: F.np }],
      { fmt: v => v >= 1000 ? (v/1000).toFixed(0) + 'k' : v.toFixed(0), fmtV: v => num(v,0) + ' tỷ' });
    const roeCo = F.roe.filter(v => v != null);
    duongQuy(document.getElementById('fc3'), q, [{ name: 'ROE', color: '--s1', v: F.roe }],
      { fmt: v => v.toFixed(1), tb: roeCo.length ? roeCo.reduce((a,b)=>a+b,0)/roeCo.length : null });
    duongQuy(document.getElementById('fc4'), q,
      [{ name: 'P/E', color: '--s1', v: F.pe }, { name: 'P/B', color: '--s5', v: F.pb }],
      { fmt: v => v.toFixed(2), zero: true });

    // ---- một câu nhận xét cho mỗi biểu đồ, rút từ chính chuỗi 12 quý ----
    const cuoi = a => { for (let i = a.length - 1; i >= 0; i--) if (a[i] != null) return a[i]; return null; };
    const nyC = cuoi(F.ny), revC = cuoi(F.rev);
    const nyCo = F.ny.filter(v => v != null);
    const hangNy = nyCo.filter(v => v > nyC).length + 1;   // 1 = cao nhất chuỗi
    const dinh = Math.max(...F.rev.filter(v => v != null));
    document.getElementById('fn1').innerHTML = nyC == null ? '' :
      ``;
    document.getElementById('fn2').innerHTML = revC == null ? '' :
      ``;
    const roeC = cuoi(F.roe), roeTb = roeCo.length ? roeCo.reduce((a,b)=>a+b,0)/roeCo.length : null;
    document.getElementById('fn3').innerHTML = (roeC == null || roeTb == null) ? '' :
      ``;

    // ---- bảng số liệu ----
    const xu = i => {
      if (F.ny[i] == null || i === 0 || F.ny[i-1] == null) return '<span class="muted">—</span>';
      return F.ny[i] >= F.ny[i-1] ? '<span class="pos">tăng tốc</span>' : '<span class="neg">giảm tốc</span>';
    };
    const hang = (ten, arr, f, mau) => `<tr><td>${ten}</td>${arr.map((v,i) =>
      `<td style="text-align:right${F.tim[i] ? ';background:color-mix(in srgb,var(--s7) 12%,transparent)' : ''}"
        class="${mau && v != null ? cls(v) : ''}">${v == null ? '—' : f(v)}</td>`).join('')}</tr>`;
    document.getElementById('ctBang').innerHTML = `<div class="card tblwrap"><table><thead><tr>
      <th>Quý</th>${q.map((x2,i) => `<th style="text-align:right">${x2}${F.tim[i] ? ' <span title="Lãi từ hoạt động bất thường" style="color:var(--s7)">●</span>' : ''}</th>`).join('')}
      </tr></thead><tbody>
      ${hang('Doanh thu (tỷ đồng)', F.rev, v => num(v,0))}
      ${hang('LNST (tỷ đồng)', F.np, v => num(v,0))}
      ${hang('%YoY Doanh thu', F.ry, v => (v>=0?'+':'')+v.toFixed(1), true)}
      ${hang('%YoY LNST', F.ny, v => (v>=0?'+':'')+v.toFixed(1), true)}
      ${hang('ROE (%)', F.roe, v => v.toFixed(1))}
      ${hang('P/E (lần)', F.pe, v => v.toFixed(2))}
      ${hang('P/B (lần)', F.pb, v => v.toFixed(2))}
      <tr><td>Xu hướng LN</td>${q.map((_,i) => `<td style="text-align:right">${xu(i)}</td>`).join('')}</tr>
      </tbody></table></div>
      ${F.tim.some(t => t) ? `` : ''}`;
  };

  const chips = () => document.getElementById('ctChips').innerHTML = nhanh.map(s2 => {
    const r = (NSI.rt || {})[s2];
    const p = r && r.ref ? (r.price / r.ref - 1) * 100 : null;
    return `<button class="ctchip${s2 === _chartSym ? ' on' : ''}" data-s="${s2}">${s2}${
      p == null ? '' : ` <span class="${p >= 0 ? 'pos' : 'neg'}">${p >= 0 ? '+' : ''}${p.toFixed(1)}%</span>`}</button>`;
  }).join('');
  const noiChip = () => document.getElementById('ctChips').querySelectorAll('[data-s]')
    .forEach(b => b.onclick = () => { ve(b.dataset.s); chips(); noiChip(); });
  chips(); noiChip();

  // khung thời gian
  root.querySelectorAll('[data-range]').forEach(b => b.onclick = () => {
    root.querySelectorAll('[data-range]').forEach(z => z.classList.toggle('on', z === b));
    CT.range = b.dataset.range;
    apKhungThoiGian();
  });
  // bật/tắt chỉ báo
  root.querySelectorAll('[data-ind]').forEach(b => b.onclick = () => {
    const k = b.dataset.ind;
    CT.ind[k] = !CT.ind[k];
    b.classList.toggle('on', CT.ind[k]);
    apChiBao();
  });

  const inp = document.getElementById('ctIn');
  inp.onkeydown = e => {
    if (e.key !== 'Enter') return;
    const v = (inp.value || '').trim().toUpperCase();
    if (v) { ve(v); chips(); noiChip(); inp.value = ''; }
  };
  if (cur) ve(cur);
}

/* bảng chỉ số bên phải biểu đồ */
function benPhai(sym, bars) {
  const x = (D.lookup || {})[sym];
  const F = (D.funda || {})[sym];
  const cuoi = a => { if (!a) return null; for (let i = a.length - 1; i >= 0; i--) if (a[i] != null) return a[i]; return null; };
  const r = (NSI.rt || {})[sym];
  const gia = r && r.price ? r.price / 1000 : (bars ? bars[bars.length - 1][4] : (x ? x.price : null));
  const pc0 = r && r.ref ? (r.price / r.ref - 1) * 100
            : (bars && bars.length > 1 ? (bars[bars.length-1][4] / bars[bars.length-2][4] - 1) * 100 : null);
  const d = [
    ['TB GTGD 20 phiên', x ? `${x.gtgd} tỷ` : '—'],
    ['P/E', F ? (cuoi(F.pe) ?? '—') : '—'],
    ['P/B', F ? (cuoi(F.pb) ?? '—') : '—'],
    ['ROE', F && cuoi(F.roe) != null ? cuoi(F.roe).toFixed(1) + '%' : '—'],
    ['RS (sức mạnh giá)', x && x.rs != null ? x.rs : '—'],
    ['RSI(14)', bars ? (rsi14(bars) ?? '—') : '—'],
    // Thang diem THAT la 100, khong phai 105. Cong lai: C1 15 + C2 15 + C3 5 +
    // A1 10 + A2 10 + N 10 + S 5 + L 15 + I 10 = 95 co dinh, cong Mom toi da 5
    // (Mom = round(5 x mom3) ma mom3 = pct_rank nam trong [0,1]). Truoc day ghi
    // 105 vi tuong Mom toi da 10. Diem cao nhat thuc te trong 1.213 ma la 89,2.
    ['Điểm CANSLIM', x ? `${x.score}/100` : '—'],
    ['Nền 30 phiên', x && x.base != null ? x.base + '%' : '—'],
    ['+/− Doanh thu (cùng kỳ)', F && cuoi(F.ry) != null ? `<span class="${cls(cuoi(F.ry))}">${cuoi(F.ry) >= 0 ? '+' : ''}${cuoi(F.ry).toFixed(1)}%</span>` : '—'],
    ['+/− LNST (cùng kỳ)', F && cuoi(F.ny) != null ? `<span class="${cls(cuoi(F.ny))}">${cuoi(F.ny) >= 0 ? '+' : ''}${cuoi(F.ny).toFixed(1)}%</span>` : '—'],
  ];
  return `<div style="display:flex;justify-content:space-between;align-items:baseline">
      <b style="font-size:17px">${sym}</b><span class="muted" style="font-size:12px">${x ? x.exch : ''}</span></div>
    <div style="font-size:34px;font-weight:750;line-height:1.15;margin-top:6px">${gia != null ? (+gia).toFixed(2) : '—'}
      ${pc0 != null ? `<span style="font-size:17px" class="${pc0 >= 0 ? 'pos' : 'neg'}">${pc0 >= 0 ? '+' : ''}${pc0.toFixed(2)}%</span>` : ''}</div>
    <div class="muted" style="font-size:12.5px;margin-bottom:12px">${
      (NSI.rt || {})[sym] ? 'real-time' : 'giá đóng cửa gần nhất'}</div>
    <div class="muted" style="font-size:12px;letter-spacing:.06em;font-weight:700;margin-bottom:6px">CHỈ SỐ CƠ BẢN</div>
    <table style="width:100%">${d.map(([k, v]) =>
      `<tr><td class="muted" style="font-size:13px;padding:5px 0">${k}</td>
       <td style="text-align:right;font-weight:640;padding:5px 0">${v}</td></tr>`).join('')}</table>
    `;
}

/* ============================================================================
   BIỂU ĐỒ NẾN CÓ ZOOM — lăn chuột để phóng to, kéo ngang để trượt thời gian.

   Vẽ bằng canvas chứ không phải SVG: 340 cây nến × mỗi lần kéo chuột là hàng
   nghìn phép vẽ, SVG sẽ giật. Canvas vẽ lại toàn khung trong ~2ms.

   Không dùng thư viện ngoài. Trang này là MỘT file tự chứa — nhét thêm thư viện
   biểu đồ vào là mất tính chất đó, và mất luôn khả năng mở bằng file trên máy.
   ========================================================================== */
const NEN = { host: null, bars: [], marks: [], i0: 0, i1: 0, hover: null, keo: null };

function nenMau(k) { return CV(k); }

function veNen(host, bars, marks) {
  if (!host) return;
  NEN.host = host; NEN.bars = bars || []; NEN.marks = marks || [];
  const n = NEN.bars.length;
  if (!n) { host.innerHTML = '<p class="muted" style="margin:0">Chưa có dữ liệu nến cho mã này.</p>'; return; }
  NEN.i0 = Math.max(0, n - 180); NEN.i1 = n - 1;

  host.innerHTML = `
    <div class="nenwrap" style="position:relative">
      <canvas id="nenCv" style="width:100%;height:420px;display:block;cursor:crosshair"></canvas>
      <div id="nenTip" class="muted" style="font-size:12.5px;margin-top:6px;min-height:18px"></div>
    </div>`;
  const cv = host.querySelector('#nenCv');

  const veLai = () => nenVe(cv);
  // Mỗi lần đổi mã là dựng lại canvas. Không gỡ cái cũ thì sau hai chục lần đổi mã
  // sẽ có hai chục ResizeObserver cùng vẽ lên một khung — máy nóng lên vô ích.
  if (NEN.ro) NEN.ro.disconnect();
  NEN.ro = new ResizeObserver(veLai);
  NEN.ro.observe(cv);
  if (!NEN.daNoiMouseUp) {
    NEN.daNoiMouseUp = true;
    window.addEventListener('mouseup', () => {
      NEN.keo = null;
      const c = document.getElementById('nenCv');
      if (c) c.style.cursor = 'crosshair';
    });
  }

  cv.onwheel = e => {
    e.preventDefault();
    const r = cv.getBoundingClientRect();
    const p = (e.clientX - r.left) / r.width;                 // vị trí con trỏ, 0..1
    const rong = NEN.i1 - NEN.i0 + 1;
    const moi = Math.round(rong * (e.deltaY > 0 ? 1.18 : 0.85));
    const rong2 = Math.max(25, Math.min(NEN.bars.length, moi));
    const neo = NEN.i0 + p * rong;                            // giữ nguyên điểm dưới con trỏ
    let a = Math.round(neo - p * rong2);
    a = Math.max(0, Math.min(NEN.bars.length - rong2, a));
    NEN.i0 = a; NEN.i1 = a + rong2 - 1;
    veLai();
  };
  cv.onmousedown = e => { NEN.keo = { x: e.clientX, i0: NEN.i0, i1: NEN.i1 }; cv.style.cursor = 'grabbing'; };
  cv.onmousemove = e => {
    const r = cv.getBoundingClientRect();
    if (NEN.keo) {
      const rong = NEN.keo.i1 - NEN.keo.i0 + 1;
      const d = Math.round((NEN.keo.x - e.clientX) / r.width * rong);
      let a = Math.max(0, Math.min(NEN.bars.length - rong, NEN.keo.i0 + d));
      NEN.i0 = a; NEN.i1 = a + rong - 1;
    } else {
      NEN.hover = { x: e.clientX - r.left, y: e.clientY - r.top };
    }
    veLai();
  };
  cv.onmouseleave = () => { NEN.hover = null; veLai(); };
  // trên điện thoại: một ngón để trượt, hai ngón để phóng
  cv.ontouchstart = e => { if (e.touches.length === 1) NEN.keo = { x: e.touches[0].clientX, i0: NEN.i0, i1: NEN.i1 }; };
  cv.ontouchmove = e => {
    if (!NEN.keo || e.touches.length !== 1) return;
    e.preventDefault();
    const r = cv.getBoundingClientRect(), rong = NEN.keo.i1 - NEN.keo.i0 + 1;
    const d = Math.round((NEN.keo.x - e.touches[0].clientX) / r.width * rong);
    let a = Math.max(0, Math.min(NEN.bars.length - rong, NEN.keo.i0 + d));
    NEN.i0 = a; NEN.i1 = a + rong - 1; veLai();
  };
  cv.ontouchend = () => { NEN.keo = null; };

  veLai();
}

function nenVe(cv) {
  const bars = NEN.bars, i0 = NEN.i0, i1 = NEN.i1;
  const view = bars.slice(i0, i1 + 1), n = view.length;
  if (!n) return;
  const dpr = window.devicePixelRatio || 1;
  const W = cv.clientWidth, H = cv.clientHeight;
  cv.width = W * dpr; cv.height = H * dpr;
  const g = cv.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, W, H);

  const PL = 8, PR = 56, PT = 10, PB = 20, HV = 62;
  const HG = H - PT - PB - HV - 6;
  const hi = Math.max(...view.map(b => b[2])), lo = Math.min(...view.map(b => b[3]));
  const pad = (hi - lo) * 0.08 || 1, y0 = lo - pad, y1 = hi + pad;
  const X = i => PL + (i + 0.5) * (W - PL - PR) / n;
  const Y = p => PT + (1 - (p - y0) / (y1 - y0)) * HG;
  const vmax = Math.max(...view.map(b => b[5])) || 1;
  const VY = v => H - PB - (v / vmax) * HV;
  const bw = Math.max(1, (W - PL - PR) / n * 0.66);

  const cLine = nenMau('--line'), cMuted = nenMau('--text-muted');
  const cUp = nenMau('--s3'), cDn = nenMau('--s2'), cMa = nenMau('--s1');
  const cBuy = nenMau('--good'), cSell = nenMau('--critical');
  g.font = '11px system-ui, sans-serif';

  // lưới giá + nhãn bên phải, đúng kiểu bảng điện
  g.strokeStyle = cLine; g.fillStyle = cMuted; g.lineWidth = 1;
  for (let k = 0; k <= 4; k++) {
    const p = y0 + (y1 - y0) * k / 4, yy = Math.round(Y(p)) + 0.5;
    g.beginPath(); g.moveTo(PL, yy); g.lineTo(W - PR, yy); g.stroke();
    g.textAlign = 'left'; g.fillText(p.toFixed(2), W - PR + 6, yy + 3.5);
  }

  // khối lượng
  view.forEach((b, i) => {
    g.fillStyle = b[4] >= b[1] ? cUp : cDn; g.globalAlpha = .3;
    g.fillRect(X(i) - bw / 2, VY(b[5]), bw, H - PB - VY(b[5]));
  });
  g.globalAlpha = 1;

  // MA20 tính trên TOÀN chuỗi rồi mới cắt — cắt trước thì 19 nến đầu khung sẽ trống
  const ma = [];
  for (let i = 0; i < bars.length; i++) {
    if (i < 19) { ma.push(null); continue; }
    let s = 0; for (let k = i - 19; k <= i; k++) s += bars[k][4];
    ma.push(s / 20);
  }
  g.strokeStyle = cMa; g.lineWidth = 1.6; g.beginPath();
  let bat = false;
  view.forEach((b, i) => {
    const v = ma[i0 + i]; if (v == null) return;
    bat ? g.lineTo(X(i), Y(v)) : g.moveTo(X(i), Y(v)); bat = true;
  });
  g.stroke();

  // nến
  view.forEach((b, i) => {
    const up = b[4] >= b[1], col = up ? cUp : cDn;
    g.strokeStyle = col; g.fillStyle = col; g.lineWidth = 1;
    const x = Math.round(X(i)) + .5;
    g.beginPath(); g.moveTo(x, Y(b[2])); g.lineTo(x, Y(b[3])); g.stroke();
    const o = Y(b[1]), c = Y(b[4]);
    g.fillRect(X(i) - bw / 2, Math.min(o, c), bw, Math.max(1.2, Math.abs(c - o)));
  });

  // dấu mua / bán của hệ thống
  const idx = {}; view.forEach((b, i) => idx[b[0]] = i);
  const daVe = new Set();
  (NEN.marks || []).forEach(m => {
    const i = idx[m.d]; if (i === undefined) return;
    const k = m.t + m.d; if (daVe.has(k)) return; daVe.add(k);
    const mua = m.t === 'B';
    const y = mua ? Y(view[i][3]) + 16 : Y(view[i][2]) - 16;
    g.fillStyle = mua ? cBuy : cSell;
    g.beginPath();
    g.moveTo(X(i), mua ? y - 9 : y + 9);
    g.lineTo(X(i) - 5, y); g.lineTo(X(i) + 5, y); g.closePath(); g.fill();
    g.textAlign = 'center'; g.font = 'bold 11px system-ui, sans-serif';
    g.fillText(mua ? 'B' : 'S', X(i), mua ? y + 12 : y - 4);
    g.font = '11px system-ui, sans-serif';
  });

  // trục thời gian
  g.fillStyle = cMuted; g.textAlign = 'center';
  const buoc = Math.max(1, Math.floor(n / 6));
  for (let i = 0; i < n; i += buoc) {
    const x = Math.max(X(i), PL + 22);      // nhãn đầu tiên hay bị cắt mất ở mép trái
    g.fillText(view[i][0].slice(2, 7), x, H - 5);
  }

  // thanh ngang giá đóng cửa gần nhất
  const last = view[n - 1];
  g.strokeStyle = cMa; g.setLineDash([4, 4]); g.lineWidth = 1;
  g.beginPath(); g.moveTo(PL, Y(last[4])); g.lineTo(W - PR, Y(last[4])); g.stroke();
  g.setLineDash([]);
  g.fillStyle = cMa; g.fillRect(W - PR + 2, Y(last[4]) - 9, PR - 4, 18);
  g.fillStyle = nenMau('--bg'); g.textAlign = 'center';
  g.fillText(last[4].toFixed(2), W - PR / 2, Y(last[4]) + 3.5);

  // chữ thập + số liệu phiên đang rê chuột
  const tip = NEN.host && NEN.host.querySelector('#nenTip');
  if (NEN.hover && NEN.hover.x > PL && NEN.hover.x < W - PR) {
    const i = Math.max(0, Math.min(n - 1, Math.round((NEN.hover.x - PL) / (W - PL - PR) * n - 0.5)));
    const b = view[i];
    g.strokeStyle = cMuted; g.globalAlpha = .55; g.setLineDash([3, 3]);
    g.beginPath(); g.moveTo(X(i), PT); g.lineTo(X(i), H - PB); g.stroke();
    g.setLineDash([]); g.globalAlpha = 1;
    if (tip) {
      const pc0 = i > 0 ? (b[4] / view[i - 1][4] - 1) * 100 : 0;
      tip.innerHTML = `<b>${b[0]}</b> · M ${b[1].toFixed(2)} · C ${b[2].toFixed(2)}
        · T ${b[3].toFixed(2)} · Đ <b style="color:var(--text-primary)">${b[4].toFixed(2)}</b>
        <span class="${pc0 >= 0 ? 'pos' : 'neg'}">${pc0 >= 0 ? '+' : ''}${pc0.toFixed(2)}%</span>
        · KL ${(b[5] / 1e6).toFixed(2)} triệu`;
    }
  } else if (tip) {
    tip.innerHTML = `${n} phiên đang hiện · <b>lăn chuột</b> để phóng to, <b>kéo ngang</b> để trượt thời gian
      · <b style="color:var(--good)">B</b> = hệ thống mua, <b style="color:var(--critical)">S</b> = hệ thống bán`;
  }
}

/* ============================================================================
   BỐN BIỂU ĐỒ CƠ BẢN — 12 quý gần nhất

   Cột mờ = vượt biên ±150%, thường do nền cùng kỳ gần bằng không. Vẽ đúng tỷ lệ
   thì một cột +3000% sẽ đè bẹp mười một cột còn lại thành đường kẻ. Cắt biên và
   nói rõ là cắt, rồi để số thật ở bảng bên dưới.
   ========================================================================== */
/* ============================================================================
   HAI BIỂU ĐỒ CỦA KHỐI "TÀI CHÍNH — 12 QUÝ GẦN NHẤT"

   LỖI CŨ, đã sửa ở đây. Cả hai hàm dùng viewBox 1000×260 kèm
   `preserveAspectRatio="none"`, rồi nhét vào ô rộng ~370px cao 210px. Trình duyệt
   được lệnh KHÔNG giữ tỷ lệ, nên nó nén ngang 0,37 lần mà chỉ nén dọc 0,81 lần —
   tức mọi chữ bị BÓP NGANG KÉO DỌC gấp hơn hai lần. Đó chính là thứ trông như
   "lỗi font": không phải font sai, mà là chữ bị biến dạng.
   Chữa: bỏ `preserveAspectRatio="none"`, để viewBox đúng tỷ lệ khung thật, và
   dùng cỡ chữ bình thường (11–13) thay vì 23–28 phóng đại để bù méo.

   LỖI THỨ HAI: nhãn giá trị cuối chuỗi đè lên nhau và đè lên nhãn "TB" —
   ROE hiện "5.8" chồng "6.6", Định giá hiện "16.81" bị đường trung bình gạch ngang.
   Chữa: đẩy nhãn tránh nhau theo chiều dọc, và cho mỗi nhãn một viền nền mỏng.
   ========================================================================== */

const FCW = 560, FCH = 260;          // khung thật của biểu đồ, giữ đúng tỷ lệ

function cotKep(host, labels, series, opt = {}) {
  const W = FCW, H = FCH, PL = 54, PR = 10, PT = 14, PB = 34;
  const tran = opt.cap || null;
  const vals = series.flatMap(s => s.v).filter(v => v != null)
    .map(v => tran ? Math.max(-tran, Math.min(tran, v)) : v);
  if (!vals.length) { host.innerHTML = '<p class="muted" style="margin:0">Chưa có số liệu.</p>'; return; }
  let hi = Math.max(...vals, 0), lo = Math.min(...vals, 0);
  const pad = (hi - lo) * 0.12 || 1;
  hi += pad;
  // Chỉ nới mép dưới khi thật sự có giá trị âm. Không thì trục hiện "−2427 tỷ
  // doanh thu" — một con số không tồn tại, chỉ là khoảng đệm bị dán nhãn.
  lo = lo < 0 ? lo - pad : 0;
  const n = labels.length, nS = series.length;
  const X = i => PL + (i + 0.5) * (W - PL - PR) / n;
  const Y = v => PT + (1 - (v - lo) / (hi - lo)) * (H - PT - PB);
  const bw = (W - PL - PR) / n * 0.66 / nS;

  let s = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" font-family="inherit">`;
  for (let k = 0; k <= 3; k++) {
    const v = lo + (hi - lo) * k / 3, y = Y(v);
    s += `<line x1="${PL}" x2="${W - PR}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="1"/>
          <text x="${PL - 7}" y="${y + 4}" text-anchor="end" font-size="11" fill="var(--text-muted)">${(opt.fmt || (x => x.toFixed(0)))(v)}</text>`;
  }
  if (lo < 0 && hi > 0) s += `<line x1="${PL}" x2="${W - PR}" y1="${Y(0)}" y2="${Y(0)}" stroke="var(--text-muted)" stroke-width="1.2" opacity=".55"/>`;
  series.forEach((se, k) => {
    se.v.forEach((v0, i) => {
      if (v0 == null) return;
      const cut = tran && Math.abs(v0) > tran;
      const v = cut ? Math.sign(v0) * tran : v0;
      const x = X(i) - (nS * bw) / 2 + k * bw;
      const y = Math.min(Y(v), Y(0)), h = Math.max(1.5, Math.abs(Y(v) - Y(0)));
      s += `<rect x="${x}" y="${y}" width="${bw * 0.86}" height="${h}" fill="var(${se.color})" rx="1"
             opacity="${cut ? .38 : .92}"><title>${labels[i]} · ${esc(se.name)}: ${(opt.fmtV || opt.fmt || (x2 => x2.toFixed(1)))(v0)}</title></rect>`;
    });
  });
  // Nhãn quý: 12 nhãn trong 560 đơn vị thì chật, nên xoay nghiêng cho dễ đọc
  // thay vì để chúng dính vào nhau.
  labels.forEach((l, i) => {
    s += `<text x="${X(i)}" y="${H - PB + 16}" text-anchor="end" font-size="10.5" fill="var(--text-muted)"
           transform="rotate(-38 ${X(i)} ${H - PB + 16})">${l}</text>`;
  });
  s += '</svg>';
  host.innerHTML = s;
}

function duongQuy(host, labels, series, opt = {}) {
  const W = FCW, H = FCH, PL = 54, PR = 14, PT = 18, PB = 34;
  const vals = series.flatMap(s => s.v).filter(v => v != null);
  if (!vals.length) { host.innerHTML = '<p class="muted" style="margin:0">Chưa có số liệu.</p>'; return; }
  let hi = Math.max(...vals), lo = Math.min(...vals);
  const pad = (hi - lo) * 0.18 || Math.abs(hi) * 0.1 || 1;
  hi += pad;
  lo = (opt.zero && lo - pad < 0) ? 0 : lo - pad;
  const n = labels.length;
  const X = i => PL + (i + 0.5) * (W - PL - PR) / n;
  const Y = v => PT + (1 - (v - lo) / (hi - lo)) * (H - PT - PB);
  const f = opt.fmt || (x => x.toFixed(1));

  let s = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" font-family="inherit">`;
  for (let k = 0; k <= 3; k++) {
    const v = lo + (hi - lo) * k / 3, y = Y(v);
    s += `<line x1="${PL}" x2="${W - PR}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="1"/>
          <text x="${PL - 7}" y="${y + 4}" text-anchor="end" font-size="11" fill="var(--text-muted)">${f(v)}</text>`;
  }
  // Gom mọi nhãn nổi vào một danh sách rồi mới đẩy tránh nhau — vẽ ngay tại chỗ
  // là cách sinh ra cảnh "5.8" nằm đè lên "6.6".
  const nhan = [];
  if (opt.tb != null) {
    s += `<line x1="${PL}" x2="${W - PR}" y1="${Y(opt.tb)}" y2="${Y(opt.tb)}" stroke="var(--text-muted)"
           stroke-width="1.1" stroke-dasharray="5 4" opacity=".65"/>`;
    nhan.push({ y: Y(opt.tb) - 6, x: W - PR - 3, neo: 'end', chu: 'TB ' + f(opt.tb), mau: 'var(--text-muted)', dam: 600 });
  }
  series.forEach(se => {
    let d = '', bat = false;
    se.v.forEach((v, i) => { if (v == null) return; d += (bat ? 'L' : 'M') + X(i) + ' ' + Y(v); bat = true; });
    if (d) s += `<path d="${d}" fill="none" stroke="var(${se.color})" stroke-width="1.9" stroke-linejoin="round"/>`;
    se.v.forEach((v, i) => { if (v != null) s += `<circle cx="${X(i)}" cy="${Y(v)}" r="2.6" fill="var(${se.color})"><title>${labels[i]} · ${esc(se.name)}: ${f(v)}</title></circle>`; });
    const cuoi = [...se.v].reverse().find(v => v != null);
    if (cuoi != null) {
      const i = se.v.lastIndexOf(cuoi);
      nhan.push({ y: Y(cuoi) - 8, x: Math.min(X(i) + 6, W - PR), neo: 'end', chu: f(cuoi), mau: `var(${se.color})`, dam: 700 });
    }
  });
  // đẩy tránh nhau: nhãn nào cách nhãn trước dưới 13 đơn vị thì đùn xuống
  nhan.sort((a, b) => a.y - b.y);
  for (let k = 1; k < nhan.length; k++) {
    if (nhan[k].y - nhan[k - 1].y < 13) nhan[k].y = nhan[k - 1].y + 13;
  }
  nhan.forEach(t => {
    // viền nền cùng màu trang: chữ nằm trên đường kẻ vẫn đọc được
    s += `<text x="${t.x}" y="${Math.min(t.y, H - PB - 2)}" text-anchor="${t.neo}" font-size="12" font-weight="${t.dam}"
           fill="${t.mau}" stroke="var(--surface-1)" stroke-width="3.2" paint-order="stroke"
           stroke-linejoin="round">${t.chu}</text>`;
  });
  labels.forEach((l, i) => {
    s += `<text x="${X(i)}" y="${H - PB + 16}" text-anchor="end" font-size="10.5" fill="var(--text-muted)"
           transform="rotate(-38 ${X(i)} ${H - PB + 16})">${l}</text>`;
  });
  s += '</svg>';
  host.innerHTML = s;
}

/* RSI 14 phiên — chỉ để tham khảo, hệ thống không dùng chỉ báo này để vào lệnh */
function rsi14(bars) {
  if (!bars || bars.length < 15) return null;
  let up = 0, dn = 0;
  for (let i = bars.length - 14; i < bars.length; i++) {
    const d = bars[i][4] - bars[i - 1][4];
    if (d >= 0) up += d; else dn -= d;
  }
  if (up + dn === 0) return 50;
  return Math.round(100 * up / (up + dn));
}

/* ============================================================================
   BIỂU ĐỒ NẾN TƯƠNG TÁC

   Vì sao bỏ iframe TradingView. Hai lý do, cả hai đều là lỗi thật anh Sơn gặp:
     1. TradingView KHÔNG có đủ mã sàn Việt Nam. HOSE:ORS báo "Mã giao dịch này
        chỉ có trên TradingView" — tức là ô biểu đồ trống trơn. Một biểu đồ chỉ
        chạy với mã lớn thì vô dụng với hệ thống này, vì hệ thống soi cả TOP
        thanh khoản chứ không chỉ vài chục mã đầu bảng.
     2. Widget đó dựng chữ tiếng Việt hỏng ("Oợ Hợ Lợ Cợ ợ").

   Thay bằng Lightweight Charts — cùng nhà TradingView làm ra, mã nguồn mở,
   nhúng thẳng vào trang. Đổi lại: dữ liệu do TA cấp, nên mã nào cũng vẽ được.

   ĐÂY LÀ BIỂU ĐỒ CHẠY THẬT, KHÔNG PHẢI ẢNH:
     · con lăn chuột = phóng to thu nhỏ theo trục thời gian
     · kéo chuột ngang = trượt qua lại lịch sử
     · chạm hai ngón trên điện thoại = phóng to
     · rê tới đâu, dòng OHLC trên đầu đọc số phiên đó
     · bấm đúp = về khung mặc định
     · kéo trục giá bên phải = giãn/nén theo chiều dọc

   NGUỒN NẾN, theo thứ tự thử:
     1. histdatafeed.vps.com.vn  — có nhãn CORS, ~6 năm, mọi mã
     2. dchart-api.vndirect.com.vn — dự phòng, cũng có nhãn CORS
     3. D.candles nhúng sẵn trong trang — dùng khi mất mạng
   ========================================================================== */

const CT = { chart: null, nen: null, kl: null, ma: {}, sym: null, bars: [],
             range: '1Y', ind: { ma: true, vol: true, bot: true }, dem: {} };

const CT_NGUON = [
  { ten: 'VPS', url: (s, f, t) =>
      `https://histdatafeed.vps.com.vn/tradingview/history?symbol=${s}&resolution=D&from=${f}&to=${t}`,
    doc: j => (j && j.s === 'ok' && j.t) ? j : null },
  { ten: 'VNDIRECT', url: (s, f, t) =>
      `https://dchart-api.vndirect.com.vn/dchart/history?resolution=D&symbol=${s}&from=${f}&to=${t}`,
    doc: j => (j && j.t && j.t.length) ? j : null },
];

/* đổi khuôn UDF (mảng song song) sang khuôn Lightweight Charts */
function udfSangNen(j) {
  const o = [];
  for (let i = 0; i < j.t.length; i++) {
    const c = +j.c[i];
    if (!c) continue;
    // Lightweight Charts nhận ngày dạng 'YYYY-MM-DD'. Mốc thời gian trả về là
    // giờ quốc tế, nên phải cộng bù 7 tiếng trước khi cắt, không thì phiên nào
    // cũng lùi một ngày.
    o.push({ time: new Date((j.t[i] + 25200) * 1000).toISOString().slice(0, 10),
             open: +j.o[i], high: +j.h[i], low: +j.l[i], close: c, value: +j.v[i] });
  }
  o.sort((a, b) => a.time < b.time ? -1 : 1);
  return o;
}

async function layNen(sym) {
  if (CT.dem[sym]) return CT.dem[sym];
  const t = Math.floor(Date.now() / 1000), f = t - 86400 * 365 * 8;
  for (const ng of CT_NGUON) {
    try {
      const r = await fetch(ng.url(sym, f, t), { cache: 'no-store' });
      if (!r.ok) continue;
      const j = ng.doc(await r.json());
      if (!j) continue;
      const bars = udfSangNen(j);
      if (bars.length > 30) { CT.dem[sym] = bars; CT.nguon = ng.ten; return bars; }
    } catch (e) { /* nguồn này hỏng thì thử nguồn sau */ }
  }
  // hết mạng: dùng nến nhúng sẵn trong trang, nếu mã đó có
  const em = (D.candles || {})[sym];
  if (em && em.bars && em.bars.length) {
    CT.nguon = 'nhúng sẵn';
    const bars = em.bars.map(b => ({ time: b[0], open: b[1], high: b[2], low: b[3], close: b[4], value: b[5] }));
    CT.dem[sym] = bars;
    return bars;
  }
  return null;
}

function ma(bars, n) {
  const o = [];
  let s = 0;
  for (let i = 0; i < bars.length; i++) {
    s += bars[i].close;
    if (i >= n) s -= bars[i - n].close;
    if (i >= n - 1) o.push({ time: bars[i].time, value: +(s / n).toFixed(3) });
  }
  return o;
}

function mauCT() {
  const s = getComputedStyle(document.documentElement);
  const g = k => s.getPropertyValue(k).trim();
  const toi = document.documentElement.getAttribute('data-theme') !== 'light';
  return { len: g('--s3') || '#199e70', giam: g('--s2') || '#d95926',
           chu: g('--text-secondary') || '#c3c2b7', mo: g('--text-muted') || '#8b8a80',
           duong: g('--line') || '#33322f', nen: 'transparent',
           s1: g('--s1') || '#3987e5', s4: g('--s4') || '#c98500', s7: g('--s7') || '#9085e9',
           toi };
}

async function moBieuDo(sym) {
  const hop = document.getElementById('tvBox'), tai = document.getElementById('tvLoad');
  if (!hop) return;
  CT.sym = sym;
  if (CT.chart) { try { CT.chart.remove(); } catch (e) {} CT.chart = null; }
  hop.innerHTML = '';
  if (tai) { tai.style.display = ''; tai.textContent = 'Đang lấy nến…'; }

  if (typeof LightweightCharts === 'undefined') {
    if (tai) tai.innerHTML = '<b>Không nạp được thư viện biểu đồ.</b> Tải lại trang.';
    return;
  }

  const bars = await layNen(sym);
  if (CT.sym !== sym) return;                  // anh Sơn đã đổi mã trong lúc chờ
  if (!bars) {
    if (tai) tai.innerHTML = `<b>Không lấy được nến của ${sym}.</b><br>
      <span class="muted">Cả hai máy chủ dữ liệu đều không trả lời. Thử lại sau, hoặc kiểm tra mạng.</span>`;
    return;
  }
  if (tai) tai.style.display = 'none';

  const M = mauCT();
  const c = LightweightCharts.createChart(hop, {
    layout: { background: { type: 'solid', color: 'transparent' }, textColor: M.chu,
              fontFamily: 'Inter,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif', fontSize: 11 },
    grid: { vertLines: { color: M.duong }, horzLines: { color: M.duong } },
    rightPriceScale: { borderColor: M.duong, scaleMargins: { top: 0.08, bottom: 0.26 } },
    // rightOffset 12: chừa chỗ trống bên phải để nhãn "MUA 14.05" của phiên cuối
    // không bị mép biểu đồ cắt cụt.
    timeScale: { borderColor: M.duong, rightOffset: 12, minBarSpacing: 0.4 },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { color: M.mo, width: 1, style: 3, labelBackgroundColor: M.toi ? '#333' : '#555' },
      horzLine: { color: M.mo, width: 1, style: 3, labelBackgroundColor: M.toi ? '#333' : '#555' },
    },
    localization: {
      locale: 'vi-VN',
      priceFormatter: p => p.toFixed(2),
      timeFormatter: t => t,
    },
    handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
    handleScale:  { mouseWheel: true, pinch: true, axisPressedMouseMove: true, axisDoubleClickReset: true },
    autoSize: true,
  });
  CT.chart = c;

  CT.nen = c.addCandlestickSeries({
    upColor: M.len, downColor: M.giam, borderUpColor: M.len, borderDownColor: M.giam,
    wickUpColor: M.len, wickDownColor: M.giam,
    priceFormat: { type: 'price', precision: 2, minMove: 0.01 },
  });
  CT.nen.setData(bars);

  // Khối lượng, ép xuống 22% dưới cùng để không che nến.
  // lastValueVisible: false — không thì trục giá bên phải hiện thêm một nhãn
  // "2305900.00" nằm ngay dưới nhãn giá, nhìn như giá cổ phiếu là hai triệu.
  CT.kl = c.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: 'kl',
                                 lastValueVisible: false, priceLineVisible: false });
  c.priceScale('kl').applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
  CT.kl.setData(bars.map(b => ({ time: b.time, value: b.value,
    color: (b.close >= b.open ? M.len : M.giam) + '55' })));

  // ba đường trung bình
  CT.ma = {};
  [[20, M.s1], [50, M.s4], [200, M.s7]].forEach(([n, col]) => {
    if (bars.length < n + 5) return;
    const s = c.addLineSeries({ color: col, lineWidth: 1.5, priceLineVisible: false,
                                lastValueVisible: false, crosshairMarkerVisible: false });
    s.setData(ma(bars, n));
    CT.ma['ma' + n] = s;
  });

  // dấu bot vào / thoát lệnh — thứ mà TradingView không bao giờ vẽ được
  CT.bars = bars;
  const co = new Set(bars.map(b => b.time));
  const MK = (typeof dauMuaBan === 'function' ? dauMuaBan(sym)
                                             : (((D.candles || {})[sym] || {}).marks || []));
  const daVe = new Set();
  CT.marks = MK.filter(m => co.has(m.d) && !daVe.has(m.t + m.d) && daVe.add(m.t + m.d))
    .sort((a, b) => a.d < b.d ? -1 : 1)
    .map(m => {
      // Nen nhung san = gia THO -> dung gia khop tho (px). Nen tai tu VPS/VNDIRECT = gia
      // DA DIEU CHINH -> dung pxa (gia dieu chinh) cho dau khong lech nen sau chia tach.
      const mua = String(m.t).startsWith('B');
      // 03/10/2026: chu tren dau = GIA KHOP THAT (gia tho) — dung bang Lich su lenh. Dau gan theo NGAY nen
      // khong lech nen du nen VPS da dieu chinh co tuc.
      const gia = m.px != null ? m.px : m.pxa;
      return {
        time: m.d, position: mua ? 'belowBar' : 'aboveBar',
        color: mua ? M.s1 : M.giam, shape: mua ? 'arrowUp' : 'arrowDown',
        text: (m.sotay ? 'SỔ TAY ' : '') + (m.t === 'B+' ? 'NHỒI' : mua ? 'MUA' : m.t === 'S1/3' ? 'BÁN 1/3' : 'BÁN') + (gia != null && gia !== '' ? ' ' + (+gia).toFixed(2).replace('.', ',') : ''),
      };
    });

  // dòng OHLC ở đầu khung, cập nhật theo con trỏ
  const dau = document.getElementById('ctHead');
  const veDau = b => {
    if (!b || !dau) return;
    const tr = bars.findIndex(x => x.time === b.time) - 1;
    const p = tr >= 0 ? (b.close / bars[tr].close - 1) * 100 : null;
    const m = b.close >= b.open ? 'var(--good)' : 'var(--critical)';
    dau.innerHTML = `<b class="ohsym">${sym}</b>
      <span class="ohk">M</span><span style="color:${m}">${b.open.toFixed(2)}</span>
      <span class="ohk">C</span><span style="color:${m}">${b.high.toFixed(2)}</span>
      <span class="ohk">T</span><span style="color:${m}">${b.low.toFixed(2)}</span>
      <span class="ohk">Đ</span><b style="color:${m}">${b.close.toFixed(2)}</b>
      ${p == null ? '' : `<span style="color:${m}">${p >= 0 ? '+' : ''}${p.toFixed(2)}%</span>`}
      <span class="ohk">KL</span><span>${(b.value / 1e6).toFixed(2)} tr</span>
      <span class="ohd">${b.time.split('-').reverse().join('/')}</span>`;
  };
  veDau(bars[bars.length - 1]);
  c.subscribeCrosshairMove(p => {
    if (!p || !p.time) { veDau(bars[bars.length - 1]); return; }
    const b = p.seriesData.get(CT.nen);
    if (b) veDau(Object.assign({ time: p.time, value: (p.seriesData.get(CT.kl) || {}).value || 0 }, b));
  });

  apChiBao();
  apKhungThoiGian();

  // Chi con mot dong nguon goc, khong huong dan. Nguoi dung tu lan chuot la biet.
  document.getElementById('tvNote').innerHTML =
    `<span class="muted">${bars.length} phiên · nguồn ${CT.nguon}${
      CT.marks.length ? ` · ${CT.marks.length} dấu bot` : ''}</span>`;

  // đổi nền sáng/tối thì vẽ lại cho khớp
  if (!CT.theoDoiMau) {
    CT.theoDoiMau = new MutationObserver(() => { if (CT.sym) moBieuDo(CT.sym); });
    CT.theoDoiMau.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  }
}

function apChiBao() {
  if (!CT.chart) return;
  Object.values(CT.ma).forEach(s => s.applyOptions({ visible: !!CT.ind.ma }));
  if (CT.kl) CT.kl.applyOptions({ visible: !!CT.ind.vol });
  if (CT.nen) CT.nen.setMarkers(CT.ind.bot ? (CT.marks || []) : []);
}

function apKhungThoiGian() {
  if (!CT.chart || !CT.bars.length) return;
  const n = { '3M': 66, '1Y': 250, '3Y': 750, '5Y': 1250, 'ALL': CT.bars.length }[CT.range] || 250;
  const b = CT.bars;
  const tu = b[Math.max(0, b.length - n)].time, den = b[b.length - 1].time;
  CT.chart.timeScale().setVisibleRange({ from: tu, to: den });
}
