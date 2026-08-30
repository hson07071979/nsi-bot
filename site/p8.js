
/* ---------- WATCHLIST ---------- */
function pageWatchlist(root){
  const W=D.watchlist||{members:[],added:[],removed:[],rules:{}};
  const R=W.rules||{};
  const fit=W.members.filter(m=>m.status==='đạt');
  const pin=W.members.filter(m=>m.status!=='đạt');
  // Nhóm "chưa đạt về cơ bản": qua hết mọi cổng TRỪ điểm số, điểm 40–45.
  // Để riêng hẳn, KHÔNG nằm trong danh sách mua. Nguyên tắc mua vẫn đòi điểm ≥ 45.
  const fa=((D.screener||{}).fa_watchlist)||[];
  root.innerHTML=`
  <h1>Watchlist</h1>

  <div class="grid kpis" style="margin-bottom:16px">
    ${kpi('Đang theo dõi', W.members.length, `${fit.length} đạt chuẩn · ${pin.length} ghim thủ công`)}
    ${kpi('Vừa thêm', W.added.length, W.added.length? W.added.slice(0,4).map(a=>a.sym).join(' · '):'—','pos')}
    ${kpi('Vừa loại', W.removed.length, W.removed.length? W.removed.slice(0,4).map(a=>a.sym).join(' · '):'—', W.removed.length?'neg':'')}
    ${kpi('Chưa đạt cơ bản', fa.length, 'để riêng, không vào danh sách mua', fa.length?'warn':'')}
  </div>

  <h2>Danh sách mua (${fit.length})</h2>
  
  <div class="tblwrap"><table id="wt"><thead><tr>
    <th data-k="sym">Mã</th><th data-k="sector">Ngành</th><th data-k="price" style="text-align:right">Giá</th>
    <th data-k="score" style="text-align:right">Điểm</th><th data-k="fund" style="text-align:right">Cơ bản</th>
    <th data-k="tech" style="text-align:right">Kỹ thuật</th><th data-k="base" style="text-align:right">Nền %</th>
    <th data-k="rs" style="text-align:right">RS</th><th data-k="gtgd20" style="text-align:right">GTGD</th>
    <th data-k="ordimb20" style="text-align:right">Dòng tiền</th><th data-k="roe" style="text-align:right">ROE</th>
    <th data-k="rev_yoy" style="text-align:right">DThu YoY</th><th data-k="npat_yoy" style="text-align:right">LNST YoY</th>
    <th>Hạng</th></tr></thead><tbody id="wtb"></tbody></table></div>

  ${(D.screener.watchlist||[]).some(m=>m.tim) ? `` : ''}

  <h2>Chưa đạt về cơ bản — FA (${fa.length})</h2>
  
  <div class="card tblwrap">${fa.length? `<table><thead><tr><th>Mã</th><th>Ngành</th>
    <th style="text-align:right">Giá</th><th style="text-align:right">Điểm</th>
    <th style="text-align:right">Cơ bản</th><th style="text-align:right">Kỹ thuật</th>
    <th style="text-align:right">Nền %</th><th style="text-align:right">RS</th>
    <th style="text-align:right">GTGD</th><th style="text-align:right">ROE</th>
    <th style="text-align:right">DThu YoY</th><th style="text-align:right">LNST YoY</th></tr></thead><tbody>
    ${fa.map(m=>`<tr><td class="sym">${esc(m.sym)}${m.tim?' <span title="Đèn tím — '+(m.tim_vi||'')+'" style="color:var(--s7)">●</span>':''}</td><td>${esc(m.sector) || ''}</td>
      <td style="text-align:right">${m.price??'—'}</td>
      <td style="text-align:right;font-weight:650;color:var(--warn)">${m.score??'—'}</td>
      <td style="text-align:right">${m.fund??'—'}<span class="muted">/55</span></td>
      <td style="text-align:right">${m.tech??'—'}<span class="muted">/50</span></td>
      <td style="text-align:right">${m.base??'—'}</td><td style="text-align:right">${m.rs??'—'}</td>
      <td style="text-align:right">${m.gtgd20??'—'}</td>
      <td style="text-align:right">${m.roe??'—'}${m.roe!=null?'%':''}</td>
      <td style="text-align:right" class="${m.rev_yoy>=0?'pos':'neg'}">${m.rev_yoy??'—'}${m.rev_yoy!=null?'%':''}</td>
      <td style="text-align:right" class="${m.npat_yoy>=0?'pos':'neg'}">${m.npat_yoy??'—'}${m.npat_yoy!=null?'%':''}</td>
    </tr>`).join('')}</tbody></table>`
    : '<p style="margin:0">Không có mã nào trong khoảng điểm này.</p>'}</div>

  <h2>Ghim thủ công (${pin.length + (typeof ghimThuCong === 'function' ? ghimThuCong().length : 0)})</h2>
  
  ${(typeof ghimThuCong === 'function' && ghimThuCong().length) ? `
  <div class="card tblwrap" style="margin-bottom:14px"><table><thead><tr>
    <th>Mã</th><th>Doanh nghiệp</th><th style="text-align:right">Giá</th>
    <th>Trạng thái hệ thống</th><th>Ghi chú của anh Sơn</th><th>Ngày thêm</th></tr></thead><tbody>
    ${ghimThuCong().map(w => `<tr>
      <td class="sym">${esc(w.sym)}${w.chuaDang ? '<span class="tag A" style="margin-left:6px">Chưa đăng</span>' : ''}</td>
      <td class="muted" style="font-size:13px">${((w.look && w.look.name) || '').slice(0, 34)}</td>
      <td style="text-align:right">${w.price ?? '—'}</td>
      <td>${w.look ? `<span class="lkbadge ${w.look.state}" style="font-size:11px">${w.look.label}</span>` : '<span class="muted">ngoài vũ trụ giao dịch</span>'}</td>
      <td class="muted" style="font-size:13px">${esc(w.note) || '—'}</td>
      <td class="muted" style="font-size:13px">${w.added || '—'}</td></tr>`).join('')}
  </tbody></table></div>` : ''}
  <div class="card tblwrap"><table><thead><tr><th>Mã</th><th>Ngành</th><th style="text-align:right">Điểm</th>
    <th style="text-align:right">Nền %</th><th style="text-align:right">RS</th><th>Vì sao chưa đạt</th></tr></thead><tbody>
    ${pin.map(m=>`<tr><td class="sym">${esc(m.sym)}</td><td>${esc(m.sector) || '—'}</td>
      <td style="text-align:right">${m.score??'—'}</td><td style="text-align:right">${m.base??'—'}</td>
      <td style="text-align:right">${m.rs??'—'}</td>
      <td><span class="pill ${m.blocked?'DO':'VANG'}">${esc(m.note) || '—'}</span></td></tr>`).join('')}</tbody></table></div>

  <h2>Nhật ký thay đổi</h2>
  <div class="two">
    <div class="card"><h3 style="margin-top:0;color:var(--good)">Thêm vào</h3>
      ${W.added.length? '<table><thead><tr><th>Mã</th><th>Ngành</th><th style="text-align:right">Điểm</th><th style="text-align:right">Nền</th><th style="text-align:right">RS</th></tr></thead><tbody>'+
        W.added.map(a=>`<tr><td class="sym">${esc(a.sym)}</td><td>${esc(a.sector) || ''}</td><td style="text-align:right">${a.score}</td><td style="text-align:right">${a.base??'—'}%</td><td style="text-align:right">${a.rs??'—'}</td></tr>`).join('')+'</tbody></table>'
        : '<p style="margin:0">Không có mã nào mới vào.</p>'}</div>
    <div class="card"><h3 style="margin-top:0;color:var(--critical)">Loại ra</h3>
      ${W.removed.length? '<table><thead><tr><th>Mã</th><th>Lý do</th></tr></thead><tbody>'+
        W.removed.map(a=>`<tr><td class="sym">${esc(a.sym)}</td><td>${esc(a.why)}</td></tr>`).join('')+'</tbody></table>'
        : '<p style="margin:0">Không có mã nào bị loại.</p>'}</div>
  </div>`;
  let sk='score',sd=-1;
  function rend(){
    const rows=[...fit].sort((a,b)=>{const x=a[sk]??-1e9,y=b[sk]??-1e9;return (x>y?1:x<y?-1:0)*sd;});
    // chấm tím = lãi quý gần nhất đến từ hoạt động bất thường, xem kỹ trước khi mua
    const _tim = s2 => { const x=(D.lookup||{})[s2];
      return x && x.tim ? ` <span title="Đèn tím — ${esc(x.tim_vi) || ''}" style="color:var(--s7)">●</span>` : ''; };
    document.getElementById('wtb').innerHTML=rows.map(m=>`<tr>
      <td class="sym">${esc(m.sym)}${_tim(m.sym)}</td><td>${esc(m.sector) || ''}</td><td style="text-align:right">${m.price??'—'}</td>
      <td style="text-align:right;font-weight:650;color:var(--text-primary)">${m.score??'—'}</td>
      <td style="text-align:right">${m.fund??'—'}<span class="muted">/55</span></td>
      <td style="text-align:right">${m.tech??'—'}<span class="muted">/50</span></td>
      <td style="text-align:right">${m.base??'—'}</td><td style="text-align:right">${m.rs??'—'}</td>
      <td style="text-align:right">${m.gtgd20??'—'}</td>
      <td style="text-align:right;font-weight:600" class="${(m.ordimb20||0)>=1.2?'pos':''}">${m.ordimb20??'—'}</td>
      <td style="text-align:right">${m.roe??'—'}%</td>
      <td style="text-align:right" class="${cls(m.rev_yoy||0)}">${m.rev_yoy==null?'—':(m.rev_yoy>=0?'+':'')+m.rev_yoy+'%'}</td>
      <td style="text-align:right" class="${cls(m.npat_yoy||0)}">${m.npat_yoy==null?'—':(m.npat_yoy>=0?'+':'')+m.npat_yoy+'%'}</td>
      <td><span class="pill ${m.grade_score==='Cao'?'XANH':m.grade_score==='Khá'?'VANG':'CAM'}">${m.grade_score}</span>
          <span class="muted" style="font-size:11.5px">${m.grade_base}</span></td></tr>`).join('');
  }
  document.querySelectorAll('#wt thead th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(!k)return;sd=(k===sk)?-sd:-1;sk=k;rend();});
  rend();
}

/* ---------- BỘ LỌC ---------- */
function pageScreener(root){
  const SC=D.screener||{rows:[]};
  const rows=SC.rows||[];
  root.innerHTML=`
  <h1>Bộ lọc cổ phiếu</h1>
  
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
    <input type="search" id="sq" placeholder="Tìm mã hoặc ngành…" style="min-width:220px">
    <select id="sf"><option value="">Mọi ngành</option></select>
    <select id="sg"><option value="">Mọi hạng điểm</option><option>Cao</option><option>Khá</option><option>Vừa</option><option>Thấp</option></select>
    <select id="sb"><option value="">Mọi loại nền</option><option>Chặt</option><option>Khá chặt</option><option>Okay</option><option>Rộng</option></select>
    <select id="sr"><option value="">Cả bị chặn &amp; không</option><option value="ok">Chỉ mã qua cổng rủi ro</option><option value="no">Chỉ mã bị chặn</option></select>
    <select id="sw"><option value="">Tất cả</option><option value="wl">Chỉ mã trong watchlist</option></select>
  </div>
  <div class="grid kpis" id="skpi" style="margin-bottom:14px"></div>
  <div class="tblwrap"><table id="st"><thead><tr>
    <th data-k="sym">Mã</th><th data-k="sector">Ngành</th><th data-k="price" style="text-align:right">Giá</th>
    <th data-k="mktcap" style="text-align:right">Vốn hoá</th><th data-k="score" style="text-align:right">Điểm</th>
    <th data-k="fund" style="text-align:right">Cơ bản</th><th data-k="tech" style="text-align:right">Kỹ thuật</th>
    <th data-k="roe" style="text-align:right">ROE</th><th data-k="rev_yoy" style="text-align:right">DThu</th>
    <th data-k="npat_yoy" style="text-align:right">LNST</th><th data-k="icr" style="text-align:right">ICR</th>
    <th data-k="de" style="text-align:right">D/E</th><th data-k="base" style="text-align:right">Nền %</th>
    <th data-k="rs" style="text-align:right">RS</th><th data-k="gtgd20" style="text-align:right">GTGD</th>
    <th data-k="ordimb20" style="text-align:right">Dòng tiền</th><th>Cổng rủi ro</th></tr></thead><tbody id="stb"></tbody></table></div>
  `;
  const secs=[...new Set(rows.map(r=>r.sector))].sort();
  sf.innerHTML+=secs.map(s=>`<option>${s}</option>`).join('');
  const wl=new Set((D.watchlist?.members||[]).map(m=>m.sym));
  let sk='score',sd=-1;
  function rend(){
    const q=sq.value.toLowerCase();
    let R=rows.filter(r=>{
      if(q && !(r.sym+' '+r.sector).toLowerCase().includes(q)) return false;
      if(sf.value && r.sector!==sf.value) return false;
      if(sg.value && r.grade_score!==sg.value) return false;
      if(sb.value && r.grade_base!==sb.value) return false;
      if(sr.value==='ok' && r.blocked) return false;
      if(sr.value==='no' && !r.blocked) return false;
      if(sw.value==='wl' && !wl.has(r.sym)) return false;
      return true;});
    R.sort((a,b)=>{const x=a[sk]??-1e9,y=b[sk]??-1e9;return (x>y?1:x<y?-1:0)*sd;});
    stb.innerHTML=R.slice(0,400).map(r=>`<tr>
      <td class="sym">${esc(r.sym)}${wl.has(r.sym)?' <span class="pill XANH" style="font-size:10px">WL</span>':''}</td>
      <td>${esc(r.sector)}</td><td style="text-align:right">${r.price??'—'}</td>
      <td style="text-align:right">${r.mktcap? num(r.mktcap)+' tỷ':'—'}</td>
      <td style="text-align:right;font-weight:650;color:var(--text-primary)">${r.score??'—'}</td>
      <td style="text-align:right">${r.fund??'—'}</td><td style="text-align:right">${r.tech??'—'}</td>
      <td style="text-align:right">${r.roe==null?'—':r.roe+'%'}</td>
      <td style="text-align:right" class="${cls(r.rev_yoy||0)}">${r.rev_yoy==null?'—':(r.rev_yoy>=0?'+':'')+r.rev_yoy+'%'}</td>
      <td style="text-align:right" class="${cls(r.npat_yoy||0)}">${r.npat_yoy==null?'—':(r.npat_yoy>=0?'+':'')+r.npat_yoy+'%'}</td>
      <td style="text-align:right" class="${(r.icr!=null&&r.icr<1.5)?'neg':''}">${r.icr??'—'}</td>
      <td style="text-align:right" class="${(r.de!=null&&r.de>4)?'neg':''}">${r.de??'—'}</td>
      <td style="text-align:right">${r.base??'—'}</td><td style="text-align:right">${r.rs??'—'}</td>
      <td style="text-align:right">${r.gtgd20??'—'}</td>
      <td style="text-align:right" class="${(r.ordimb20||0)>=1.2?'pos':''}">${r.ordimb20??'—'}</td>
      <td>${r.blocked?`<span class="pill DO">${r.block}</span>`:(r.warn?'<span class="pill VANG">Cờ vàng</span>':'<span class="pill XANH">Qua</span>')}</td></tr>`).join('');
    const pass=R.filter(r=>!r.blocked).length;
    skpi.innerHTML=kpi('Số mã',R.length,R.length>400?'hiện 400 dòng đầu':'')
      +kpi('Qua cổng rủi ro',pass, R.length? pct(pass/R.length):'')
      +kpi('Điểm ≥ 60', R.filter(r=>(r.score||0)>=60).length,'hạng Khá trở lên')
      +kpi('Nền chặt ≤12%', R.filter(r=>r.base!=null&&r.base<=12).length,'sẵn sàng cho điểm mua')
      +kpi('Dòng tiền ≥1,2', R.filter(r=>(r.ordimb20||0)>=1.2).length,'lệnh mua to hơn lệnh bán');
  }
  document.querySelectorAll('#st thead th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(!k)return;sd=(k===sk)?-sd:-1;sk=k;rend();});
  ['sq','sf','sg','sb','sr','sw'].forEach(id=>document.getElementById(id).oninput=rend);
  rend();
}

/* ---------- CHUÔNG BÁO (ghi đè pageLive ở p3) ---------- */
function pageLive(root){
  // ⚠️ CO HAI HAM pageLive TRONG DU AN: mot o p3.js (BAN CU, da chet vi p8.js nap sau
  // nen ghi de) va ban nay. Sua nham file la khong thay gi thay doi ca — da vap mot lan.
  // Neu co live.json (trang chay tren web that) thi ve ban truc tiep.
  if (typeof LIVE !== 'undefined' && LIVE && LIVE.data) { pageLiveTrucTiep(root, LIVE.data); return; }
  const A=D.alerts||{alerts:[],counts:{},asof:'',light:'DO',scanned:0,universe:0};
  const last=D.regime[D.regime.length-1];
  const ICON={MUA:'🔴',SAP_DU:'🟠',THEO_DOI:'🟡',CHAN:'⚠️'};
  const NAME={MUA:'ĐỦ ĐIỀU KIỆN NGAY BÂY GIỜ — đặt lệnh trước ATC',
              SAP_DU:'SẮP ĐỦ — dự phóng sẽ đạt lúc đóng cửa, theo sát',
              THEO_DOI:'THEO DÕI — đang động đậy nhưng còn thiếu nhiều',
              CHAN:'CHẶN — bắt trần nhưng cổng rủi ro phủ quyết'};
  const by=k=>A.alerts.filter(a=>a.level===k);
  root.innerHTML=`
  <h1>Chuông báo</h1>

  <div class="card" style="display:flex;gap:26px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
    <div><div class="muted" style="text-transform:uppercase;letter-spacing:.06em;font-weight:600;font-size:12px">Đèn thị trường</div>
      <div style="font-size:34px;font-weight:750;color:var(${LIGHTVAR[A.light||last.light]})">${LIGHTNAME[A.light||last.light].toUpperCase()}</div>
      <div class="muted">Cỡ vị thế × ${A.size_mul ?? '—'}</div></div>
    <div style="border-left:1px solid var(--line);padding-left:26px;display:grid;gap:9px">
      <div><span class="muted">G1 · chỉ số đều trọng số vs MA200</span><br><b style="font-size:17px">${last.g1.toFixed(0)}</b>
        <span class="${last.g1>=(last.g1ma||0)?'pos':'neg'}">${last.g1ma?(last.g1>=last.g1ma?'trên':'dưới'):'—'} ${last.g1ma?last.g1ma.toFixed(0):''}</span></div>
      <div><span class="muted">G2 · VN-Index vs MA50</span><br><b style="font-size:17px">${last.vni.toFixed(1)}</b>
        <span class="${last.vni>=(last.vma50||0)?'pos':'neg'}">${last.vma50?(last.vni>=last.vma50?'trên':'dưới'):'—'} ${last.vma50?last.vma50.toFixed(0):''}</span></div>
      <div><span class="muted">G3 · ngày phân phối / 25 phiên</span><br><b style="font-size:17px" class="${last.dd>=5?'neg':last.dd>=3?'':'pos'}">${last.dd}</b>
        <span class="muted"> · độ rộng ${pct(last.br50,0)} số mã trên MA50</span></div></div>
    <div style="border-left:1px solid var(--line);padding-left:26px">
      ${['MUA','SAP_DU','THEO_DOI','CHAN'].map(k=>`<div style="font-size:15px;margin:3px 0">${ICON[k]} <b>${(A.counts||{})[k]||0}</b> <span class="muted">${k.replace('_',' ').toLowerCase()}</span></div>`).join('')}
    </div>
  </div>

  ${['MUA','SAP_DU','THEO_DOI','CHAN'].map(k=>{
    const list=by(k);
    return `<h2>${ICON[k]} ${NAME[k]} <span class="muted" style="font-size:15px;font-weight:400">(${list.length})</span></h2>
    ${list.length? `<div class="tblwrap" style="max-height:none"><table><thead><tr><th>Mã</th><th>Ngành</th>
      <th style="text-align:right">Giá</th><th style="text-align:right">%</th><th style="text-align:right">Vol/TB20</th>
      <th style="text-align:right">GTGD</th><th style="text-align:right">Nền</th><th style="text-align:right">Dòng tiền</th>
      <th style="text-align:right">Điểm</th><th>Điều kiện</th><th>Còn thiếu / ghi chú</th></tr></thead><tbody>
      ${list.map(a=>`<tr><td class="sym">${esc(a.sym)}${a.watchlist?' <span class="pill XANH" style="font-size:10px">WL</span>':''}</td>
        <td>${esc(a.sector)}</td><td style="text-align:right">${a.price}</td>
        <td style="text-align:right;font-weight:650" class="${cls(a.pct)}">${a.pct>=0?'+':''}${a.pct}%</td>
        <td style="text-align:right">${a.volr}×<span class="muted" style="font-size:11.5px"> → ${a.volr_proj??a.volr}×</span></td>
        <td style="text-align:right">${a.gtgd} tỷ<span class="muted" style="font-size:11.5px"> → ${a.gtgd_proj??a.gtgd}</span></td>
        <td style="text-align:right">${a.base}%</td>
        <td style="text-align:right" class="${(a.ordimb||0)>=1.2?'pos':''}">${a.ordimb!=null?a.ordimb:(a.ordimb_prev!=null?'<span class="muted">'+a.ordimb_prev+' (hôm qua)</span>':'—')}</td>
        <td style="text-align:right;color:var(--text-primary);font-weight:640">${a.score}</td>
        <td>${Object.entries(a.cond).map(([kk,v])=>`<span class="ck ${v?'y':'n'}" title="${kk}" style="display:inline-grid;margin-right:2px">${v?'✓':'✕'}</span>`).join('')}</td>
        <td class="muted" style="font-size:12.5px">${a.blocked? '<span class="pill DO">'+a.block+'</span>' : (a.level==='SAP_DU'&&a.need&&a.need.length? a.need.join(' · ') : (a.missing&&a.missing.length? 'thiếu: '+a.missing.join(', ') : '—'))}${a.locked?' <span class="pill CAM">trần cứng, khó khớp</span>':''}</td></tr>`).join('')}
      </tbody></table></div>`
    : `<div class="card"><p style="margin:0">Không có mã nào ở mức này tại lần quét gần nhất.</p></div>`}`;
  }).join('')}

  <h2>Danh mục hệ thống đang mở</h2>
  <div class="card" id="openbox"></div>`;
  const ob=document.getElementById('openbox');
  ob.innerHTML = D.open_positions.length
    ? '<table><thead><tr><th>Mã</th><th>Ngành</th><th>Ngày mua</th><th style="text-align:right">Giá vốn</th><th style="text-align:right">Hiện tại</th><th style="text-align:right">Lãi/lỗ</th></tr></thead><tbody>'+
      D.open_positions.map(p=>`<tr><td class="sym">${esc(p.sym)}</td><td>${esc(p.sector)}</td><td>${p.entry}</td><td style="text-align:right">${p.entry_px}</td><td style="text-align:right">${p.last}</td><td style="text-align:right" class="${cls(p.pnl)}">${p.pnl>=0?'+':''}${p.pnl}%</td></tr>`).join('')+'</tbody></table>'
    : `<p style="margin:0">Không có vị thế nào đang mở. Đèn thị trường đang <b style="color:var(${LIGHTVAR[last.light]})">${LIGHTNAME[last.light]}</b> — hệ thống giữ tiền mặt và chờ.</p>`;
}
