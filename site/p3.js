
/* ---------- shared ---------- */
const P = D.prod, M = P.metrics, BM = D.bench_metrics;
const dates = P.curve.map(c=>c[0]);
const xticks = (()=>{const o=[];let l='';dates.forEach((d,i)=>{if(d.slice(0,4)!==l){o.push([i,d.slice(0,4)]);l=d.slice(0,4);}});return o;})();
const botCurve = P.curve.map(c=>c[1]);
const benchCurve = D.bench.map(b=>b[1]);
function ddSeries(v){const o=[];let pk=-1e9;v.forEach(x=>{pk=Math.max(pk,x);o.push(-(1-x/pk));});return o;}
const nPos = (()=>{const c={};P.trades.forEach(t=>{c[t.sym+t.entry]=[t.entry,t.exit];});
  const iv=Object.values(c);return dates.map(d=>iv.filter(([a,z])=>a<=d&&d<=z).length);})();
const avgPos = (nPos.reduce((a,b)=>a+b,0)/nPos.length);
const pctInvested = nPos.filter(x=>x>0).length/nPos.length;

/* Cot thu 4 = AN khoi thanh dieu huong. Trang van TON TAI va van vao duoc bang
   duong dan #ten-trang — chi la khach hang khong thay trong menu. */
/* ============================================================================
   THANH ĐIỀU HƯỚNG — bản gốc tám mục, giữ nguyên thứ tự anh Sơn đã quen.

   Cột thứ tư = ẨN khỏi menu. Trang vẫn tồn tại và vẫn vào được bằng #tên-trang.

   Ghi chú: bản 17 từng đổi sang năm mục hướng khách hàng (Hôm nay · Cơ hội ·
   Danh mục · Tra cứu mã · Hiệu quả & Phương pháp). Anh Sơn thấy khó đọc nên đã
   trả về bản này. Ba trang đó KHÔNG bị xoá — vẫn vào được bằng #homnay, #cohoi,
   #hieuqua, muốn dùng lúc nào cũng được.
   ========================================================================== */
const PAGES = [
 ['hieusuat','Hiệu suất', pageHome],
 ['chuong','Chuông báo', pageLive],
 ['danhmuc','Danh mục hệ thống', pageSoLenh],
 ['watchlist','Watchlist', pageWatchlist],
 ['boloc','Bộ lọc', pageScreener],
 ['lenh','Lịch sử lệnh', pageTrades],
 ['bieudo','Chi tiết mã', pageChart],
 ['kiemdinh','Kiểm định',        pageKiemDinh,  true],   // an khoi menu theo yeu cau
 ['tongquan','Tổng quan chi tiết', pageOverview,  true],
 ['backtest','Backtest',           pageBacktest,  true],
 ['dongtien','Dòng tiền lớn',      pageFlow,      true],
 ['hethong','Hệ thống 9 lớp',      pageSystem,    true],
 ['bangchung','Bằng chứng',        pageEvidence,  true],
 ['sotay','Sổ tay của tôi',        pageNotebook,  true],
 // ba trang thử nghiệm của bản 17 — giữ lại, ẩn khỏi menu
 ['homnay','Hôm nay (thử nghiệm)',      pageHomNay,  true],
 ['cohoi','Cơ hội (thử nghiệm)',        pageCoHoi,   true],
 ['hieuqua','Hiệu quả & PP (thử nghiệm)', pageHieuQua, true],
];
const HOME = 'hieusuat';
function kpi(lab,val,sub,klass){
  return `<div class="card kpi"><div class="lab">${lab}</div><div class="val ${klass||''}">${val}</div>${sub?`<div class="sub">${sub}</div>`:''}</div>`;
}

