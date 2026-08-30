
function pageTrades(root){
  root.innerHTML=`
  <h1>Lịch sử lệnh</h1>
  
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
    <input type="search" id="q" placeholder="Tìm mã, ngành, cửa thoát…" style="min-width:240px">
    <select id="fy"><option value="">Tất cả các năm</option></select>
    <select id="fr"><option value="">Tất cả cửa thoát</option></select>
    <select id="fw"><option value="">Thắng &amp; thua</option><option value="w">Chỉ thắng</option><option value="l">Chỉ thua</option></select>
    <select id="fl"><option value="">Mọi đèn</option><option>XANH</option><option>VANG</option><option>CAM</option><option>DO</option></select>
  </div>
  <div class="grid kpis" id="tkpi" style="margin-bottom:14px"></div>
  <div class="tblwrap"><table id="tt"><thead><tr>
    <th data-k="sym">Mã</th><th data-k="sector">Ngành</th><th data-k="entry">Mua</th><th data-k="exit">Bán</th>
    <th data-k="held" style="text-align:right">Phiên</th><th data-k="entry_px" style="text-align:right">Giá mua</th>
    <th data-k="exit_px" style="text-align:right">Giá bán</th><th data-k="pnl_pct" style="text-align:right">Lãi/lỗ</th>
    <th data-k="pnl_vnd" style="text-align:right">Tiền</th><th data-k="peak" style="text-align:right">Đỉnh lãi</th>
    <th data-k="reason">Cửa thoát</th><th data-k="light">Đèn</th></tr></thead><tbody id="tb"></tbody></table></div>`;
  const years=[...new Set(P.trades.map(t=>t.exit.slice(0,4)))].sort();
  const reasons=[...new Set(P.trades.map(t=>t.reason))];
  fy.innerHTML+=years.map(y=>`<option>${y}</option>`).join('');
  fr.innerHTML+=reasons.map(r=>`<option>${r}</option>`).join('');
  let sk='exit',sd=-1;
  function render(){
    const Q=q.value.toLowerCase();
    let rows=P.trades.filter(t=>{
      if(fy.value&&t.exit.slice(0,4)!==fy.value)return false;
      if(fr.value&&t.reason!==fr.value)return false;
      if(fl.value&&t.light!==fl.value)return false;
      if(fw.value==='w'&&t.pnl_pct<=0)return false;
      if(fw.value==='l'&&t.pnl_pct>0)return false;
      if(Q&&!(t.sym+' '+t.sector+' '+t.reason).toLowerCase().includes(Q))return false;
      return true;});
    rows.sort((a,b)=>{const x=a[sk],y=b[sk];return (x>y?1:x<y?-1:0)*sd;});
    tb.innerHTML=rows.map(t=>`<tr><td class="sym">${t.sym}</td><td>${t.sector}</td><td>${t.entry}</td><td>${t.exit}</td>
      <td style="text-align:right">${t.held}</td><td style="text-align:right">${t.entry_px}</td><td style="text-align:right">${t.exit_px}</td>
      <td style="text-align:right;font-weight:650" class="${cls(t.pnl_pct)}">${t.pnl_pct>=0?'+':''}${t.pnl_pct}%</td>
      <td style="text-align:right" class="${cls(t.pnl_vnd)}">${t.pnl_vnd>=0?'+':''}${vnd(t.pnl_vnd)}</td>
      <td style="text-align:right">${t.peak?'+'+t.peak+'%':'—'}</td><td>${t.reason}</td>
      <td><span class="pill ${t.light}">${LIGHTNAME[t.light]}</span></td></tr>`).join('');
    const w=rows.filter(t=>t.pnl_pct>0),l=rows.filter(t=>t.pnl_pct<=0),tot=rows.reduce((s,t)=>s+t.pnl_vnd,0);
    tkpi.innerHTML=kpi('Số lệnh',rows.length,'')
      +kpi('Tỷ lệ thắng',rows.length?pct(w.length/rows.length):'—','')
      +kpi('Lãi TB khi thắng',w.length?'+'+(w.reduce((s,t)=>s+t.pnl_pct,0)/w.length).toFixed(2)+'%':'—','','pos')
      +kpi('Lỗ TB khi thua',l.length?(l.reduce((s,t)=>s+t.pnl_pct,0)/l.length).toFixed(2)+'%':'—','','neg')
      +kpi('Tổng tiền',(tot>=0?'+':'')+vnd(tot),'',cls(tot));
  }
  document.querySelectorAll('#tt thead th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;sd=(k===sk)?-sd:-1;sk=k;render();});
  ['q','fy','fr','fw','fl'].forEach(id=>document.getElementById(id).oninput=render);
  render();
}

function pageFlow(root){
  const s3=(D.sweeps||{}).s3||{}, s2=(D.sweeps||{}).s2||{};
  // Cac bang nay den tu thi nghiem chay MOT LAN (thu muc evidence/). Neu thieu file
  // thi bao ro chu khong de ca trang vo — trang van con phan giai thich cach do.
  if (!s2['baseline'] || !s3 || !Object.keys(s3).length){
    root.innerHTML = `<h1>Dòng tiền lớn</h1>
      `;
    return;
  }
  root.innerHTML=`
  <h1>Dòng tiền lớn</h1>

  <h2>Cách đo mới: cỡ lệnh mua so với cỡ lệnh bán</h2>
  <div class="card">
    <p style="margin-top:0">FireAnt công bố bốn con số mà DNSE không có: <code>BuyQuantity</code>, <code>BuyCount</code>, <code>SellQuantity</code>, <code>SellCount</code>. Từ đó tính được:</p>
    <div style="background:var(--surface-2);border-radius:10px;padding:14px 18px;font-family:ui-monospace,monospace;font-size:13.5px;margin:14px 0;color:var(--text-primary)">
      cỡ lệnh mua TB = BuyQuantity / BuyCount<br>
      cỡ lệnh bán TB = SellQuantity / SellCount<br><br>
      <b style="color:var(--s1)">tỷ số dòng tiền = cỡ lệnh mua TB ÷ cỡ lệnh bán TB</b>
    </div>
    <p>Tỷ số &gt; 1 nghĩa là <b>bên mua đang đặt lệnh to hơn bên bán</b> — dấu hiệu tổ chức gom hàng từ tay nhỏ lẻ. Tỷ số &lt; 1 là ngược lại: lệnh bán to, lệnh mua nhỏ, tức tay to đang phân phối cho nhỏ lẻ đúng lúc giá tăng. Đây chính là cái mà buổi 5 gọi là "đổi thuyền trưởng", nhưng đo được bằng số thay vì đoán qua volume.</p>
  </div>

  <h2>Nó thực sự có tác dụng không?</h2>
  
  <div class="card"><table><thead><tr><th>Cấu hình</th><th style="text-align:right">Lệnh</th><th style="text-align:right">Tổng LN</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Drawdown</th><th style="text-align:right">Sharpe</th><th style="text-align:right">Tỷ lệ thắng</th></tr></thead><tbody id="ftbl"></tbody></table></div>

  <h2>Nó sửa đúng những năm anh nói là "lỗ"</h2>
  <div class="card"><div id="fyear"></div>
  </div>

  <h2>Cổng rủi ro đã chặn những gì</h2>
  
  <div class="card"><div id="blockchart"></div></div>

  `;

  const base=s2['baseline'], f10=s2['loc co lenh mua>ban (>=1.0)'], f13=s2['loc co lenh mua>ban (>=1.3)'];
  document.getElementById('ftbl').innerHTML=[
    ['Không lọc dòng tiền',base],['Tỷ số ≥ 1,0 (đang dùng)',f10],['Tỷ số ≥ 1,3 (khắt khe hơn)',f13]
  ].map(([n,m])=>`<tr><td class="sym">${n}</td><td style="text-align:right">${m.trades}</td>
    <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
    <td style="text-align:right;font-weight:640;color:var(--text-primary)">${m.pf}</td>
    <td style="text-align:right" class="neg">−${pct(m.maxdd)}</td><td style="text-align:right">${m.sharpe}</td>
    <td style="text-align:right">${pct(m.winrate)}</td></tr>`).join('');
  const yrs=Object.keys(base.yearly);
  groupedBars(document.getElementById('fyear'), yrs.map(y=>({k:y,a:(f10.yearly[y]||0)*100,b:(base.yearly[y]||0)*100})),
    {h:230,fmtY:v=>v.toFixed(0)+'%'});
  const legend=el('div','legend','<span><i style="background:var(--s1)"></i>Có lọc dòng tiền</span><span><i style="background:var(--s2)"></i>Không lọc</span>');
  document.getElementById('fyear').prepend(legend);
  const BL={'CFO':'CFO < 0 — dòng tiền kinh doanh âm','ICR':'ICR < 1,5 — không đủ tiền trả lãi vay',
            'D/E':'D/E > 4,0 — đòn bẩy quá dày','NPL':'NPL > 3% — nợ xấu ngân hàng','Chưa':'Chưa có báo cáo tài chính'};
  barChart(document.getElementById('blockchart'), Object.entries(D.blocked).map(([k,v])=>({k,v,color:'--s8',note:BL[k]||k})),
    {h:230,fmtY:v=>(v/1000).toFixed(0)+'k',fmtV:v=>num(v),label:'Lượt mã-phiên bị chặn'});
}
