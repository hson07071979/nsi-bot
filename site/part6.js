
function pageSystem(root){
  const gates=[
   [0,'Vũ trụ cổ phiếu','Mã này có đủ lớn và đủ lịch sử để phân tích không?',`HOSE + HNX (loại UPCOM) · vốn hoá &gt; 1.000 tỷ · ≥ 250 phiên lịch sử · ≥ 4 quý báo cáo liên tiếp · <b>chỉ TOP ${cpTop()} thanh khoản</b>, xếp hạng lại từng phiên.`,'B'],
   [1,'Cổng rủi ro','Doanh nghiệp này có nguy cơ vỡ nợ không?','<b>Quyền phủ quyết tuyệt đối.</b> ICR &lt; 1,5 → chặn. CFO &lt; 0 → chặn. D/E &gt; 4,0 → chặn. Riêng ngân hàng: NPL &gt; 3% hoặc CAR &lt; 8% → chặn. ICR 1,5–2,5 → cờ vàng, cỡ vị thế × 0,5.','A'],
   [2,'Chấm điểm CANSLIM','Nó có đang tăng trưởng thật không?','Thang 100 điểm — <b>cơ bản 55đ + kỹ thuật 45đ</b>. LNST YoY ≥ 25% (15đ) · <b>doanh thu YoY ≥ 15% (15đ — mới)</b> · tăng tốc QoQ (+5đ) · CAGR 3 năm ≥ 20% (10đ) · <b>ROE ≥ 17% (10đ — mới)</b> · cách đỉnh 52 tuần ≤ 15% (10đ) · volume ≥ 1,2× (5đ) · RS ≥ 70 (15đ) · GTGD ≥ 15 tỷ (10đ) · <b>return 3 tháng (tối đa 5đ — mới)</b>. Điểm cao nhất thực tế trong 1.213 mã là 89,2 — thang 100 gần như không ai chạm trần. Điểm <b>không</b> phải điều kiện vào lệnh, chỉ là sàn mềm + xếp hạng.','A'],
   [3,'Nền giá','Giá đã tích luỹ đủ chặt chưa?',`Nền ${cpV('base_len',30)} phiên trước điểm mua, biên độ nền <b>≤ ${cpNen()}%</b>. Nền càng chặt thì cỡ vị thế càng lớn (≤ 10% → × 1,2).`,'A'],
   [4,'Điểm mua','Hôm nay có phải phiên tiền lớn nhảy vào không?','Phải đạt <b>tất cả các điều kiện đang bật, trong cùng một phiên</b>. Xem bảng bên dưới — bảng ghi rõ luật nào đang chạy, luật nào đã tắt.','A'],
   [5,'Cổng thị trường','Thị trường chung có cho phép mua không?','Hệ đèn 4 mức từ ba tín hiệu: G1 (chỉ số đều trọng số vs MA200), G2 (VN-Index vs MA50), G3 (đếm ngày phân phối 25 phiên). <b>Luật vàng: cổng chỉ chặn MỞ LỆNH MỚI</b> — vị thế đang cầm vẫn chạy theo bộ thoát bình thường.','A'],
   [6,'Lọc ngành','Danh mục có bị dồn quá nhiều vào một ngành không?','Trần 30% NAV cho một nhóm ngành ICB.','B'],
   [7,'Cỡ vị thế','Nên bỏ bao nhiêu tiền vào?',`<b>${cpSo(cpV('base_size',0.42)*100)}% NAV</b> × hệ số đèn (Xanh 1,0 · Vàng 0,6 · Cam 0,35 · Đỏ 0,2) × hệ số nền (1,2 / 1,0) × hệ số rủi ro (cờ vàng 0,5), rồi cắt bởi các trần: <b>${cpSo(cpV('max_pos',0.5)*100)}% NAV</b> một mã, <b>${cpSo(cpV('sector_cap',0.30)*100)}% NAV</b> một ngành, <b>${cpSo(cpV('max_total',1)*100)}% NAV</b> toàn danh mục, tiền mặt, tối đa <b>${cpV('max_pos_n',12)} mã</b>, sàn ${cpSo(cpV('min_size',0.02)*100)}% NAV. <b style="color:var(--warn)">Thực tế: trần ngành ${cpSo(cpV('sector_cap',0.30)*100)}% luôn cắt trước khi đèn Xanh cho ra ${cpSo(cpV('base_size',0.42)*100)}% — lệnh mới lớn nhất là ${cpSo(Math.min(cpV('base_size',0.42),cpV('sector_cap',0.30))*100)}% NAV.</b> Cùng một bộ chia vốn (allocator.py) dùng cho backtest, sổ paper, chuông Telegram và trang này.`,'A'],
   [8,'Bộ thoát','Khi nào thì ra?','Kiểm tra theo đúng thứ tự ưu tiên. Đây là nơi tiền thực sự được kiếm — xem bảng bên dưới.','A'],
   [9,'Pyramid','Có nên gia tăng vị thế không?','Phiên 4–7 sau điểm mua, đang lãi ≥ 10%, giá ≥ 99,9% đỉnh 10 phiên, chỉ 1 lần, chỉ khi đèn Xanh. Thêm 50% vị thế gốc nếu sau khi nhồi mã đó vẫn ≤ trần mỗi mã (50% NAV) và đủ tiền mặt. <b>Trần ngành 30% chỉ áp cho lệnh mới, không áp cho lệnh nhồi</b> — đó là luật đang chạy (kiểm toán 23/09 đo: bắt lệnh nhồi tôn trọng cả trần ngành thì +696,8% còn +579,1%; anh Sơn giữ luật cũ).','B'],
  ];
  // Đọc thẳng từ cấu hình bộ máy (D.cfg_prod). Cột cuối nói luật nào ĐANG CHẠY,
  // luật nào ĐÃ TẮT — bản cũ liệt kê cả luật đã tắt như thể đang chạy, người đọc
  // học thuộc một bộ luật không tồn tại.
  const conds=[
   ['1','Biên độ tăng giá',`HOSE ≥ ${cpSo(cpV('trig_hose',0.058)*100)}% · HNX ≥ ${cpSo(cpV('trig_hnx',0.088)*100)}% — cận trần hoặc trần`,'A',true],
   ['2','Khối lượng sàn dưới',`≥ ${cpSo(cpV('vol_floor',2.0))} × trung bình 20 phiên — tiền thật đổ vào`,'A',true],
   ['3','Giá trị giao dịch phiên',`≥ ${Math.round(cpV('gtgd_min',15e9)/1e9)} tỷ — đủ thanh khoản để sau này còn thoát được`,'A',true],
   ['4','Nền 30 phiên sạch',`Biên độ nền ${cpV('base_len',30)} phiên ≤ ${cpNen()}% — đã tích luỹ yên tĩnh, không phải mã vừa chạy xong`,'A',true],
   ['5','LNST YoY ngoài vùng yếu',cpV('dk5_hi',0.25)>cpV('dk5_lo',0)?`Ngoài khoảng ${Math.round(cpV('dk5_lo',0)*100)}–${Math.round(cpV('dk5_hi',0.25)*100)}%`:'Đã tắt 25/09/2026 — giữ vùng 0–25% làm giảm lợi nhuận ở mọi nấc thử','B',cpV('dk5_hi',0.25)>cpV('dk5_lo',0)],
   ['6','Trần khối lượng',`vol ≤ ${cpSo(cpV('vol_ceil',4.5))} × TB20 — ý tưởng là tránh phiên "đổi thuyền trưởng", nhưng bật lên thì cắt mất chính nhóm bùng nổ về sau thành lãi lớn`,'C',cpBat('use_cond6',false)],
   ['7','Biến động TB20',`≥ ${cpSo(cpV('volat_min',0.015)*100)}%/ngày — loại các mã "chết"`,'A',true],
   ['8','Đóng cửa nửa trên nến','close ≥ (high+low)/2 — tránh bẫy UTAD','C',cpBat('use_cond8',true)],
   ['9','Ngưỡng dòng tiền',`cỡ lệnh mua ÷ cỡ lệnh bán ≥ <b>${cpDTvi()}</b> — nhân tố mạnh nhất tìm được. Sở chỉ công bố số lệnh SAU giờ đóng cửa, nên ĐK9 là bước XÁC NHẬN buổi tối cho lệnh đã mua dò lúc ATC (không đạt → bán ATC T+${cpV('sell_from',2)})`,'A',cpBat('use_ordimb',true)],
  ];
  // THỨ TỰ DƯỚI ĐÂY LÀ THỨ TỰ ƯU TIÊN THẬT trong bộ máy — luật nào đứng trước
  // thì nổ trước, không phải xếp cho đẹp. Chép sai thứ tự là hiểu sai vì sao
  // "Van thời gian" chiếm gần một nửa số lệnh ra.
  const cf = cpV('conf', 2);
  const exits=[
   ['0','Lệnh dò trượt ĐK9',`Mua dò ĐỦ lệnh lúc ATC khi đạt ĐK1–8 (ĐK9 chỉ có số sau giờ đóng cửa). Tối ~18–19h: ĐK9 ≥ ${cpDTvi()} → giữ; không đạt → bán ATC T+${cpV('sell_from',2)}, phiên đầu tiên bán được. Đứng trước mọi luật thoát khác`,'A',cpV('stage1',null)!=null],
   ['1',`Hard stop ${cpSo(cpV('hard_stop',-0.10)*100)}%`,`Bán hết, xét từ phiên T+${cpV('sell_from',2)} — phiên đầu tiên bán được theo tài khoản của anh Sơn; trước đó không bán dù chạm luật nào. Mọi luật thoát đều tính bằng giá đóng cửa (ATC) từ T+${cpV('sell_from',2)} trở đi. Đứng trước mọi luật thoát khác`,'B',cpBat('use_hard_stop',true)],
   ['2','Cây nến bảo vệ','Đóng cửa dưới low của nến breakout → bán hết. Cắt sớm kiểu này làm mất quá nhiều lệnh về sau thành lãi lớn','C',cpBat('use_protective_candle',false)],
   ['2b',`Momentum T+${cpV('mo_by',3)}`,`Tới phiên T+${cpV('mo_by',3)} mà chưa từng đóng cửa lãi ≥ ${cpSo(cpV('mo_need',0.01)*100)}% (đã tính phí mua) → bán hết. Breakout thật thì phải chạy ngay (thêm 25/09/2026)`,'A',!!cpV('mo_by',0)],
   ['3',`Cắt lỗ ${cpSo(cpV('stop',-0.07)*100)}%`,'Từ phiên 3 trở đi → bán hết','A',true],
   ['4','Chốt bảo vệ (trả lại % đỉnh)','Lãi từng chạm ngưỡng rồi trả lại quá nửa → bán hết','C',cpBat('use_giveback',false)],
   ['5','Khoá lãi S1',`${erTiers(CP).map(([a,b])=>`đỉnh lãi ≥ <b>${cpSo(a*100)}%</b> → sàn <b>+${cpSo(b*100)}%</b>`).join('; ')} (sàn cao hơn thay sàn thấp hơn). Đỉnh lãi và lãi hiện tại tính bằng <b>giá đóng cửa</b>, đã gồm phí mua; đóng cửa ≤ sàn → bán ATC. Chỉ bán từ T+${cpV('sell_from',2)}; sàn thủng ở T+1/T+2 thì xét lại lúc ATC T+${cpV('sell_from',2)}. <b>Không phải lệnh dừng trong phiên</b> — phiên sập xuyên sàn thì bán ở giá đóng cửa phiên đó, có thể thấp hơn sàn. MA10 vẫn là cửa ra của lệnh lãi lớn. Thay luật "về bờ +1%" từ 26/09/2026`,'A',erTiers(CP).length>0],
   ['5b','Về bờ (luật cũ)',`Đã từng lãi ≥ ${cpSo(cpV('be_trigger',0.08)*100)}% mà tụt về ${cpSo(cpV('be_level',0.01)*100)}% → bán hết. Đã thay bằng khoá lãi S1 ngày 26/09/2026`,'C',cpBat('use_be',false)],
   ['6',`Van thời gian T+${cpV('t_valve',4)}`,`Đến phiên T+${cpV('t_valve',4)} mà lãi/lỗ (đã tính phí mua) ≤ 0 → bán hết. Lệnh chỉ cần <b>còn lãi dù nhỏ</b> là qua van, không cần đã bùng nổ. <b>Đây là cửa ra đông nhất</b>`,'A',true],
   ['7','Big sell khẩn','Giảm &gt; 4% + volume &gt; 120% TB20 → bán 1/2. Trùng chức năng với trailing MA và cửa đèn Cam','C',cpBat('use_big_sell',false)],
   ['8','Trailing lãi lớn',`Đã từng lãi ≥ <b>${cpSo(cpV('big_win',0.19)*100)}%</b> → ${cf} phiên đóng dưới MA${cpV('trail_fast',10)} → bán hết`,'A',true],
   ['9','Trailing mặc định',`${cf} phiên liên tiếp đóng dưới <b>MA${cpV('trail_ma',30)}</b> → bán hết. MA${cpV('trail_ma',30)} là cửa ra THẬT, không phải chỉ báo động như trang này từng ghi`,'A',true],
   ['10',`Chốt 1/3 khi vol &gt; ${cpSo(cpV('vol_ceil',4.5))}×`,'Lãi ≥ 20% và volume cực đoan → bán 1/3','C',cpBat('use_partial_take',false)],
   ['11','Đèn Cam — hạ 1/3',cpBat('orange_cut_only_if_worse',true)
      ? 'Đèn Cam <b>VÀ đèn xấu đi so với lúc mua</b> → hạ 1/3. Mua dưới đèn Cam thì đã vào có 35% rồi, hạ tiếp cũng vì đèn Cam là đếm hai lần một tín hiệu xấu'
      : 'Đèn Cam (≥ 5 ngày phân phối) → hạ 1/3 danh mục','C',cpBat('use_orange_cut',true)],
  ];
  root.innerHTML=`
  <h1>Hệ thống 9 lớp</h1>

  <div class="note info"><b>Ý tưởng cốt lõi, gói trong một câu:</b> lợi nhuận của hệ này không đến từ việc đoán đúng nhiều. Nó đến từ chỗ khác hẳn — <b>sai thì mất rất ít, đúng thì ăn rất lớn</b>. Cứ 10 lệnh thì khoảng 6 lệnh thua nhẹ (mỗi lệnh mất chừng 2–4%), và 4 lệnh thắng đậm. Hệ này sẽ khiến bạn sai liên tục, và đó chính là lúc nó đang hoạt động đúng.</div>

  <h2>Chín cánh cửa</h2>
  <div class="card">${gates.map(([n,t,q,d,g])=>`<div class="gate"><div class="gnum">${n}</div><div>
    <h4>${t}<span class="tag ${g}">${g}</span></h4><p>${d}</p></div></div>`).join('')}</div>

  <h2>Cửa 4 — các điều kiện của một điểm mua (xem cột Đang chạy)</h2>
  
  <div class="card"><table><thead><tr><th>#</th><th>Điều kiện</th><th>Ngưỡng</th><th>Hạng</th><th>Trạng thái</th></tr></thead><tbody>
   ${conds.map(([i,n,v,g,on])=>`<tr${on?'':' style="opacity:.55"'}><td>${i}</td><td class="sym">${n}</td><td>${v}</td><td><span class="tag ${g}">${g}</span></td><td>${cpNhan(on)}</td></tr>`).join('')}</tbody></table>
   <p class="muted" style="margin:12px 0 0">Đếm đúng: bộ máy đang bật <b>${conds.filter(c=>c[4]).length}/${conds.length}</b> điều kiện vào lệnh.</p></div>

  <h2>Cửa 8 — bộ thoát, nơi tiền thực sự được kiếm</h2>
  
  <div class="card"><table><thead><tr><th>#</th><th>Luật</th><th>Điều kiện</th><th>Hạng</th><th>Trạng thái</th></tr></thead><tbody>
   ${exits.map(([i,n,v,g,on])=>`<tr${on?'':' style="opacity:.55"'}><td>${i}</td><td class="sym">${n}</td><td>${v}</td><td><span class="tag ${g}">${g}</span></td><td>${cpNhan(on)}</td></tr>`).join('')}</tbody></table>
   <p class="muted" style="margin:12px 0 0">Thứ tự trong bảng là <b>thứ tự ưu tiên thật</b> trong bộ máy: luật đứng trước nổ trước. Đang bật <b>${exits.filter(e=>e[4]).length}/${exits.length}</b> cửa ra.</p></div>

  <h2>Ba thứ trong giáo trình đã bị dữ liệu bác bỏ</h2>
  <div class="three">
    <div class="card"><h3 style="margin-top:0">Trend Template (MA30&gt;MA50&gt;MA200)</h3>
      <p style="font-size:14px">Ba nguồn độc lập cùng phủ nhận. Cross-test cho thấy bộ lọc này sẽ chặn mất PLX (+46,7%) — deal tốt nhất trong hai deal đã kiểm chứng. Đo trên 418 mẫu, nhân tố này có edge <b class="neg">−2,5 điểm %</b> — âm nhất trong tám nhân tố. <b>Đã bỏ.</b></p></div>
    <div class="card"><h3 style="margin-top:0">Chốt lời cứng ở 18–20%</h3>
      <p style="font-size:14px">Chỉ 10,3% số lệnh tạo ra gần như toàn bộ lợi nhuận, với lãi trung vị +26,8%. Chốt ở mốc 18–20% là bán đúng ngay trước khi nhóm này bung ra. A/B test: tỷ lệ thắng rơi gần một nửa nhưng kỳ vọng <b class="pos">gấp ba</b>. <b>Đã bỏ</b> (trừ khi volume &gt; 4,5×).</p></div>
    <div class="card"><h3 style="margin-top:0">Phân bổ 25% NAV một mã</h3>
      <p style="font-size:14px">Công thức Kelly f* = W − (1−W)/R. Với số hiện tại (theo vị thế: W = ${Math.round(((D.prod.deal_metrics||{}).winrate||0)*1000)/10}%, R = ${String((D.prod.deal_metrics||{}).rr||'—').replace('.',',')}) full-Kelly ≈ <b>${(()=>{const w=(D.prod.deal_metrics||{}).winrate||0,r=(D.prod.deal_metrics||{}).rr||1;return (Math.max(0,w-(1-w)/r)*100).toFixed(1).replace('.',',')})()}%</b> NAV; nửa Kelly bằng một nửa số đó.
      <b style="color:var(--warn)">Cỡ lý thuyết 42% NAV, nhưng mỗi lệnh mới thực tế tối đa 30% (trần ngành cắt).</b>
      Đây là lựa chọn đánh đổi rủi ro lấy lợi nhuận, không phải mức an toàn theo Kelly.
      <span class="muted">(Số đo CŨ, cấu hình trước 21/09:)</span> quét cỡ vị thế khi đó cho thấy Sharpe đỉnh ở 30% NAV (1,77) chứ không phải 42% (1,71). <b>Thực tế đang chạy:</b> trần ngành 30% cắt mọi lệnh mới về tối đa 30% NAV; quét lại 24/09: bỏ trần ngành (để 42%) còn +610,8% so với +696,8%.</p></div>
  </div>

  <div class="note" style="margin-top:22px"><b>Điều bạn cần chấp nhận trước khi dùng hệ thống này:</b> tỷ lệ thắng của hệ khoảng ${Math.round(((D.prod.deal_metrics||{}).winrate||0.38)*100)}% theo vị thế (${Math.round((D.prod.metrics.winrate||0.46)*100)}% theo dòng lệnh). Bạn sẽ thấy chuỗi 5–6 lệnh lỗ liên tiếp. Mỗi lệnh lỗ chỉ mất 2–4%, nhưng cảm giác thì rất khó chịu. Nếu bạn tắt hệ thống sau chuỗi thua đó, bạn sẽ bỏ lỡ đúng nhóm lệnh tạo ra toàn bộ lợi nhuận.</div>
  `;
}
