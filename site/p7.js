
function pageEvidence(root){
  const s2=D.sweeps.s2, s3=D.sweeps.s3, op=D.sweeps.opt;
  root.innerHTML=`
  <h1>Bằng chứng</h1>
  <p class="lead">Tài liệu gốc yêu cầu: luật hạng C phải chạy backtest riêng, bật từng cái một. Đây là kết quả những bài test đó trên dữ liệu FireAnt — cùng bộ dữ liệu, mỗi lần chỉ đổi đúng một tham số.</p>

  <h2 style="color:var(--warn)">0. Giả định khớp lệnh — thứ quan trọng nhất trên trang này</h2>
  <div class="note"><b>Đọc kỹ phần này trước mọi con số khác.</b> Toàn bộ backtest giả định mua được ở <b>giá đóng cửa của chính phiên bắn tín hiệu</b> — tức phiên cổ phiếu tăng cận trần với khối lượng gấp đôi. Nếu anh không kịp khớp trong phiên đó mà phải mua sang phiên sau, kết quả <b>rơi rất mạnh</b>. Đây không phải chi tiết kỹ thuật, đây là toàn bộ hệ.</div>
  <div class="card" style="margin-top:14px"><table><thead><tr><th>Giả định khớp lệnh</th>
    <th style="text-align:right">Deal</th><th style="text-align:right">Tỷ lệ thắng</th><th style="text-align:right">R:R</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Tổng LN</th><th style="text-align:right">CAGR</th>
    <th style="text-align:right">Drawdown</th></tr></thead><tbody id="fillTbl"></tbody></table>
  <div class="note warn" style="margin:12px 0 0"><b>Ba dòng này KHÔNG so được với con số ${M.trades} lệnh · ${sg(M.total_return)} ở các trang khác.</b>
  Đây là một thí nghiệm chạy MỘT LẦN dưới cấu hình cũ (vũ trụ rộng hơn, ngưỡng lãi lớn 25%),
  nên nó ra khoảng <b>215 lệnh</b> chứ không phải ${M.trades}. Bảng này chỉ dùng để đọc <b>tỷ lệ giữa
  ba cách khớp lệnh với nhau</b> — PF 2,62 so 1,76 so 1,65 — chứ tuyệt đối không lấy con số tuyệt đối
  của nó đem so với bản đang chạy. Muốn so trực tiếp thì phải chạy lại cả ba dòng dưới cấu hình hiện tại.</div>
  <p class="muted" style="margin:12px 0 0">Cả ba dòng đều đã tính phí 0,15%/0,25% <b>và</b> trượt giá 0,2% mỗi chiều.<br><br>
  <b>Ý nghĩa thực hành:</b> luật "chỉ xác nhận tín hiệu sau 14h00" trong tài liệu không phải chi tiết phụ — <b>nó là cả hệ thống</b>. Anh phải có mặt từ 14h00 đến ATC để đặt lệnh. Nếu anh chỉ xem tín hiệu buổi tối rồi mua sáng hôm sau, Profit Factor rơi từ 2,62 xuống 1,65 và drawdown gần gấp đôi.<br><br>
  <b>Và điều này cũng đúng với mọi hệ khác công bố con số backtest theo cách tương tự</b> — nếu họ cũng khớp ở giá đóng cửa phiên tín hiệu thì con số của họ mang đúng giả định lạc quan này. Em không có cách kiểm chứng, nên chỉ nêu ra để anh biết mà đối chiếu.</p></div>

  <h2>1. Vũ trụ cổ phiếu — thủ phạm của "quá ít lệnh"</h2>
  <div class="card"><table><thead><tr><th>Phễu tín hiệu 2019 → nay</th><th style="text-align:right">Phiên-mã</th><th style="text-align:right">Còn lại</th></tr></thead><tbody>
    <tr><td class="sym">Trong vũ trụ (vốn hoá &gt; 1.000 tỷ, ≥ 250 phiên)</td><td style="text-align:right">497.346</td><td style="text-align:right">—</td></tr>
    <tr><td class="sym">+ Bắt trần theo <b>giá tham chiếu</b></td><td style="text-align:right">15.211</td><td style="text-align:right">3,1%</td></tr>
    <tr><td class="sym">+ Volume ≥ 2× TB20</td><td style="text-align:right">5.566</td><td style="text-align:right">36,6%</td></tr>
    <tr><td class="sym">+ GTGD ≥ 15 tỷ</td><td style="text-align:right">3.717</td><td style="text-align:right">66,8%</td></tr>
    <tr><td class="sym">+ Biến động &amp; đóng cửa nửa trên nến</td><td style="text-align:right">3.675</td><td style="text-align:right">98,9%</td></tr>
    <tr style="border-top:2px solid var(--line)"><td class="sym">+ Nền 30 phiên ≤ 12% (nguyên bản)</td><td style="text-align:right">709</td><td style="text-align:right"><b style="color:var(--text-primary)">93/năm</b></td></tr>
    <tr><td class="sym">+ Nền 30 phiên ≤ 18% (đang dùng)</td><td style="text-align:right">1.553</td><td style="text-align:right"><b style="color:var(--text-primary)">204/năm</b></td></tr>
    <tr><td class="sym">+ Nền 30 phiên ≤ 25%</td><td style="text-align:right">2.304</td><td style="text-align:right">303/năm</td></tr></tbody></table>
  <p class="muted" style="margin:12px 0 0">Bản v1 chạy trên 311 mã cho <b>21 tín hiệu kỹ thuật/năm</b>. Bản v2 với ${D.universe_n} mã, cùng luật nguyên bản ≤12%, cho <b>93/năm</b> — gấp 4,4 lần. Luật không sai; vũ trụ mới sai.</p></div>

  <h2>2. Ngưỡng dòng tiền — factor mạnh nhất tìm được</h2>
  <p class="muted" style="margin-top:0">Quét ngưỡng cỡ lệnh mua ÷ cỡ lệnh bán, cỡ vị thế cố định 30% NAV. Nếu đây chỉ là nhiễu thì đường cong sẽ nhảy lung tung; nó lại đi lên gần như đơn điệu.</p>
  <div class="card"><div id="omChart"></div>
  <table style="margin-top:14px"><thead><tr><th>Ngưỡng</th><th style="text-align:right">Lệnh</th><th style="text-align:right">Tổng LN</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Drawdown</th><th style="text-align:right">Tỷ lệ thắng</th></tr></thead><tbody id="omTbl"></tbody></table>
  <p class="muted" style="margin:12px 0 0"><b>Kết luận:</b> Profit Factor đi từ 2,16 lên 4,62 khi siết ngưỡng, tỷ lệ thắng từ 44% lên 48%, đổi lại số lệnh giảm dần. Em chọn <b>≥1,20</b> vì nó giữ được ~29 lệnh/năm (xấp xỉ 31 lệnh/năm của anh Khoa) mà Profit Factor vẫn 3,28 và drawdown thấp nhất bảng.</p></div>

  <h2>3. Cỡ vị thế dưới ràng buộc drawdown ≤ 15%</h2>
  <p class="muted" style="margin-top:0">Quét cỡ vị thế và số mã song song, tìm cấu hình cho lợi nhuận cao nhất mà vẫn không vượt ngưỡng chịu đau anh đặt ra.</p>
  <div class="card"><table><thead><tr><th>Cấu hình</th><th style="text-align:right">Tổng LN</th><th style="text-align:right">CAGR</th>
    <th style="text-align:right">Drawdown</th><th style="text-align:right">Sharpe</th><th>Kết luận</th></tr></thead><tbody id="optTbl"></tbody></table></div>

  <h2>4. Đèn thị trường: khoá cứng hay thăm dò?</h2>
  <div class="card"><table><thead><tr><th>Cách xử lý đèn Cam</th><th style="text-align:right">Lệnh</th><th style="text-align:right">Tổng LN</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Tỷ lệ thắng</th></tr></thead><tbody id="mgTbl"></tbody></table>
  <p class="muted" style="margin:12px 0 0"><b>Kết luận:</b> luật "đèn Cam hạ 1/3 danh mục" (hạng C trong tài liệu) nâng tỷ lệ thắng từ 27% lên 38% nhưng gần như không đổi tổng lợi nhuận — nó đổi cảm giác lấy sự bình yên chứ không tạo ra tiền. Em giữ vì nó giảm drawdown và giúp gồng phần còn lại dễ hơn.</p></div>

  <h2>5. Trần cứng hay cận trần?</h2>
  <div class="card"><div id="ceilChart"></div>
  <p class="muted" style="margin:8px 0 0"><b>Kết luận:</b> chỉ mua khi đã <b>trần cứng</b> (≥6,8% HOSE) cho Profit Factor cao hơn hẳn và tỷ lệ thắng tăng rõ. Nhưng nó bỏ lỡ những cây cận trần bùng nổ mạnh nhất năm 2021. Đây là lựa chọn thật sự giữa "ít mà chắc" và "nhiều mà bạo".</p></div>

  <h2>6. Sàn điểm CANSLIM có nên là ngưỡng cứng?</h2>
  <div class="card"><div id="sfChart"></div>
  <p class="muted" style="margin:8px 0 0"><b>Kết luận:</b> nâng sàn điểm làm Profit Factor tăng đều nhưng <b>tổng lợi nhuận giảm</b> và hệ thống bỏ lỡ 2026. Điểm số vẫn chỉ nên làm sàn mềm + xếp hạng, đúng như tài liệu kết luận.</p></div>

  <h2>7. Bộ thoát: có nên bảo vệ lãi đã có?</h2>
  <p class="muted" style="margin-top:0">Năm 2025 lệnh thắng đạt đỉnh +15,1% nhưng thoát ở +8,0%. Em thử ba cách bịt chỗ rò rỉ này.</p>
  <div class="card"><table><thead><tr><th>Luật bảo vệ lãi</th><th style="text-align:right">Lệnh</th><th style="text-align:right">Tổng LN</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Drawdown</th><th style="text-align:right">Sharpe</th><th>Phán quyết</th></tr></thead><tbody id="exitTbl"></tbody></table>
  <p class="muted" style="margin:12px 0 0"><b>Kết luận:</b> luật <b>"về bờ"</b> (đã lãi ≥8% thì đặt stop ở +1%) là thứ duy nhất vừa tăng lợi nhuận vừa tăng Sharpe mà không đụng drawdown — đã bật. Các luật "chốt bảo vệ khi trả lại % đỉnh" giảm drawdown xuống 11% nhưng cắt mất lệnh lãi lớn, tổng lợi nhuận rơi hơn 40 điểm phần trăm. Đây đúng là bài học của tài liệu: <b>bảo vệ lãi quá sớm là giết con gà đẻ trứng vàng.</b></p></div>

  <h2>8. Nới nền giá có mua được thêm hàng tốt không?</h2>
  <div class="card"><table><thead><tr><th>Cách định nghĩa nền</th><th style="text-align:right">Lệnh</th><th style="text-align:right">Tổng LN</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Drawdown</th></tr></thead><tbody id="shelfTbl"></tbody></table>
  <p class="muted" style="margin:12px 0 0"><b>Kết luận:</b> thêm "nền phẳng 15 phiên" (mẫu hình hạng C trong tài liệu) làm số lệnh tăng từ 308 lên 354, nhưng Profit Factor rơi từ 2,23 xuống 2,00. <b>Nới ra là mua thêm hàng kém.</b> Đã tắt.</p></div>

  <h2>9. Những thứ đã test và bị loại</h2>
  <div class="card"><table><thead><tr><th>Ý tưởng</th><th style="text-align:right">Tổng LN</th><th style="text-align:right">PF</th><th style="text-align:right">Sharpe</th><th>Phán quyết</th></tr></thead><tbody id="rejTbl"></tbody></table></div>

  <div class="note" style="margin-top:22px"><b>Cảnh báo trung thực:</b> ${M.trades} lệnh trên 7,6 năm với tỷ lệ thắng ${pct(M.winrate)} vẫn chưa đủ mẫu để phân biệt chắc chắn "luật tốt" và "may mắn". Những kết luận trùng khớp độc lập với tài liệu gốc (cổng thị trường có tác dụng, cắt lỗ % không quan trọng, điểm số không nên làm gate cứng) đáng tin hơn. Những kết luận chỉ xuất hiện ở đây (T+6, MA30, lọc cỡ lệnh) nên coi là <b>giả thuyết cần theo dõi tiếp trên tiền thật với size nhỏ</b>.</div>`;

  const FC=D.sweeps.fill||{};
  const FROWS=[['Đóng cửa phiên tín hiệu <span class="muted">(giả định đang dùng)</span>','v3 dang chay | khop dong cua phien tin hieu'],
               ['Bình quân phiên sau','v3 dang chay | khop binh quan phien sau'],
               ['Mở cửa phiên sau','v3 dang chay | khop mo cua phien sau']];
  document.getElementById('fillTbl').innerHTML=FROWS.map(([lab,k],i)=>{
    const x=FC[k]; if(!x) return '';
    const m=x.metrics, d=x.deal;
    return `<tr><td class="sym">${lab}</td><td style="text-align:right">${d.deals}</td>
      <td style="text-align:right">${pct(d.winrate)}</td><td style="text-align:right">${d.rr}</td>
      <td style="text-align:right;font-weight:${i===0?650:400};color:var(--text-primary)">${d.pf}</td>
      <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
      <td style="text-align:right">${sg(m.cagr)}</td>
      <td style="text-align:right" class="neg">−${pct(m.maxdd)}</td></tr>`;}).join('');
  const O6=D.sweeps.o6||{};
  const omKeys=Object.keys(O6).filter(k=>k.startsWith('om')&&!k.includes('_s'));
  if(omKeys.length){
    barChart(document.getElementById('omChart'), omKeys.map(k=>({k:'≥'+k.slice(2),v:O6[k].pf,color:'--s3',
      note:O6[k].trades+' lệnh · tổng '+sg(O6[k].total_return)})),
      {h:230,fmtY:v=>v.toFixed(1),fmtV:v=>v.toFixed(2),label:'Profit Factor'});
    document.getElementById('omTbl').innerHTML=omKeys.map(k=>{
      const m=O6[k], cur=k==='om1.2';
      return `<tr><td class="sym">≥ ${k.slice(2)}${cur?' ← đang dùng':''}</td><td style="text-align:right">${m.trades}</td>
        <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
        <td style="text-align:right;font-weight:${cur?650:400};color:var(--text-primary)">${m.pf}</td>
        <td style="text-align:right" class="neg">−${pct(m.maxdd)}</td>
        <td style="text-align:right">${pct(m.winrate)}</td></tr>`;}).join('');
  }
  document.getElementById('optTbl').innerHTML=Object.entries(op).map(([k,m])=>{
    const ok=m.maxdd<=0.155, cur=Math.abs(m.total_return-M.total_return)<0.01;
    return `<tr><td class="sym">${k.replace('size','Cỡ ').replace('_n',' · ').replace('_tot',' mã · tổng ')}${cur?' ← đang chạy':''}</td>
      <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
      <td style="text-align:right">${sg(m.cagr)}</td>
      <td style="text-align:right" class="${ok?'':'neg'}">−${pct(m.maxdd)}</td>
      <td style="text-align:right">${m.sharpe}</td>
      <td>${cur?'<span class="tag A">Đã chọn</span>':ok?'<span class="tag B">Đạt ngưỡng</span>':'<span class="tag C">Vượt 15%</span>'}</td></tr>`;}).join('');

  document.getElementById('mgTbl').innerHTML=[
    ['Hạ 1/3 danh mục (đang dùng)',s2['baseline']],
    ['Không làm gì',s2['tat den CAM ha 1/3']],
    ['Ngừng mua hoàn toàn',s2['den CAM chi ngung mua (0%)']],
  ].map(([n,m])=>`<tr><td class="sym">${n}</td><td style="text-align:right">${m.trades}</td>
    <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
    <td style="text-align:right">${m.pf}</td><td style="text-align:right">${pct(m.winrate)}</td></tr>`).join('');

  barChart(document.getElementById('ceilChart'),[
    {k:'Cận trần ≥5,8%',v:s2['baseline'].pf,color:'--s1',note:'Tổng LN '+sg(s2['baseline'].total_return)+' · WR '+pct(s2['baseline'].winrate)},
    {k:'Trần cứng ≥6,8%',v:s2['chi TRAN CUNG (>=6.8%)'].pf,color:'--s3',note:'Tổng LN '+sg(s2['chi TRAN CUNG (>=6.8%)'].total_return)+' · WR '+pct(s2['chi TRAN CUNG (>=6.8%)'].winrate)},
    {k:'+ lọc dòng tiền',v:s3['ordimb + tran cung'].pf,color:'--s3',note:'Tổng LN '+sg(s3['ordimb + tran cung'].total_return)},
  ],{h:220,fmtY:v=>v.toFixed(1),fmtV:v=>v.toFixed(2),label:'Profit Factor'});

  barChart(document.getElementById('sfChart'),[
    {k:'≥ 45 điểm',v:s2['baseline'].total_return*100,color:'--s4',note:'PF '+s2['baseline'].pf},
    {k:'≥ 55 điểm',v:s2['san diem 55'].total_return*100,color:'--s4',note:'PF '+s2['san diem 55'].pf},
    {k:'≥ 60 điểm',v:s2['san diem 60'].total_return*100,color:'--s4',note:'PF '+s2['san diem 60'].pf},
  ],{h:220,fmtY:v=>v.toFixed(0)+'%',fmtV:v=>'+'+v.toFixed(1)+'%',label:'Tổng lợi nhuận'});

  const s4=D.sweeps.s4, s5=D.sweeps.s5;
  document.getElementById('exitTbl').innerHTML=[
    ['Không có (chỉ trailing MA)',s4['baseline (hien tai)'],'—'],
    ['Về bờ: lãi ≥8% → stop +1%',s4['ve bo: lai>=8% -> stop +1%'],'<span class="tag A">Đã bật</span>'],
    ['Về bờ: lãi ≥6% → stop +1%',s4['ve bo: lai>=6% -> stop +1%'],'<span class="tag B">Trung tính</span>'],
    ['Chốt bảo vệ: giữ 50% đỉnh',s4['chot bao ve: giu 50% dinh'],'<span class="tag C">Cắt mất lãi lớn</span>'],
    ['Chốt bảo vệ: giữ 65% đỉnh',s4['chot bao ve: giu 65% dinh (tu 8%)'],'<span class="tag C">DD thấp nhưng LN rơi</span>'],
  ].map(([n,m,v])=>`<tr><td class="sym">${n}</td><td style="text-align:right">${m.trades}</td>
    <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
    <td style="text-align:right">${m.pf}</td><td style="text-align:right" class="neg">−${pct(m.maxdd)}</td>
    <td style="text-align:right">${m.sharpe}</td><td>${v}</td></tr>`).join('');
  document.getElementById('shelfTbl').innerHTML=[
    ['Chỉ nền 30 phiên ≤18% (đang dùng)',s5['baseline + ve bo']],
    ['+ nền phẳng 15 phiên ≤10%',s5['+ nen phang 15 phien <=10%']],
    ['+ nền phẳng 15 phiên ≤12%',s5['+ nen phang 15 phien <=12%']],
  ].map(([n,m])=>`<tr><td class="sym">${n}</td><td style="text-align:right">${m.trades}</td>
    <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
    <td style="text-align:right">${m.pf}</td><td style="text-align:right" class="neg">−${pct(m.maxdd)}</td></tr>`).join('');
  document.getElementById('rejTbl').innerHTML=[
    ['Lọc khối ngoại mua ròng',s3['ordimb + khoi ngoai mua rong'],'Giảm lợi nhuận, không giảm rủi ro'],
    ['Chỉ mua mã RS ≥ 80',s3['ordimb + RS>=80'],'Mua quá muộn, bỏ lỡ cây đầu tiên'],
    ['Chỉ mua mã RS ≥ 60',s3['ordimb + RS>=60'],'Trung tính, không đáng thêm phức tạp'],
    ['Trần volume 4,5× ở điểm mua',null,'Loại mất tín hiệu tốt — đã tắt từ v1'],
    ['Chốt lời cứng 18–20%',null,'Bán đúng trước khi nhóm lãi lớn bung ra'],
    ['Trend Template MA30>50>200',null,'Edge âm, chặn mất deal tốt nhất'],
  ].map(([n,m,verdict])=>`<tr><td class="sym">${n}</td>
    <td style="text-align:right">${m?sg(m.total_return):'—'}</td><td style="text-align:right">${m?m.pf:'—'}</td>
    <td style="text-align:right">${m?m.sharpe:'—'}</td><td class="muted">${verdict}</td></tr>`).join('');
}

