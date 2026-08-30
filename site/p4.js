
function pageBacktest(root){
  root.innerHTML=`
  <h1>Backtest chi tiết</h1>
  <p class="lead">Chạy tuần tự từng phiên từ 02/01/2019 đến ${D.asof} trên ${D.universe_n} mã. Dữ liệu cơ bản chỉ được dùng <b>sau ngày công bố báo cáo thật</b>. Vốn hoá lấy theo từng phiên từ FireAnt — không có lookahead ở bất kỳ đâu.</p>

  <h2>Năm cấu hình, cùng một bộ tín hiệu</h2>
  <div class="card"><table><thead><tr><th>Cấu hình</th><th style="text-align:right">Tổng LN</th><th style="text-align:right">CAGR</th>
    <th style="text-align:right">Drawdown</th><th style="text-align:right">PF</th><th style="text-align:right">Sharpe</th><th style="text-align:right">Lệnh/năm</th></tr></thead><tbody id="presetTbl"></tbody></table>
  </div>

  <h2>Đánh đổi: nhiều deal hơn được gì, mất gì</h2>
  
  <div class="card"><table><thead><tr><th>Phương án</th><th style="text-align:right">Deal</th>
    <th style="text-align:right">Deal/năm</th><th style="text-align:right">Tỷ lệ thắng</th><th style="text-align:right">R:R</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Tổng LN</th><th style="text-align:right">Drawdown</th>
    <th style="text-align:right">Sharpe</th></tr></thead><tbody id="tradeoffTbl"></tbody></table>
  <p class="muted" style="margin:12px 0 0"><b>Quy luật rất rõ:</b> mỗi deal thêm vào đều là một tín hiệu <i>kém hơn</i> tín hiệu trước đó — vì hệ thống đã xếp hạng và lấy cái tốt nhất trước. Nới nền từ 18% lên 25% cho gấp rưỡi số deal nhưng tổng lợi nhuận giảm. Không có bữa trưa miễn phí ở đây.<br><br>
  Bản đang chạy là <b>nền 18% + van T+4</b> — cho tổng lợi nhuận cao nhất. Nếu anh muốn nhiều deal hơn thì bấm nút ở tab Tổng quan để xem ngay các phương án nới rộng; cái giá phải trả nằm đúng ở cột Tổng LN trong bảng này.</p></div>

  <h2>Đếm theo lệnh hay theo deal?</h2>
  
  <div class="card"><table><thead><tr><th>Chỉ số</th><th style="text-align:right">Đếm theo lệnh</th>
    <th style="text-align:right">Đếm theo deal</th><th style="text-align:right">Khoa Nguyen</th></tr></thead><tbody id="dealTbl"></tbody></table>
  </div>

  <h2>Cửa thoát — tiền được kiếm ở đâu</h2>
  <div class="two">
    <div class="card"><div id="doorchart"></div></div>
    <div class="card"><table><thead><tr><th>Cửa thoát</th><th style="text-align:right">Lệnh</th><th style="text-align:right">Tỷ lệ</th><th style="text-align:right">Trung vị</th></tr></thead><tbody id="doorTbl"></tbody></table>
    </div>
  </div>

  <h2>Phân bố kết quả từng lệnh</h2>
  <div class="card"><div id="hist"></div>
  </div>

  <h2>Số vị thế mở theo thời gian</h2>
  <div class="card"><div id="poschart"></div>
  </div>

  <h2>Đèn thị trường theo thời gian</h2>
  <div class="card"><div class="ribbon" id="ribbon"></div>
    <div class="legend" style="margin-top:10px">
      <span><i style="background:var(--good)"></i>Xanh · size 100% (${P.lights.XANH||0} phiên)</span>
      <span><i style="background:var(--warn)"></i>Vàng · size 60% (${P.lights.VANG||0})</span>
      <span><i style="background:var(--serious)"></i>Cam · size 35% (${P.lights.CAM||0})</span>
      <span><i style="background:var(--critical)"></i>Đỏ · size 20% (${P.lights.DO||0})</span></div>
    </div>

  <h2>Nguyên bản tài liệu vs bản đã hiệu chỉnh</h2>
  <div class="card"><table><thead><tr><th>Chỉ số</th><th style="text-align:right">Nguyên bản</th><th style="text-align:right">Bản đang chạy</th></tr></thead><tbody id="cmpTbl"></tbody></table>
  </div>`;

  const rows=[['Đang chạy — nền 18%, van T+4',M],
    ['Có trượt giá 0,2% (sát thực tế nhất)',D.presets.thucte.metrics],
    ['Nhiều deal hơn — nền 20%, T+4',D.presets.nhieudeal.metrics],
    ['Nhiều deal nhất — nền 25%, size 25%',D.presets.khoa.metrics],
    ['Bền nhất — size 30%',D.presets.benhat.metrics],
    ['Van T+4',D.presets.tvalve4.metrics]];
  document.getElementById('presetTbl').innerHTML=rows.map(([n,m])=>
    `<tr><td class="sym">${n}</td><td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
     <td style="text-align:right" class="${cls(m.cagr)}">${sg(m.cagr)}</td>
     <td style="text-align:right" class="${m.maxdd>0.15?'neg':''}">−${pct(m.maxdd)}</td>
     <td style="text-align:right">${m.pf}</td><td style="text-align:right">${m.sharpe}</td><td style="text-align:right">${m.per_year}</td></tr>`).join('')
   +`<tr style="border-top:2px solid var(--line)"><td class="sym">VN-Index (mua &amp; giữ)</td>
     <td style="text-align:right" class="pos">${sg(BM.total)}</td><td style="text-align:right" class="pos">${sg(BM.cagr)}</td>
     <td style="text-align:right" class="neg">−${pct(BM.mdd)}</td><td style="text-align:right">—</td><td style="text-align:right">—</td><td style="text-align:right">—</td></tr>`;

  const DM=P.deal_metrics||{}, KK=D.peer.khoa;
  const TO=[['Nền 18% + T+4 — đang chạy',{metrics:M,deal_metrics:DM}],
            ['Van T+4 (giải phóng vốn nhanh hơn)',D.presets.tvalve4],
            ['Nền 20% + T+4 — nhiều deal hơn',D.presets.nhieudeal],
            ['Nền 25% + size 25% — nhiều deal nhất',D.presets.khoa],
            ['Size 30% — bền nhất',D.presets.benhat]];
  document.getElementById('tradeoffTbl').innerHTML=TO.map(([n,p])=>{
    const m=p.metrics, d=p.deal_metrics||{};
    return `<tr><td class="sym">${n}</td><td style="text-align:right;font-weight:650;color:var(--text-primary)">${d.deals??'—'}</td>
      <td style="text-align:right">${d.deals?(d.deals/7.6).toFixed(1):'—'}</td>
      <td style="text-align:right">${d.winrate?pct(d.winrate):'—'}</td><td style="text-align:right">${d.rr??'—'}</td>
      <td style="text-align:right">${d.pf??'—'}</td>
      <td style="text-align:right" class="${cls(m.total_return)}">${sg(m.total_return)}</td>
      <td style="text-align:right" class="neg">−${pct(m.maxdd)}</td>
      <td style="text-align:right">${m.sharpe}</td></tr>`;}).join('');
  document.getElementById('dealTbl').innerHTML=[
    ['Số lần ghi nhận', M.trades, DM.deals, KK.deals],
    ['Tỷ lệ thắng', pct(M.winrate), pct(DM.winrate||0), pct(KK.winrate)],
    ['Lãi TB khi thắng', '+'+M.avg_win+'%', '+'+DM.avg_win+'%', '—'],
    ['Lỗ TB khi thua', M.avg_loss+'%', DM.avg_loss+'%', '—'],
    ['R:R', M.rr, DM.rr, KK.rr],
    ['Profit Factor', M.pf, DM.pf, '—'],
    ['Kỳ vọng mỗi lần', '+'+M.expectancy+'%', '+'+DM.expectancy+'%', '—'],
  ].map(([a,b,c,d])=>`<tr><td class="sym">${a}</td><td style="text-align:right">${b}</td>
    <td style="text-align:right"><b style="color:var(--text-primary)">${c}</b></td>
    <td style="text-align:right">${d}</td></tr>`).join('');
  document.getElementById('doorTbl').innerHTML=P.doors.map(d=>
    `<tr><td class="sym">${d.door}</td><td style="text-align:right">${d.n}</td><td style="text-align:right">${d.pct}%</td>
     <td style="text-align:right" class="${cls(d.median)}">${d.median>=0?'+':''}${d.median}%</td></tr>`).join('');
  barChart(document.getElementById('doorchart'), P.doors.map(d=>({
      k:d.door.replace('Van thời gian ','').replace('Trailing ','T.').replace(' (lãi lớn)','↑').replace('Đèn Cam — hạ 1/3','Đèn Cam'),
      v:d.median, color:d.median>=0?'--s3':'--s8', note:d.n+' lệnh · '+d.pct+'%'})),
    {h:250,fmtY:v=>v.toFixed(0)+'%',fmtV:v=>(v>=0?'+':'')+v.toFixed(1)+'%',label:'Lãi/lỗ trung vị'});

  const bins=[-100,-10,-7,-5,-3,-1,0,3,7,12,20,30,50,1e4];
  const labs=['<-10','-10..-7','-7..-5','-5..-3','-3..-1','-1..0','0..3','3..7','7..12','12..20','20..30','30..50','>50'];
  const cnt=new Array(labs.length).fill(0);
  P.trades.forEach(t=>{for(let i=0;i<labs.length;i++){if(t.pnl_pct>bins[i]&&t.pnl_pct<=bins[i+1]){cnt[i]++;break;}}});
  barChart(document.getElementById('hist'), labs.map((k,i)=>({k,v:cnt[i],color:i<6?'--s8':'--s3'})),
    {h:250,fmtY:v=>v.toFixed(0),fmtV:v=>v,label:'Số lệnh'});
  lineChart(document.getElementById('poschart'),{h:170,series:[{name:'Vị thế mở',color:'--s7',v:nPos,fill:true}],
    labels:dates,xticks,fmtY:v=>v.toFixed(0),fmtV:v=>v.toFixed(0)+' mã',min:0});

  const rb=document.getElementById('ribbon'); const step=Math.max(1,Math.floor(D.regime.length/380));
  for(let i=0;i<D.regime.length;i+=step){const dv=el('div');dv.style.flex='1';dv.style.background=`var(${LIGHTVAR[D.regime[i].light]})`;
    dv.title=`${D.regime[i].date} — ${LIGHTNAME[D.regime[i].light]} · ${D.regime[i].dd} ngày phân phối`;rb.appendChild(dv);}

  const cr=[['Số lệnh','trades',x=>x],['Lệnh/năm','per_year',x=>x],['Tổng lợi nhuận','total_return',sg],['CAGR','cagr',sg],
    ['Drawdown','maxdd',x=>'−'+pct(x)],['Tỷ lệ thắng','winrate',x=>pct(x)],['Lãi TB khi thắng','avg_win',x=>'+'+x+'%'],
    ['Lỗ TB khi thua','avg_loss',x=>x+'%'],['Profit Factor','pf',x=>x],['Sharpe','sharpe',x=>x]];
  document.getElementById('cmpTbl').innerHTML=cr.map(([lab,k,f])=>
    `<tr><td class="sym">${lab}</td><td style="text-align:right">${f(D.strict.metrics[k])}</td>
     <td style="text-align:right"><b style="color:var(--text-primary)">${f(M[k])}</b></td></tr>`).join('');
}
