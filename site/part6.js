
function pageSystem(root){
  const gates=[
   [0,'Vũ trụ cổ phiếu','Mã này có đủ lớn và đủ lịch sử để phân tích không?','HOSE + HNX (loại UPCOM) · vốn hoá &gt; 1.000 tỷ · ≥ 250 phiên lịch sử · ≥ 4 quý báo cáo liên tiếp.','B'],
   [1,'Cổng rủi ro','Doanh nghiệp này có nguy cơ vỡ nợ không?','<b>Quyền phủ quyết tuyệt đối.</b> ICR &lt; 1,5 → chặn. CFO &lt; 0 → chặn. D/E &gt; 4,0 → chặn. Riêng ngân hàng: NPL &gt; 3% hoặc CAR &lt; 8% → chặn. ICR 1,5–2,5 → cờ vàng, cỡ vị thế × 0,5.','A'],
   [2,'Chấm điểm CANSLIM','Nó có đang tăng trưởng thật không?','Thang 100 điểm — <b>cơ bản 55đ + kỹ thuật 45đ</b>. LNST YoY ≥ 25% (15đ) · <b>doanh thu YoY ≥ 15% (15đ — mới)</b> · tăng tốc QoQ (+5đ) · CAGR 3 năm ≥ 20% (10đ) · <b>ROE ≥ 17% (10đ — mới)</b> · cách đỉnh 52 tuần ≤ 15% (10đ) · volume ≥ 1,2× (5đ) · RS ≥ 70 (15đ) · GTGD ≥ 15 tỷ (10đ) · <b>return 3 tháng (tối đa 5đ — mới)</b>. Điểm cao nhất thực tế trong 1.213 mã là 89,2 — thang 100 gần như không ai chạm trần. Điểm <b>không</b> phải điều kiện vào lệnh, chỉ là sàn mềm + xếp hạng.','A'],
   [3,'Nền giá','Giá đã tích luỹ đủ chặt chưa?','Nền ≥ 30 phiên trước điểm mua, biên độ nền hẹp. Nền càng chặt thì cỡ vị thế càng lớn (hạng A → × 1,2).','A'],
   [4,'Điểm mua','Hôm nay có phải phiên tiền lớn nhảy vào không?','Phải đủ <b>cả 8 điều kiện trong cùng một phiên</b>. Xem bảng bên dưới.','A'],
   [5,'Cổng thị trường','Thị trường chung có cho phép mua không?','Hệ đèn 4 mức từ ba tín hiệu: G1 (chỉ số đều trọng số vs MA200), G2 (VN-Index vs MA50), G3 (đếm ngày phân phối 25 phiên). <b>Luật vàng: cổng chỉ chặn MỞ LỆNH MỚI</b> — vị thế đang cầm vẫn chạy theo bộ thoát bình thường.','A'],
   [6,'Lọc ngành','Danh mục có bị dồn quá nhiều vào một ngành không?','Trần 30% NAV cho một nhóm ngành ICB.','B'],
   [7,'Cỡ vị thế','Nên bỏ bao nhiêu tiền vào?','<b>42% NAV</b> × hệ số đèn (Xanh 1,0 · Vàng 0,6 · Cam 0,35 · Đỏ 0,2) × hệ số nền (1,2 / 1,0) × hệ số rủi ro (cờ vàng 0,5). Trần <b>50% NAV</b> một mã, <b>100% NAV</b> toàn danh mục, tối đa <b>12 mã</b>, sàn 2% NAV. <b style="color:var(--warn)">Trang này từng ghi 10%/20%/60% — đó là giá trị mặc định của engine, KHÔNG phải cấu hình đang chạy. Toàn bộ con số hiệu suất trên trang được tạo ra ở mức 42%.</b> Kelly tính ra 19,6%; 42% là <b>hơn hai lần Kelly</b> — đây là lựa chọn đánh đổi rủi ro lấy lợi nhuận, không phải mức an toàn.','A'],
   [8,'Bộ thoát','Khi nào thì ra?','Kiểm tra theo đúng thứ tự ưu tiên. Đây là nơi tiền thực sự được kiếm — xem bảng bên dưới.','A'],
   [9,'Pyramid','Có nên gia tăng vị thế không?','Phiên 4–7 sau điểm mua, đang lãi ≥ 10%, giá ≥ 99,9% đỉnh 10 phiên, chỉ 1 lần, chỉ khi đèn Xanh. Thêm 50% vị thế gốc.','B'],
  ];
  const conds=[
   ['1','Biên độ tăng giá','HOSE ≥ 5,8% · HNX ≥ 8,8% — cận trần hoặc trần','A'],
   ['2','Khối lượng sàn dưới','≥ 2,0 × trung bình 20 phiên — tiền thật đổ vào','A'],
   ['3','Giá trị giao dịch phiên','≥ 15 tỷ — đủ thanh khoản để sau này còn thoát được','A'],
   ['4','Nền 30 phiên sạch','Đã tích luỹ yên tĩnh, không phải mã vừa chạy xong','A'],
   ['5','LNST YoY ngoài vùng yếu','Ngoài khoảng 0–25%','B'],
   ['6','Trần khối lượng','vol ≤ 4,5 × TB20 — volume 450–600% là dấu hiệu "đổi thuyền trưởng"','C'],
   ['7','Biến động TB20','≥ 1,5%/ngày — loại các mã "chết"','A'],
   ['8','Đóng cửa nửa trên nến','close ≥ (high+low)/2 — tránh bẫy UTAD','C'],
  ];
  const exits=[
   ['1','Hard stop −10%','Bán hết, áp dụng mọi phiên','B'],
   ['2','Cây nến bảo vệ','Đóng cửa dưới low của nến breakout → bán hết','C'],
   ['3','Cắt lỗ −7%','Từ phiên 3 trở đi → bán hết','A'],
   ['4','Van thời gian T+N','Hết phiên thứ N mà lệnh vẫn chưa có lãi → bán hết, bất kể lý do','A'],
   ['5','Big sell khẩn','Giảm &gt; 4% + volume &gt; 120% TB20 → bán 1/2','C'],
   ['6','Trailing lãi lớn','Đã từng lãi ≥ 25% → 2 phiên dưới MA10 → bán hết','A'],
   ['7','Trailing mặc định','2 phiên liên tiếp đóng dưới đường trung bình → bán hết','A'],
   ['8','Cảnh báo MA30/MA50','Chỉ báo động, KHÔNG đóng lệnh','A'],
   ['9','Rủi ro hệ thống','Đèn Cam (≥ 5 ngày phân phối) → hạ 1/3 danh mục','C'],
  ];
  root.innerHTML=`
  <h1>Hệ thống 9 lớp</h1>

  <div class="note info"><b>Ý tưởng cốt lõi, gói trong một câu:</b> lợi nhuận của hệ này không đến từ việc đoán đúng nhiều. Nó đến từ chỗ khác hẳn — <b>sai thì mất rất ít, đúng thì ăn rất lớn</b>. Cứ 10 lệnh thì khoảng 6 lệnh thua nhẹ (mỗi lệnh mất chừng 2–4%), và 4 lệnh thắng đậm. Hệ này sẽ khiến bạn sai liên tục, và đó chính là lúc nó đang hoạt động đúng.</div>

  <h2>Chín cánh cửa</h2>
  <div class="card">${gates.map(([n,t,q,d,g])=>`<div class="gate"><div class="gnum">${n}</div><div>
    <h4>${t}<span class="tag ${g}">${g}</span></h4><p>${d}</p></div></div>`).join('')}</div>

  <h2>Cửa 4 — tám điều kiện của một điểm mua</h2>
  
  <div class="card"><table><thead><tr><th>#</th><th>Điều kiện</th><th>Ngưỡng</th><th>Hạng</th></tr></thead><tbody>
   ${conds.map(([i,n,v,g])=>`<tr><td>${i}</td><td class="sym">${n}</td><td>${v}</td><td><span class="tag ${g}">${g}</span></td></tr>`).join('')}</tbody></table></div>

  <h2>Cửa 8 — bộ thoát, nơi tiền thực sự được kiếm</h2>
  
  <div class="card"><table><thead><tr><th>#</th><th>Luật</th><th>Điều kiện</th><th>Hạng</th></tr></thead><tbody>
   ${exits.map(([i,n,v,g])=>`<tr><td>${i}</td><td class="sym">${n}</td><td>${v}</td><td><span class="tag ${g}">${g}</span></td></tr>`).join('')}</tbody></table></div>

  <h2>Ba thứ trong giáo trình đã bị dữ liệu bác bỏ</h2>
  <div class="three">
    <div class="card"><h3 style="margin-top:0">Trend Template (MA30&gt;MA50&gt;MA200)</h3>
      <p style="font-size:14px">Ba nguồn độc lập cùng phủ nhận. Cross-test cho thấy bộ lọc này sẽ chặn mất PLX (+46,7%) — deal tốt nhất trong hai deal đã kiểm chứng. Đo trên 418 mẫu, nhân tố này có edge <b class="neg">−2,5 điểm %</b> — âm nhất trong tám nhân tố. <b>Đã bỏ.</b></p></div>
    <div class="card"><h3 style="margin-top:0">Chốt lời cứng ở 18–20%</h3>
      <p style="font-size:14px">Chỉ 10,3% số lệnh tạo ra gần như toàn bộ lợi nhuận, với lãi trung vị +26,8%. Chốt ở mốc 18–20% là bán đúng ngay trước khi nhóm này bung ra. A/B test: tỷ lệ thắng rơi gần một nửa nhưng kỳ vọng <b class="pos">gấp ba</b>. <b>Đã bỏ</b> (trừ khi volume &gt; 4,5×).</p></div>
    <div class="card"><h3 style="margin-top:0">Phân bổ 25% NAV một mã</h3>
      <p style="font-size:14px">Công thức Kelly f* = W − (1−W)/R với W=40%, R=3,0 cho ra <b>20%</b>, không phải 25%. Full-Kelly là mức tối đa lý thuyết; thực hành chuẩn là nửa Kelly, tức khoảng 10% NAV.
      <b style="color:var(--warn)">Nhưng cấu hình đang chạy là 42% NAV — hơn hai lần full-Kelly.</b>
      Đây là lựa chọn đánh đổi rủi ro lấy lợi nhuận, không phải mức an toàn theo Kelly.
      Quét cỡ vị thế cho thấy Sharpe đạt đỉnh ở 30% NAV (1,77) chứ không phải 42% (1,71):
      42% mua thêm lợi nhuận bằng cách trả Profit Factor 4,70 xuống 4,04.</p></div>
  </div>

  <div class="note" style="margin-top:22px"><b>Điều bạn cần chấp nhận trước khi dùng hệ thống này:</b> tỷ lệ thắng của hệ nằm quanh 30–42%. Bạn sẽ thấy chuỗi 5–6 lệnh lỗ liên tiếp. Mỗi lệnh lỗ chỉ mất 2–4%, nhưng cảm giác thì rất khó chịu. Nếu bạn tắt hệ thống sau chuỗi thua đó, bạn sẽ bỏ lỡ đúng nhóm lệnh tạo ra toàn bộ lợi nhuận.</div>
  `;
}