/* ---------- router ---------- */
const main=document.getElementById('main'), tabs=document.getElementById('tabs');
const secs={};
PAGES.forEach(([id,label,fn,hidden],i)=>{
  if(!hidden){ const b=el('button',i===0?'on':'',label); b.dataset.id=id; b.onclick=()=>go(id); tabs.appendChild(b); }
  const s=el('section','page'+(i===0?' on':'')); s.id='pg-'+id; main.appendChild(s);
  secs[id]={fn,rendered:false,node:s,hidden:!!hidden,label};
});
function go(id){
  if(!secs[id]) id=HOME;
  tabs.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.id===id));
  document.body.classList.toggle('inpriv', !!secs[id].hidden);
  Object.entries(secs).forEach(([k,v])=>v.node.classList.toggle('on',k===id));
  const s=secs[id]; if(!s.rendered){s.fn(s.node);s.rendered=true;}
  window.scrollTo({top:0,behavior:'instant'}); location.hash=id;
}
document.getElementById('themebtn').onclick=()=>{
  const cur=document.documentElement.getAttribute('data-theme');
  document.documentElement.setAttribute('data-theme',cur==='dark'?'light':'dark');
  Object.values(secs).forEach(v=>{if(v.rendered){v.node.innerHTML='';v.rendered=false;}});
  const a=(location.hash?location.hash.slice(1):HOME); const t=secs[a]?a:HOME;
  secs[t].fn(secs[t].node); secs[t].rendered=true;
};
go(location.hash?location.hash.slice(1):HOME);
// cho phep dieu huong bang thanh dia chi / nut back cua trinh duyet
window.addEventListener('hashchange',()=>{const id=location.hash.slice(1)||HOME; if(secs[id])go(id);});
// lop truc tiep: doc live.json va tu cap nhat
if (typeof batDauLive === 'function') batDauLive();
