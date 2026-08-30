/* ============================================================================
   TRANG KIỂM ĐỊNH — Robustness & Validation
   Đọc data/robust.json (sinh bởi robustness.py) và trình bày tám bài kiểm tra.

   Nguyên tắc trình bày ở trang này khác mọi trang khác trong site: KHÔNG khoe.
   Mỗi bài kiểm tra được viết ra để có thể TRƯỢT, và khi nó trượt thì trang phải
   nói thẳng là trượt. Một trang kiểm định chỉ toàn màu xanh là một trang vô dụng.
   ========================================================================== */

function pageKiemDinh(root) {
  const V = D.robust;
  if (!V) {
    root.innerHTML = `<h1>Kiểm định</h1>
      <div class="note warn"><b>Chưa có kết quả kiểm định.</b>
      Chạy <code>python3 robustness.py</code> để sinh <code>data/robust.json</code>,
      rồi dựng lại trang. Bộ kiểm định mất khoảng 8–15 phút vì nó chạy lại backtest
      vài chục lần với tham số khác nhau.</div>`;
    return;
  }
  const S = V.scorecard, P = V.prod, PROD_SIZE = 0.42;
  const sg = v => (v >= 0 ? '+' : '−') + Math.abs(v * 100).toFixed(1) + '%';
  const cls = v => v >= 0 ? 'pos' : 'neg';
  const dau = ok => ok ? '<span class="kdok">ĐẠT</span>' : '<span class="kdno">TRƯỢT</span>';

  root.innerHTML = `
  <div class="hero">
    <div class="badge">Sinh tự động · ${V.n_phien} phiên · chốt ${V.asof} · chạy hết ${V.runtime_s}s</div>
    <h1>Nếu tôi cố tình phá hệ thống này,<br>nó còn kiếm được tiền không?</h1>
    <p class="lead">Backtest đẹp là chuyện dễ: vặn tham số cho vừa quá khứ thì đường vốn nào cũng dựng đứng.
    Trang này hỏi câu ngược lại. Tám bài dưới đây được viết ra để hệ thống <b>trượt</b> —
    đổi ngưỡng, tăng trượt giá, bỏ những deal lãi nhất, xáo tung thứ tự thắng thua,
    và bắt tham số chọn bằng quá khứ đi thi trên năm chưa từng thấy.</p>
  </div>

  <div class="card" style="margin-bottom:18px;border-color:${S.san_sang ? 'var(--good)' : 'var(--warn)'}">
    <div style="display:flex;gap:16px;align-items:baseline;flex-wrap:wrap">
      <div style="font-size:28px;font-weight:750;color:var(--warn)">
        NGHIÊN CỨU — CHƯA CHẠY TIỀN THẬT</div>
      <div class="muted">${S.san_sang
        ? 'Năm tầng dưới đây đều đạt, nhưng <b>năm tầng này không đủ để gọi là sẵn sàng</b>. Chúng chỉ kiểm phần mô hình. Ba nhóm câu hỏi nặng hơn — dữ liệu có đúng point-in-time không, lệnh cận trần có khớp được thật không, và edge có sống qua nhiều chế độ thị trường không — vẫn chưa được trả lời. Xem mục "Những gì bộ kiểm định này KHÔNG chứng minh" ở cuối trang.'
        : 'Còn tầng chưa qua. Một tầng trượt không có nghĩa hệ thống hỏng, nhưng có nghĩa là chưa nên tăng vốn.'}</div>
    </div>
    <div class="kdtang">${S.tang.map(t => `
      <div class="kdt ${t.dat ? 'ok' : 'no'}">
        <div class="kdtn">Tầng ${t.tang} ${dau(t.dat)}</div>
        <div class="kdtt">${t.ten}</div>
        <div class="muted" style="font-size:12.5px">${t.ly_do}</div>
      </div>`).join('')}</div>
  </div>

  <div class="grid kpis">
    ${kpi('Lợi nhuận toàn kỳ', sg(P.total_return), 'mốc so sánh của mọi bài dưới', cls(P.total_return))}
    ${kpi('CAGR', sg(P.cagr), 'lãi kép mỗi năm')}
    ${kpi('Sụt tối đa', '−' + (P.maxdd * 100).toFixed(1) + '%', 'đáy sâu nhất so đỉnh', 'neg')}
    ${kpi('Profit Factor', P.pf, 'tổng lãi ÷ tổng lỗ')}
    ${kpi('Sharpe', P.sharpe, 'lợi nhuận trên độ dao động')}
    ${kpi('Số lệnh', P.trades, `${P.per_year}/năm · thắng ${(P.winrate * 100).toFixed(0)}%`)}
  </div>

  <h2>1 · Walk-forward — tham số chọn bằng quá khứ, chấm điểm trên tương lai</h2>
  <p>Đây là bài nghiêm khắc nhất. Backtest toàn kỳ luôn đẹp vì tham số đã được nhìn thấy cả kỳ.
  Walk-forward không cho phép điều đó: mỗi cửa sổ chỉ được dùng dữ liệu <b>trước</b> năm thi
  để chọn tham số, rồi đem đúng bộ đó chấm trên năm chưa hề đụng tới.</p>
  <div class="card tblwrap"><table><thead><tr>
    <th>Huấn luyện</th><th>Thi trên</th><th>Tham số tự chọn</th>
    <th style="text-align:right">Lợi nhuận (train)</th><th style="text-align:right">Lợi nhuận (thi)</th>
    <th style="text-align:right">PF (thi)</th><th style="text-align:right">Sụt (thi)</th><th style="text-align:right">Lệnh</th>
  </tr></thead><tbody>${V.walk_forward.windows.map(w => `<tr>
    <td class="sym">${w.train}</td><td class="sym">${w.test}</td>
    <td class="muted" style="font-size:12.5px">nền ${(w.chon.base_range * 100).toFixed(0)}% · sàn điểm ${w.chon.score_floor}</td>
    <td style="text-align:right" class="${cls(w.train_m.total_return)}">${sg(w.train_m.total_return)}</td>
    <td style="text-align:right;font-weight:660" class="${cls(w.test_m.total_return)}">${sg(w.test_m.total_return)}</td>
    <td style="text-align:right">${w.test_m.pf ?? '—'}</td>
    <td style="text-align:right" class="neg">−${(w.test_m.maxdd * 100).toFixed(1)}%</td>
    <td style="text-align:right">${w.test_m.trades}</td></tr>`).join('')}
  </tbody></table></div>
  <p class="muted" style="margin-top:8px;font-size:12.5px">Lưới tham số của cửa sổ huấn luyện cố ý nhỏ
  (nền 16/18/20%, sàn điểm 42/45/48) và chọn theo <b>Sharpe</b> chứ không theo lợi nhuận thô —
  lợi nhuận thô luôn kéo về phía tham số liều lĩnh nhất. Đây không phải toàn bộ không gian tham số,
  nhưng đủ để trả lời câu hỏi "chọn bằng quá khứ có sống sang tương lai không".</p>

  <h3>Đối chiếu — chính cấu hình đang chạy, không tối ưu gì, trên từng năm</h3>
  <div class="card tblwrap"><table><thead><tr><th>Năm</th>
    <th style="text-align:right">Lợi nhuận</th><th style="text-align:right">PF</th>
    <th style="text-align:right">Sụt</th><th style="text-align:right">Lệnh</th><th style="text-align:right">Thắng</th>
  </tr></thead><tbody>${V.walk_forward.prod_by_year.map(x => `<tr>
    <td class="sym">${x.nam}</td>
    <td style="text-align:right;font-weight:660" class="${cls(x.m.total_return)}">${sg(x.m.total_return)}</td>
    <td style="text-align:right">${x.m.pf ?? '—'}</td>
    <td style="text-align:right" class="neg">−${(x.m.maxdd * 100).toFixed(1)}%</td>
    <td style="text-align:right">${x.m.trades}</td>
    <td style="text-align:right">${(x.m.winrate * 100).toFixed(0)}%</td></tr>`).join('')}
  </tbody></table></div>

  <h2>2 · Trượt giá — kể cả kịch bản trắng bên mua</h2>
  <p>Test 0,2% hai chiều là một giả định dễ chịu hơn thực tế. Ở thị trường Việt Nam,
  chiều <b>mua trần</b> thường trượt ít nhưng dễ thiếu khối lượng; chiều <b>bán tháo</b> khi gãy MA
  thì trượt rất nặng vì trắng bên mua. Nên bảng dưới tách hai chiều ra.</p>
  <div class="two">
    <div class="card"><h3 style="margin:0 0 8px">Trượt giá đối xứng</h3>
      <div class="tblwrap"><table><thead><tr><th>Mức</th>
        <th style="text-align:right">Lợi nhuận</th><th style="text-align:right">Sụt</th>
        <th style="text-align:right">PF</th><th style="text-align:right">Sharpe</th></tr></thead><tbody>
        ${V.slippage.doi_xung.map(x => `<tr>
          <td class="sym">${(x.slip * 100).toFixed(2)}%</td>
          <td style="text-align:right" class="${cls(x.m.total_return)}">${sg(x.m.total_return)}</td>
          <td style="text-align:right" class="neg">−${(x.m.maxdd * 100).toFixed(1)}%</td>
          <td style="text-align:right">${x.m.pf ?? '—'}</td>
          <td style="text-align:right">${x.m.sharpe ?? '—'}</td></tr>`).join('')}
      </tbody></table></div></div>
    <div class="card"><h3 style="margin:0 0 8px">Bất đối xứng mua / bán</h3>
      <div class="tblwrap"><table><thead><tr><th>Kịch bản</th><th style="text-align:right">Mua</th>
        <th style="text-align:right">Bán</th><th style="text-align:right">Lợi nhuận</th>
        <th style="text-align:right">Sụt</th><th style="text-align:right">PF</th></tr></thead><tbody>
        ${V.slippage.bat_doi_xung.map(x => `<tr>
          <td class="sym">${x.ten}</td>
          <td style="text-align:right" class="muted">${(x.mua * 100).toFixed(2)}%</td>
          <td style="text-align:right" class="muted">${(x.ban * 100).toFixed(2)}%</td>
          <td style="text-align:right;font-weight:660" class="${cls(x.m.total_return)}">${sg(x.m.total_return)}</td>
          <td style="text-align:right" class="neg">−${(x.m.maxdd * 100).toFixed(1)}%</td>
          <td style="text-align:right">${x.m.pf ?? '—'}</td></tr>`).join('')}
      </tbody></table></div></div>
  </div>

  <h2>3 · Độ nhạy tham số — nhìn vùng phẳng, không nhìn đỉnh</h2>
  <p>Cách đọc <b>duy nhất</b> đúng ở đây: đừng tìm con số cao nhất. Nếu chỉ một điểm cho kết quả tốt
  còn hai bên sụp thì đó là dấu hiệu tham số đã bị vặn cho vừa quá khứ. Vùng phẳng —
  nhiều giá trị liền kề cho kết quả na ná — mới là dấu hiệu có quy luật thật.</p>
  <div id="kdSweep"></div>

  <h2>4 · Bỏ những deal lãi nhất</h2>
  <p>Tỷ lệ thắng chỉ ${(P.winrate * 100).toFixed(0)}%, nên phần lớn lợi nhuận đến từ một nhóm nhỏ deal thắng đậm.
  Câu hỏi là: nhóm đó có phải chỉ vài lần may mắn không? Nếu bỏ 3 deal mà PF sụp từ ${P.pf} xuống dưới 1,5
  thì cái gọi là "edge" thực ra là một chuỗi may.</p>
  <div class="card tblwrap"><table><thead><tr><th>Kịch bản</th>
    <th style="text-align:right">Lợi nhuận</th><th style="text-align:right">PF</th>
    <th style="text-align:right">Sụt</th><th style="text-align:right">Thắng</th><th>Deal bị bỏ</th>
  </tr></thead><tbody>${V.remove_winners.map(x => `<tr>
    <td class="sym">${x.bo}</td>
    <td style="text-align:right;font-weight:660" class="${cls(x.m.total_return)}">${sg(x.m.total_return)}</td>
    <td style="text-align:right">${x.m.pf ?? '—'}</td>
    <td style="text-align:right" class="neg">−${(x.m.maxdd * 100).toFixed(1)}%</td>
    <td style="text-align:right">${(x.m.winrate * 100).toFixed(0)}%</td>
    <td class="muted" style="font-size:12.5px">${(x.deal_bo || []).map(d => `${d.sym} ${d.pnl > 0 ? '+' : ''}${d.pnl}%`).join(' · ') || '—'}</td>
  </tr>`).join('')}</tbody></table></div>
  <div class="note warn" style="margin-top:8px"><b>Cột "Sụt" ở bảng này là thước đo KHÁC
  với −${(P.maxdd * 100).toFixed(1)}% ở đầu trang.</b> Đầu trang đo trên đường NAV từng phiên
  (có ngày không cầm gì, có ngày cầm bốn mã). Bảng này đo trên chuỗi deal nối tiếp nhau.
  Hai con số không so được với nhau — chỉ so được các dòng <i>trong cùng bảng này</i>.</div>
  <p class="muted" style="margin-top:8px;font-size:12.5px">Đường vốn ở bảng này dựng lại từ chuỗi deal
  theo <b>đúng thứ tự thời gian</b>, với cỡ vị thế hiệu dụng <b>${((V.frac_hieu_chuan||0)*100).toFixed(1)}%</b> mỗi lệnh —
  con số này được hiệu chuẩn sao cho dòng "Nguyên bản" khớp đúng backtest đầy đủ
  (${sg(P.total_return)}), vì bot chạy tới 12 vị thế song song nên vốn được chia sẻ, không phải
  ${(PROD_SIZE*100).toFixed(0)}% cho mỗi lệnh nối tiếp nhau. Nhờ vậy mọi dòng dưới nó so được với nhau
  trên cùng một thước đo.</p>

  <h2>5 · Monte Carlo — cùng edge, thứ tự khác đi</h2>
  <p>Lấy đúng ${V.monte_carlo.n_deal} deal đã có, xáo tung thứ tự, chạy lại ${V.monte_carlo.n_sim.toLocaleString('vi')} lần.
  Đường vốn đơn lẻ không trả lời được câu hỏi này: <b>nếu chuỗi thắng thua rơi khác đi, tôi có gồng nổi không?</b></p>
  <div class="grid kpis">
    ${kpi('Sụt trung vị', '−' + (V.monte_carlo.dd.p50 * 100).toFixed(1) + '%', 'một nửa số kịch bản nông hơn mức này', 'neg')}
    ${kpi('Sụt ở p95', '−' + (V.monte_carlo.dd.p95 * 100).toFixed(1) + '%', '5% kịch bản còn sâu hơn', 'neg')}
    ${kpi('Sụt xấu nhất', '−' + (V.monte_carlo.dd.worst * 100).toFixed(1) + '%', `trong ${V.monte_carlo.n_sim.toLocaleString('vi')} lần chạy`, 'neg')}
    ${kpi('Chuỗi thua dài nhất', V.monte_carlo.streak.p99 + ' lệnh', `p99 · xấu nhất ${V.monte_carlo.streak.worst} lệnh`)}
    ${kpi('P(sụt > 25%)', (V.monte_carlo.p_dd_25 * 100).toFixed(1) + '%', 'xác suất gặp mức sụt này')}
    ${kpi('P(lỗ toàn kỳ)', (V.monte_carlo.p_lo * 100).toFixed(1) + '%', 'kịch bản kết thúc dưới vốn gốc')}
  </div>
  <div class="card" style="margin-top:14px"><h3 style="margin:0 0 6px">Phân bố mức sụt tối đa</h3>
    <div class="muted" style="font-size:12.5px;margin-bottom:8px">Mỗi cột = số kịch bản rơi vào khoảng sụt đó.
    Đuôi bên phải mới là thứ đáng nhìn: đó là những đường vốn anh sẽ phải sống cùng nếu xui.</div>
    <div id="kdMC"></div></div>
  <div class="note warn" style="margin-top:12px"><b>Phép mô phỏng này CHỈ nói được về mức sụt và chuỗi thua.</b>
  Xáo thứ tự deal không làm đổi tích lãi kép, nên phần <i>lợi nhuận</i> ra y hệt nhau ở mọi phân vị —
  đó là tính chất của phép nhân, không phải bằng chứng hệ ổn định. Trang này vì thế không in
  phân vị lợi nhuận, và <b>đừng trích "P(lỗ) = 0%"</b> như một kết luận.
  <div style="margin-top:8px">Hạn chế thứ hai, nặng hơn: xáo từng deal riêng lẻ <b>phá mất tính bầy đàn</b> —
  ngoài đời các mã cùng ngành gãy cùng lúc, nhiều vị thế mở song song, và breakout hỏng hàng loạt
  trong một cú đảo chiều. Mức sụt thật vì thế <b>nặng hơn</b> con số dưới đây. Muốn đúng phải
  bootstrap theo khối ngày hoặc theo nhóm tín hiệu cùng phiên — chưa làm.</div></div>

  <div class="note" style="margin-top:12px"><b>Con số cần nhớ, không phải con số để khoe.</b>
  Sụt tối đa trong backtest là −${(P.maxdd * 100).toFixed(1)}%, nhưng Monte Carlo nói rằng cùng bộ deal ấy
  có thể cho ra mức sụt <b>−${(V.monte_carlo.dd.p95 * 100).toFixed(1)}%</b> ở kịch bản xấu 1 trên 20,
  và chuỗi <b>${V.monte_carlo.streak.p99} lệnh thua liên tiếp</b> là chuyện hoàn toàn bình thường.
  Nếu anh không chịu được con số đó thì phải hạ cỡ vị thế <b>trước</b>, chứ không phải hạ giữa chuỗi thua.</div>

  <h2>6 · Nhìn trước — kiểm tra bằng khẳng định, không bằng lời hứa</h2>
  <p>Nhìn trước là lỗi giết chết nhiều hệ thống hơn mọi lỗi khác cộng lại, vì nó không báo lỗi —
  nó chỉ làm backtest đẹp lên. Sáu phép thử dưới đây <b>chạy thật</b> mỗi lần kiểm định.</p>
  <div class="card"><div class="kdchk">${V.lookahead.checks.map(c => `
    <div class="kdc ${c.ok ? 'ok' : 'no'}">
      <div>${c.ok ? '✓' : '✕'}</div>
      <div><div style="color:var(--text-primary);font-weight:600">${c.ten}</div>
      <div class="muted" style="font-size:12.5px">${c.chi_tiet}</div></div>
    </div>`).join('')}</div></div>

  <h2>7 · Ngắt mạch bảo vệ vốn</h2>
  <p>Với tỷ lệ thắng ${(P.winrate * 100).toFixed(0)}%, chuỗi ${V.monte_carlo.streak.p90}–${V.monte_carlo.streak.p99}
  lệnh thua liên tiếp là chuyện xác suất bình thường, không phải dấu hiệu hệ thống hỏng.
  Ngắt mạch <b>không đoán thị trường</b> — nó chỉ hạ cỡ vị thế <b>sau khi</b> thiệt hại đã xảy ra,
  và tự mở lại khi NAV lập đỉnh mới. Bảng dưới là A/B thật, không phải ý kiến.</p>
  <div class="card tblwrap"><table><thead><tr><th>Quy tắc</th>
    <th style="text-align:right">Lợi nhuận</th><th style="text-align:right">Sụt</th>
    <th style="text-align:right">PF</th><th style="text-align:right">Sharpe</th>
    <th style="text-align:right">Lệnh</th><th style="text-align:right">Số lần ngắt</th>
  </tr></thead><tbody>${V.circuit_breaker.map((x, i) => `<tr${i === 0 ? ' style="background:var(--surface-2)"' : ''}>
    <td class="sym">${x.ten}</td>
    <td style="text-align:right;font-weight:660" class="${cls(x.m.total_return)}">${sg(x.m.total_return)}</td>
    <td style="text-align:right" class="neg">−${(x.m.maxdd * 100).toFixed(1)}%</td>
    <td style="text-align:right">${x.m.pf ?? '—'}</td>
    <td style="text-align:right">${x.m.sharpe ?? '—'}</td>
    <td style="text-align:right">${x.m.trades}</td>
    <td style="text-align:right">${x.n_ngat}</td></tr>`).join('')}
  </tbody></table></div>
  <div class="note info" style="margin-top:10px"><b>Ngắt mạch đang TẮT trong cấu hình chạy thật.</b>
  Bảng trên chỉ là thí nghiệm. Bật hay không là quyết định của anh Sơn, không phải của bot —
  và nếu nó làm lợi nhuận giảm mà mức sụt không giảm tương xứng thì đừng bật.</div>

  <h2>8 · Kẹt thanh khoản T+2.5</h2>
  <p>Kịch bản mà van T+6 hoàn toàn vô hiệu: mua xong gặp bull-trap, sàn liên tiếp hai phiên
  trong lúc hàng chưa về nên không bán được gì cả. Giả định
  <b>${(V.t25.ty_le * 100).toFixed(0)}% số deal</b> (${V.t25.n_deal_dinh} deal) dính cú sốc
  <b>${(V.t25.sock * 100).toFixed(1)}%</b> — đúng bằng hai phiên sàn HOSE.</p>
  <div class="grid kpis">
    ${kpi('Sụt gốc', '−' + (V.t25.goc.maxdd * 100).toFixed(1) + '%', 'backtest không có cú sốc', 'neg')}
    ${kpi('Sụt trung vị khi kẹt', '−' + (V.t25.dd.p50 * 100).toFixed(1) + '%', `${V.t25.n_sim.toLocaleString('vi')} lần mô phỏng`, 'neg')}
    ${kpi('Sụt p95 khi kẹt', '−' + (V.t25.dd.p95 * 100).toFixed(1) + '%', 'kịch bản xấu 1/20', 'neg')}
    ${kpi('Lợi nhuận trung vị', sg(V.t25.ret.p50), 'sau khi trừ cú sốc', cls(V.t25.ret.p50))}
  </div>

  <h2>9 · Khớp lệnh thật — bài nặng nhất, và hệ trượt ở đây</h2>
  ${!D.congb ? '<div class="note">Chưa chạy <code>cong_b.py</code>.</div>' : (() => {
    const B = D.congb;
    const b1 = B.b1_khop_lenh, b2 = B.b2_khong_khop, b3 = B.b3_suc_chua;
    const goc = b1.khong_truot[0], sau = b1.khong_truot[1];
    const mat = (1 - (1 + sau.total_return) / (1 + goc.total_return)) * 100;
    return `
    <div class="note warn"><b>Backtest giả định mua đúng giá đóng cửa của phiên bắn tín hiệu.</b>
    Nhưng giá đóng cửa, giá cao nhất, giá thấp nhất và khối lượng cả phiên chỉ biết được
    <i>sau khi</i> phiên đóng. Lúc 14h25 anh chưa biết khối lượng cuối phiên là bao nhiêu.
    Đây <b>không phải trượt giá — đây là biết trước</b>. Bảng dưới đo xem mất bao nhiêu khi bỏ giả định đó.</div>
    <div class="card tblwrap" style="margin-top:12px"><table><thead><tr><th>Giả định khớp lệnh</th>
      <th style="text-align:right">Lợi nhuận</th><th style="text-align:right">Sụt</th>
      <th style="text-align:right">PF</th><th style="text-align:right">Lệnh</th></tr></thead><tbody>
      ${b1.khong_truot.concat(b1.co_truot).map((x, i) => `<tr${i === 0 ? ' style="background:var(--surface-2)"' : ''}>
        <td class="sym">${esc(x.ten)}</td>
        <td style="text-align:right;font-weight:660" class="${cls(x.total_return)}">${sg(x.total_return)}</td>
        <td style="text-align:right" class="neg">−${(x.maxdd * 100).toFixed(1)}%</td>
        <td style="text-align:right">${x.pf}</td>
        <td style="text-align:right">${x.trades}</td></tr>`).join('')}
    </tbody></table></div>
    <div class="note" style="margin-top:10px"><b>Chuyển từ khớp giá đóng cửa sang khớp phiên sau
    làm mất ${mat.toFixed(0)}% tổng lợi nhuận.</b> Đây là con số chạy dưới đúng cấu hình đang dùng,
    không phải thí nghiệm cấu hình cũ. Nghĩa là <b>edge của hệ nằm phần lớn ở khả năng khớp
    trong chính phiên bắn tín hiệu</b> — nếu anh không có mặt từ 14h00 tới ATC thì đừng dùng hệ này.</div>

    <h3 style="margin-top:24px">Rủi ro không khớp được lệnh</h3>
    <p><b>${b2.n_cham_tran}/${b2.n_lenh} lệnh (${(b2.n_cham_tran / b2.n_lenh * 100).toFixed(0)}%)
    vào đúng phiên cổ phiếu chạm trần</b>, trong đó ${b2.n_mong} lệnh có khối lượng dưới 3× trung bình
    20 phiên — dấu hiệu bên bán đã rút, khả năng cao không mua đủ. Trượt giá không mô phỏng được
    chuyện này: đây là <b>mất luôn cơ hội</b>, không phải mua đắt hơn.</p>
    <div class="card tblwrap"><table><thead><tr><th>Kịch bản</th>
      <th style="text-align:right">Số lệnh mất</th><th style="text-align:right">Lợi nhuận trung vị</th>
      <th style="text-align:right">Kịch bản xấu (p5)</th></tr></thead><tbody>
      <tr style="background:var(--surface-2)"><td class="sym">Khớp được hết (giả định hiện tại)</td>
        <td style="text-align:right">0</td>
        <td style="text-align:right;font-weight:660" class="pos">${sg(b2.goc)}</td>
        <td style="text-align:right">—</td></tr>
      ${b2.kich_ban.map(x => `<tr>
        <td class="sym">Hỏng ${(x.ty_le * 100).toFixed(0)}% số lệnh chạm trần</td>
        <td style="text-align:right">${x.n_bo}</td>
        <td style="text-align:right;font-weight:660" class="${cls(x.p50)}">${sg(x.p50)}</td>
        <td style="text-align:right" class="${cls(x.p5)}">${sg(x.p5)}</td></tr>`).join('')}
    </tbody></table></div>

    <h3 style="margin-top:24px">Sức chứa vốn — hệ này chạy được tới bao nhiêu tiền</h3>
    <p>GTGD phiên vào lệnh trung vị <b>${(b3.gtgd_trungvi / 1e9).toFixed(0)} tỷ</b>.
    Một lệnh vượt 10% GTGD phiên là bắt đầu tự đẩy giá mình lên.</p>
    <div class="card tblwrap"><table><thead><tr><th>Vốn</th>
      <th style="text-align:right">Mỗi lệnh</th><th style="text-align:right">% GTGD phiên</th>
      <th style="text-align:right">Tỷ lệ lệnh vượt 10% GTGD</th><th>Đánh giá</th></tr></thead><tbody>
      ${b3.bang.map(x => {
        const ok = x.pct_qua_10 < 0.05, vua = x.pct_qua_10 < 0.20;
        return `<tr><td class="sym">${(x.nav / 1e9).toFixed(0)} tỷ</td>
          <td style="text-align:right">${(x.lenh / 1e9).toFixed(1)} tỷ</td>
          <td style="text-align:right">${(x.ty_tb * 100).toFixed(1)}%</td>
          <td style="text-align:right">${(x.pct_qua_10 * 100).toFixed(0)}%</td>
          <td style="color:var(${ok ? '--good' : vua ? '--warn' : '--critical'})">${
            ok ? 'Chạy được' : vua ? 'Bắt đầu chật' : 'Không chạy được'}</td></tr>`;
      }).join('')}
    </tbody></table></div>
    <div class="note warn" style="margin-top:10px"><b>Trần thực tế khoảng 20–30 tỷ NAV.</b>
    Từ 50 tỷ trở lên, một phần ba số lệnh đã vượt 10% GTGD phiên — tức chính lệnh của anh
    đẩy giá lên trước khi mua xong. Con số CAGR trên trang này <b>không áp dụng được</b> cho quy mô đó.</div>`;
  })()}

  <h2>Những gì bộ kiểm định này KHÔNG chứng minh</h2>
  <div class="note warn">
    <p style="margin:0 0 8px"><b>Nó không chứng minh hệ thống sẽ lãi.</b> Nó chỉ chứng minh hệ thống
    chưa bị bắt lỗi bởi tám phép thử này. Đó là hai chuyện khác nhau.</p>
    <p style="margin:0 0 8px"><b>Walk-forward ở đây chỉ chọn trong lưới nhỏ.</b> Một quy trình tối ưu thật
    sẽ quét rộng hơn nhiều, và kết quả có thể xấu đi.</p>
    <p style="margin:0 0 8px"><b>Toàn bộ dữ liệu là 2019 → nay.</b> Chưa có một chu kỳ giảm dài nào
    kiểu 2008 hay 2011 trong mẫu. Hệ thống chưa từng bị thử ở đó.</p>
    <p style="margin:0"><b>Trượt giá vẫn là mô hình, không phải sổ khớp lệnh thật.</b> Con số thật
    chỉ có sau khi <b>Danh mục hệ thống</b> chạy đủ vài chục lệnh về phía trước.</p>
  </div>`;

  veSweep();
  veMC();

  /* --- biểu đồ độ nhạy: mỗi tham số một dải cột, cột đang dùng tô đậm --- */
  function veSweep() {
    const host = document.getElementById('kdSweep');
    host.innerHTML = V.perturb.map(p => {
      const pfs = p.rows.map(r => r.m.pf || 0);
      const hi = Math.max(...pfs, 1e-9);
      return `<div class="card" style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px">
          <h3 style="margin:0">${p.ten}</h3>
          <div class="${p.dinh_sac ? 'kdno' : 'kdok'}" style="font-size:12px">
            ${p.dinh_sac ? 'ĐỈNH SẮC — nghi overfit' : 'VÙNG PHẲNG — ổn'}
            <span class="muted">· độ dao động PF ${p.cv == null ? '—' : (p.cv * 100).toFixed(0) + '%'}</span></div>
        </div>
        <div class="kdbars">${p.rows.map(r => {
          const h = Math.max(3, (r.m.pf || 0) / hi * 100);
          return `<div class="kdb ${r.la_prod ? 'now' : ''}" title="PF ${r.m.pf} · lợi nhuận ${sg(r.m.total_return)} · sụt −${(r.m.maxdd * 100).toFixed(1)}% · ${r.m.trades} lệnh">
            <div class="kdbv">${r.m.pf ?? '—'}</div>
            <div class="kdbc" style="height:${h}%"></div>
            <div class="kdbl">${typeof r.v === 'number' && r.v < 1 ? (r.v * 100).toFixed(0) + '%' : r.v}</div>
          </div>`;
        }).join('')}</div>
        <div class="muted" style="font-size:12px;margin-top:6px">Cột sáng = giá trị đang chạy thật.
        Chiều cao = Profit Factor. Di chuột vào cột để xem đủ số.</div>
      </div>`;
    }).join('');
  }

  /* --- histogram phân bố mức sụt Monte Carlo --- */
  function veMC() {
    const h = V.monte_carlo.hist_dd, e = V.monte_carlo.hist_dd_edges;
    const hi = Math.max(...h, 1);
    const W = 900, H = 190, pad = 34, bw = (W - pad * 2) / h.length;
    const p95 = V.monte_carlo.dd.p95, lo = e[0], hiE = e[e.length - 1];
    const x95 = pad + (p95 - lo) / (hiE - lo) * (W - pad * 2);
    const xBT = pad + (P.maxdd - lo) / (hiE - lo) * (W - pad * 2);
    document.getElementById('kdMC').innerHTML = `
      <svg viewBox="0 0 ${W} ${H + 26}" style="width:100%">
        ${h.map((v, i) => `<rect x="${pad + i * bw + 1}" y="${H - v / hi * (H - 20)}"
          width="${bw - 2}" height="${v / hi * (H - 20)}" rx="2"
          fill="var(--s1)" opacity="${e[i] > p95 ? .95 : .55}"><title>sụt ${(e[i]*100).toFixed(0)}–${(e[i+1]*100).toFixed(0)}% · ${v} kịch bản</title></rect>`).join('')}
        <line x1="${xBT}" y1="6" x2="${xBT}" y2="${H}" stroke="var(--good)" stroke-width="2"/>
        <text x="${xBT + 5}" y="16" fill="var(--good)" font-size="11" font-weight="700">backtest −${(P.maxdd*100).toFixed(1)}%</text>
        <line x1="${x95}" y1="6" x2="${x95}" y2="${H}" stroke="var(--critical)" stroke-width="2" stroke-dasharray="4 3"/>
        <text x="${x95 + 5}" y="32" fill="var(--critical)" font-size="11" font-weight="700">p95 −${(p95*100).toFixed(1)}%</text>
        <line x1="${pad}" y1="${H}" x2="${W - pad}" y2="${H}" stroke="var(--line)"/>
        ${[0, .25, .5, .75, 1].map(f => {
          const x = pad + f * (W - pad * 2), val = lo + f * (hiE - lo);
          return `<text x="${x}" y="${H + 18}" fill="var(--text-muted)" font-size="11" text-anchor="middle">−${(val*100).toFixed(0)}%</text>`;
        }).join('')}
      </svg>`;
  }
}