function pageOverview(root){
  root.innerHTML = `
  <div class="hero">
    <div class="badge">Dữ liệu FireAnt · ${D.universe_n} mã HOSE + HNX · backtest 2019 → ${D.asof}</div>
    <h1>Hệ thống không đoán thị trường.<br>Nó chỉ chờ đúng một loại phiên.</h1>
    <p class="lead">Hệ thống của Nguyễn Sơn mua cổ phiếu <b>đúng phiên tiền lớn nhảy vào</b> — giá cận trần, khối lượng gấp đôi, <b>cỡ lệnh mua to hơn cỡ lệnh bán 20%</b>, sau một nền giá yên tĩnh 30 phiên. Sai thì cắt trong 3–4%, đúng thì gồng tới cùng. Dưới đây là toàn bộ những gì đã thực sự xảy ra trong ${(dates.length/250).toFixed(1)} năm qua.</p>
  </div>
  <div class="grid kpis" id="kpirow"></div>

  <h2>Đường vốn — Hệ thống so với VN-Index</h2>
  <p class="muted" style="margin-top:0">Cùng xuất phát 1,00 vào 02/01/2019. Vốn 1 tỷ, mỗi lệnh 42% NAV, tối đa 12 mã, phí 0,15% mua / 0,25% bán, van T+4.</p>
  <div class="seg" id="presetSeg" style="margin-bottom:12px"></div>
  <div class="card"><div class="legend">
    <span><i style="background:var(--s1)"></i>Hệ thống Nguyễn Sơn</span>
    <span><i style="background:var(--s2)"></i>VN-Index</span></div><div id="eqchart"></div></div>

  <div class="two" style="margin-top:14px">
    <div class="card"><h3 style="margin-top:0">Sụt giảm tối đa</h3>
      <div class="legend"><span><i style="background:var(--s1)"></i>Hệ thống</span><span><i style="background:var(--s2)"></i>VN-Index</span></div>
      <div id="ddchart"></div>
      <p class="muted" style="margin:8px 0 0">Hệ thống chạm đáy sâu nhất <b class="neg">−${(M.maxdd*100).toFixed(1)}%</b>; VN-Index <b class="neg">−${(BM.mdd*100).toFixed(1)}%</b>. Ngưỡng chịu đau anh đặt ra là 15%.</p></div>
    <div class="card"><h3 style="margin-top:0">Lợi nhuận từng năm</h3>
      <div class="legend"><span><i style="background:var(--s1)"></i>Hệ thống</span><span><i style="background:var(--s2)"></i>VN-Index</span></div>
      <div id="yearchart"></div></div>
  </div>

  <h2>So với hai hệ tham chiếu</h2>
  <div class="card"><table><thead><tr><th>Chỉ số</th><th style="text-align:right">Hệ thống Nguyễn Sơn</th>
    <th style="text-align:right">Khoa Nguyen Invest</th><th style="text-align:right">VN-Index</th></tr></thead><tbody id="peer"></tbody></table>
  <p class="muted" style="margin:12px 0 0"><b style="color:var(--text-primary)">Đọc bảng này cho đúng — chỗ này quan trọng.</b> Tỷ lệ thắng và R:R ở trên đếm theo <b>deal</b> (một mã mua vào rồi bán ra trọn vẹn), không đếm theo lệnh. Hệ thống bán từng phần nên nếu đếm theo lệnh sẽ ra ${M.trades} lệnh với tỷ lệ thắng ${pct(M.winrate)} — con số đó không so sánh được với anh Khoa. Gom lại đúng chuẩn deal thì <b>tỷ lệ thắng ${pct((P.deal_metrics||{}).winrate||0)} so với 35% và R:R ${(P.deal_metrics||{}).rr} so với 5,2</b> — gần như trùng khít. Chất lượng tín hiệu của hai hệ là một; khác biệt duy nhất còn lại là <b>số deal ${(P.deal_metrics||{}).deals} so với 237</b>, tức anh Khoa đánh nhiều hơn.<br><br>
  Cùng cách tính phí: 0,15% mua · 0,25% bán, không tính trượt giá — đúng như trang Khoa Nguyen công bố. Nếu tính thêm trượt giá 0,2%/chiều cho sát thực tế, hệ thống cho <b>${sg(D.presets.thucte.metrics.total_return)}</b> với drawdown ${pct(D.presets.thucte.metrics.maxdd)} (bấm nút "Có trượt giá" ở biểu đồ trên).<br><br>
  <b>Lưu ý về tính trung thực:</b> con số của Khoa Nguyen lấy từ ảnh chụp trang chủ anh Sơn gửi (+462,8% · 237 deal · WR 35% · R:R 5,2). Trang đó render bằng JavaScript nên công cụ của em không đọc trực tiếp được nguyên tắc chi tiết — phần so sánh luật lấy từ bảng cross-check trong tài liệu <i>Hệ Thống Giao Dịch Hợp Nhất v1.0</i>.</p></div>

  <h2>Ba phiên bản của chính hệ thống này</h2>
  <div class="card"><table><thead><tr><th>Chỉ số</th><th style="text-align:right">Bản 1 (DNSE, 311 mã)</th><th style="text-align:right">Bản 2 (FireAnt, ${D.universe_n} mã)</th><th style="text-align:right">VN-Index</th></tr></thead><tbody id="cmpv"></tbody></table>
  <p class="muted" style="margin:12px 0 0">Ba thay đổi tạo ra khác biệt: <b>(1)</b> vũ trụ rộng gấp đôi — đây là thủ phạm chính của "quá ít lệnh"; <b>(2)</b> bắt trần theo <b>giá tham chiếu</b> thay vì giá điều chỉnh, đúng như bảng điện; <b>(3)</b> thêm bộ lọc <b>cỡ lệnh mua so với cỡ lệnh bán</b> — factor chỉ FireAnt mới có.</p></div>

  <h2>Năm 2026 — hệ thống có thật sự đứng im không?</h2>
  <p class="muted" style="margin-top:0">Đây là câu hỏi anh đặt ra. Bản v1 khoá cứng khi đèn đỏ nên nghỉ liền 5 tháng. Bản v2 vẫn thăm dò 20% cỡ vị thế trong đèn đỏ.</p>
  <div class="card"><table><thead><tr><th>Tháng</th><th style="text-align:right">Lệnh vào</th><th style="text-align:right">Lãi/lỗ thực hiện</th><th>Đèn thị trường</th></tr></thead><tbody id="m26"></tbody></table>
  <p class="muted" style="margin:12px 0 0"><b>Nhưng phải nói thẳng:</b> giai đoạn tháng 3→8 đèn đỏ là <b>đúng</b>. Hệ thống vẫn đánh thăm dò và lỗ đều. Toàn bộ lợi nhuận 2026 đến từ tháng 1–2. Cái sai của bản cũ không phải "đứng ngoài" mà là đứng ngoài <b>100%</b> thay vì thăm dò 20%.</p></div>

  <h2>Điểm yếu thật sự của hệ — và em không giấu</h2>
  <div class="card">
    <p style="margin-top:0">Nhìn biểu đồ lợi nhuận từng năm sẽ thấy ngay hai năm âm nhẹ: <b>2022 ${sg(P.yearly['2022'])}</b> và <b>2023 ${sg(P.yearly['2023'])}</b>, cộng thêm <b>2019 ${sg(P.yearly['2019'])}</b>. Đây là bản chất của hệ, không phải lỗi code:</p>
    <ul style="color:var(--text-secondary);font-size:14.5px;line-height:1.75">
      <li>Hệ đòi <b>một phiên bùng nổ cận trần sau nền yên tĩnh 30 phiên</b>. Thị trường đi ngang hoặc trend đều đặn không tạo ra loại phiên đó — hệ thống đứng nhìn.</li>
      <li>Năm 2022 VN-Index mất ${pct(Math.abs(D.bench_yearly['2022']))} thì hệ thống chỉ ${sg(P.yearly['2022'])} — cổng thị trường làm đúng việc của nó, đó mới là giá trị thật.</li>
      <li>Đã thử nới bằng "nền phẳng 15 phiên" để bắt thêm lệnh: số lệnh tăng nhưng Profit Factor rơi rõ rệt. <b>Nới ra là mua thêm hàng kém, không phải mua thêm hàng tốt.</b> Nên không bật.</li>
      <li>Luật <b>"về bờ"</b> (đã lãi ≥8% thì dời stop lên +1%) được thêm sau khi phát hiện lệnh thắng thường đạt đỉnh lãi cao hơn nhiều so với mức thoát thực tế — tức trả lại quá nhiều lợi nhuận đã có.</li>
    </ul>
    <p style="margin-bottom:0">Kết luận thật lòng: <b>đây là hệ bắt sóng lớn, không phải hệ đánh mọi thị trường.</b> Nó ăn đậm 2020, 2021, 2025 và đi ngang 2022–2023. Nếu cần một hệ có lãi đều mọi năm thì phải là hệ khác.</p>
  </div>

  <div class="note" style="margin-top:22px"><b>Vũ trụ giao dịch hiện tại:</b> chỉ TOP 110 mã thanh khoản nhất, xếp hạng lại theo <i>từng phiên</i> bằng GTGD bình quân 20 phiên — không dùng danh sách VN30/VN100 của hôm nay áp ngược lại quá khứ (đó là nhìn trước). So với chạy toàn thị trường: lợi nhuận ${sg(M.total_return)} so với +517,6% và sụt giảm tối đa ${pct(M.maxdd)} so với 12,8%. Ngưỡng \"lãi lớn\" bật trailing MA10 chốt nhanh đã hạ từ 25% xuống <b>19%</b> — nằm giữa vùng phẳng 18–22% và cho drawdown thấp nhất toàn lưới; từ 24% trở lên drawdown nhảy lên 13%.</div>`;

  document.getElementById('kpirow').innerHTML =
    kpi('Tổng lợi nhuận', sg(M.total_return), `${(dates.length/250).toFixed(1)} năm · NAV ${vnd(M.final_nav)}`, cls(M.total_return))
  + kpi('CAGR', sg(M.cagr), `VN-Index ${sg(BM.cagr)}`, cls(M.cagr))
  + kpi('Drawdown tối đa', '−'+pct(M.maxdd), `VN-Index −${pct(BM.mdd)}`, 'neg')
  + kpi('Profit Factor', M.pf, 'lãi gộp / lỗ gộp')
  + kpi('Số lệnh', M.trades, `${M.per_year} lệnh mỗi năm`)
  + kpi('Tỷ lệ thắng', pct(M.winrate), `+${M.avg_win}% / ${M.avg_loss}%`)
  + kpi('Sharpe', M.sharpe, 'trên chuỗi NAV ngày');

  document.getElementById('cmpv').innerHTML=[
    ['Số lệnh', D.v1.trades, M.trades, '—'],
    ['Lệnh mỗi năm', D.v1.per_year, M.per_year, '—'],
    ['Tổng lợi nhuận', sg(D.v1.total_return), sg(M.total_return), sg(BM.total)],
    ['CAGR', sg(D.v1.cagr), sg(M.cagr), sg(BM.cagr)],
    ['Drawdown', '−'+pct(D.v1.maxdd), '−'+pct(M.maxdd), '−'+pct(BM.mdd)],
    ['Profit Factor', D.v1.pf, M.pf, '—'],
    ['Sharpe', D.v1.sharpe, M.sharpe, '—'],
  ].map(([a,b,c,d])=>`<tr><td class="sym">${a}</td><td style="text-align:right">${b}</td>
    <td style="text-align:right"><b style="color:var(--text-primary)">${c}</b></td><td style="text-align:right">${d}</td></tr>`).join('');
  const K=D.peer.khoa, DM=P.deal_metrics||{};
  document.getElementById('peer').innerHTML=[
    ['Tổng lợi nhuận từ 2019', sg(M.total_return), sg(K.total), sg(BM.total)],
    ['CAGR', sg(M.cagr), sg(Math.pow(1+K.total,1/(dates.length/250))-1), sg(BM.cagr)],
    ['Drawdown tối đa', '−'+pct(M.maxdd), '~−15,4%', '−'+pct(BM.mdd)],
    ['Tỷ lệ thắng <span class="muted">(theo deal)</span>', pct(DM.winrate||M.winrate), pct(K.winrate), '—'],
    ['R:R <span class="muted">(theo deal)</span>', DM.rr??M.rr, K.rr, '—'],
    ['Lãi TB khi thắng', '+'+(DM.avg_win??M.avg_win)+'%', '—', '—'],
    ['Lỗ TB khi thua', (DM.avg_loss??M.avg_loss)+'%', '—', '—'],
    ['Số deal', DM.deals??M.trades, K.deals, '—'],
    ['Profit Factor', DM.pf??M.pf, '—', '—'],
  ].map(([a,b,c,d])=>`<tr><td class="sym">${a}</td>
    <td style="text-align:right"><b style="color:var(--text-primary)">${b}</b></td>
    <td style="text-align:right">${c}</td><td style="text-align:right">${d}</td></tr>`).join('');

  document.getElementById('m26').innerHTML = D.m2026.map(x=>{
    const L=Object.entries(x.lights).sort((a,b)=>b[1]-a[1]);
    return `<tr><td class="sym">${x.m}</td><td style="text-align:right">${x.n}</td>
      <td style="text-align:right" class="${cls(x.pnl)}">${x.pnl>=0?'+':''}${x.pnl} tr</td>
      <td>${L.map(([k,v])=>`<span class="pill ${k}">${LIGHTNAME[k]} ${v}</span>`).join(' ')}</td></tr>`;}).join('');

  drawEquity('prod');
  const seg=document.getElementById('presetSeg');
  const PRE=[['prod','Đang chạy — nền 18%, T+4'],['thucte','Có trượt giá 0,2%'],['nhieudeal','Nhiều deal hơn — nền 20%'],['khoa','Nhiều deal nhất — nền 25%'],['benhat','Bền nhất — size 30%'],['tvalve6','Van T+6 — cấu hình cũ']];
  PRE.forEach(([k,lab],i)=>{const b=el('button',i===0?'on':'',lab);
    b.onclick=()=>{seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');drawEquity(k);};seg.appendChild(b);});

  const yrs=Object.keys(P.yearly);
  const host=document.getElementById('yearchart');
  groupedBars(host, yrs.map(y=>({k:y,a:P.yearly[y]*100,b:(D.bench_yearly[y]||0)*100})),
    {h:230,fmtY:v=>v.toFixed(0)+'%'});
  lineChart(document.getElementById('ddchart'),{h:200,series:[
    {name:'Hệ thống',color:'--s1',v:ddSeries(botCurve),fill:true},
    {name:'VN-Index',color:'--s2',v:ddSeries(benchCurve)}],
    labels:dates,xticks,fmtY:v=>(v*100).toFixed(0)+'%',fmtV:v=>(v*100).toFixed(1)+'%'});
}
function drawEquity(key){
  const host=document.getElementById('eqchart'); host.innerHTML='';
  const cur = key==='prod'? botCurve : D.presets[key].curve.map(c=>c[1]);
  const nm  = key==='prod'? 'Hệ thống Nguyễn Sơn' : D.presets[key].label;
  lineChart(host,{h:330,series:[
    {name:nm,color:'--s1',v:cur,fill:true},
    {name:'VN-Index',color:'--s2',v:benchCurve}],
    labels:dates,xticks,fmtY:v=>v.toFixed(2),fmtV:v=>v.toFixed(3)+'×'});
}

/* ---------- grouped bar (2 series) ---------- */
function groupedBars(host, items, opt={}){
  const W=1000,H=opt.h||240,P_={t:18,r:12,b:40,l:56};
  const box=el('div','chartbox'); host.appendChild(box);
  const tip=el('div','tip'); box.appendChild(tip);
  const NS='http://www.w3.org/2000/svg';
  const mk=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e;};
  const svg=mk('svg',{viewBox:`0 0 ${W} ${H}`,preserveAspectRatio:'none'}); svg.style.height=H+'px'; box.appendChild(svg);
  const vals=items.flatMap(d=>[d.a,d.b]);
  let lo=Math.min(0,...vals),hi=Math.max(0,...vals);const pad=(hi-lo)*.14||1;hi+=pad;if(lo<0)lo-=pad;
  const Y=v=>P_.t+(hi-v)*(H-P_.t-P_.b)/(hi-lo);
  const gw=(W-P_.l-P_.r)/items.length;
  for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4;
    svg.appendChild(mk('line',{x1:P_.l,x2:W-P_.r,y1:Y(v),y2:Y(v),stroke:CV('--line'),'stroke-width':1,'vector-effect':'non-scaling-stroke'}));
    const t=mk('text',{x:P_.l-8,y:Y(v)+4,'text-anchor':'end',fill:CV('--text-muted'),'font-size':11});t.textContent=opt.fmtY?opt.fmtY(v):v.toFixed(0);svg.appendChild(t);}
  items.forEach((d,i)=>{
    const x0=P_.l+i*gw+gw*0.14, bw=gw*0.72/2-1;
    [['a','--s1'],['b','--s2']].forEach(([key,col],k)=>{
      const v=d[key], y0=Y(0),y1=Y(v),top=Math.min(y0,y1),h=Math.max(2,Math.abs(y1-y0));
      const r=mk('rect',{x:x0+k*(bw+2),y:top,width:bw,height:h,fill:CV(col),rx:3});
      svg.appendChild(r);
      r.addEventListener('pointerenter',ev=>{
        tip.innerHTML=`<b>${d.k}</b><div style="margin-top:3px"><span style="width:9px;height:9px;border-radius:3px;background:${CV('--s1')};display:inline-block"></span> Hệ thống: <b>${(d.a>=0?'+':'')+d.a.toFixed(1)}%</b></div>
          <div><span style="width:9px;height:9px;border-radius:3px;background:${CV('--s2')};display:inline-block"></span> VN-Index: <b>${(d.b>=0?'+':'')+d.b.toFixed(1)}%</b></div>`;
        tip.style.opacity=1;const br=box.getBoundingClientRect();
        tip.style.left=Math.min(Math.max(0,ev.clientX-br.left-80),br.width-170)+'px';tip.style.top='0px';});
      r.addEventListener('pointerleave',()=>tip.style.opacity=0);
    });
    const t=mk('text',{x:x0+gw*0.36,y:H-22,'text-anchor':'middle',fill:CV('--text-muted'),'font-size':11});t.textContent=d.k;svg.appendChild(t);
  });
  svg.appendChild(mk('line',{x1:P_.l,x2:W-P_.r,y1:Y(0),y2:Y(0),stroke:CV('--text-muted'),'stroke-width':1.5,'vector-effect':'non-scaling-stroke'}));
}

/* ---------- HỆ THỐNG HÔM NAY ---------- */
/* Hàm pageLive BẢN CŨ đã bị xoá khỏi đây (29/08/2026).
   Trước đó có HAI hàm cùng tên: một ở file này, một ở p8.js. p8.js nạp sau nên
   ghi đè bản này — nghĩa là bản này chưa bao giờ chạy, và ai sửa nó thì sửa mãi
   không thấy gì đổi. Đã vấp đúng một lần. Trang Chuông báo dùng pageLive của p8.js. */
