/* ============================================================================
   KIẾN TRÚC THÔNG TIN HƯỚNG KHÁCH HÀNG

   Bản cũ tổ chức theo "hệ thống có những module gì": Hiệu suất · Chuông báo ·
   Danh mục · Watchlist · Bộ lọc · Lịch sử lệnh · Chi tiết mã · Kiểm định, cộng
   sáu trang nội bộ nữa. Cách đó cho khách thấy hệ thống phức tạp đến mức nào,
   nhưng bắt họ ghép ba trang mới ra được một kết luận.

   Bản này tổ chức theo "khách mở web lên muốn biết gì", đúng năm câu hỏi:

     1. Hôm nay thị trường thế nào?        -> Hôm nay
     2. Có mã nào đáng mua?                -> Hôm nay + Cơ hội
     3. Tại sao mã này được chọn?          -> Tra cứu mã
     4. Mua rồi thì làm gì tiếp?           -> Danh mục
     5. Hệ thống có đáng tin không?        -> Hiệu quả & Phương pháp

   Thứ tự bắt buộc: HÀNH ĐỘNG -> LÝ DO -> DỮ LIỆU -> PHƯƠNG PHÁP -> BẰNG CHỨNG.
   Không phải phương pháp -> chín lớp -> bằng chứng -> cuối cùng mới biết mua gì.

   KHÔNG XOÁ GÌ CẢ. Toàn bộ trang nghiên cứu vẫn còn nguyên, vẫn vào được bằng
   đường dẫn #tên-trang, và có lối vào gọn ở cuối trang Hiệu quả. Chỉ là chúng
   không còn chiếm chỗ trên thanh điều hướng của khách.
   ========================================================================== */

/* ---------------------------------------------------------------------------
   DỊCH LUẬT THOÁT THÀNH MỘT VIỆC PHẢI LÀM

   Khách không cần nhớ "Lớp 8 luật số 4". Họ cần biết: giữ, theo dõi, hạ, hay ra.
   Hàm này đọc lãi/lỗ, số phiên đã giữ và đỉnh lãi rồi trả về đúng một việc.

   Giới hạn phải nói thẳng: ở đây KHÔNG có MA10/MA30 (muốn có phải tải nến từng
   mã, quá nặng cho trang chủ). Nên hai luật trailing chỉ được CẢNH BÁO SỚM khi
   đỉnh lãi đã vượt ngưỡng, chứ trang không tự khẳng định đã thủng MA. Con số
   chốt vẫn là của bộ máy chạy tối 19h30.
--------------------------------------------------------------------------- */
function vieccanlam(p) {
  const l = p.pnl, giu = p.held, dinh = p.peak;
  if (l == null) return { m: 'cho', t: 'CHƯA CÓ GIÁ', v: 'Chờ dữ liệu', ly: '' };

  if (l <= -10) return { m: 'thoat', t: 'THOÁT', v: 'Bán toàn bộ',
    ly: `Lỗ ${l.toFixed(1)}% — đã chạm cắt lỗ cứng −10%.` };
  if (giu != null && giu >= 3 && l <= -7) return { m: 'thoat', t: 'THOÁT', v: 'Bán toàn bộ',
    ly: `Lỗ ${l.toFixed(1)}% sau ${giu} phiên — đã chạm cắt lỗ −7%.` };
  if (dinh != null && dinh >= 8 && l <= 1) return { m: 'thoat', t: 'THOÁT', v: 'Bán toàn bộ',
    ly: `Từng lãi ${dinh.toFixed(1)}% rồi rơi về ${l.toFixed(1)}% — luật về bờ.` };
  if (giu != null && giu >= 4 && l <= 0) return { m: 'thoat', t: 'THOÁT', v: 'Bán toàn bộ',
    ly: `Giữ ${giu} phiên vẫn chưa có lãi — van thời gian T+4. Giả thuyết đã sai, trả vốn về.` };

  if (l <= -5) return { m: 'ha', t: 'GẦN CẮT LỖ', v: 'Theo dõi sát',
    ly: `Lỗ ${l.toFixed(1)}% — còn ${(l + 7).toFixed(1)} điểm nữa là chạm cắt lỗ −7%.` };
  if (giu != null && giu >= 2 && l <= 2) return { m: 'ha', t: 'SẮP HẾT GIỜ', v: 'Chuẩn bị ra',
    ly: `Giữ ${giu} phiên mới lãi ${l.toFixed(1)}% — còn ${4 - giu} phiên tới van T+4.` };
  if (dinh != null && dinh >= 19) return { m: 'theo', t: 'BÁM MA10', v: 'Giữ, theo MA10',
    ly: `Đỉnh lãi ${dinh.toFixed(1)}% đã vượt 19% — hệ chuyển sang bám MA10, chốt nhanh hơn.` };
  if (dinh != null && dinh >= 8 && l < dinh - 6) return { m: 'theo', t: 'ĐANG TRẢ LẠI LÃI', v: 'Theo dõi',
    ly: `Đỉnh ${dinh.toFixed(1)}%, giờ ${l.toFixed(1)}% — đã trả lại ${(dinh - l).toFixed(1)} điểm.` };

  return { m: 'giu', t: 'BÌNH THƯỜNG', v: 'Giữ',
    ly: l >= 0 ? `Đang lãi ${l.toFixed(1)}%, chưa chạm luật thoát nào.`
              : `Lỗ nhẹ ${l.toFixed(1)}%, còn xa mọi ngưỡng.` };
}

const VCLMAU = { thoat: '--critical', ha: '--serious', theo: '--warn', giu: '--good', cho: '--text-muted' };

/* ---------------------------------------------------------------------------
   1. HÔM NAY — trang chủ. Mười giây phải hiểu hôm nay cần làm gì.
--------------------------------------------------------------------------- */
function pageHomNay(root) {
  const L = (typeof LIVE !== 'undefined' && LIVE.data) ? LIVE.data : (D.live || { hits: [] });
  const last = D.regime[D.regime.length - 1];
  const den = last.light;
  const smul = { XANH: 1.0, VANG: 0.6, CAM: 0.35, DO: 0.2 }[den];
  const NOI = { XANH: 'Được đánh mạnh', VANG: 'Ưu tiên thận trọng', CAM: 'Hạ tỷ trọng', DO: 'Gần như đứng ngoài' };
  const GIAI = {
    XANH: 'Thị trường chung đang khoẻ: chỉ số trên MA200, VN-Index trên MA50, ít ngày phân phối.',
    VANG: 'Có dấu hiệu yếu — VN-Index dưới MA50 hoặc đã có 3–4 ngày phân phối. Vẫn mua được nhưng nhỏ hơn.',
    CAM: 'Từ 5 ngày phân phối trở lên — tiền lớn đang rút. Chỉ vào lệnh thật đẹp, và nhỏ.',
    DO: 'Chỉ số thủng MA200 và chưa có phiên bùng nổ xác nhận. Hệ chỉ thăm dò để không mất dấu thị trường.',
  };

  const mua = L.hits.filter(h => h.level === 'MUA');
  const sap = L.hits.filter(h => h.level === 'SAP_DU');
  const dem = L.hits.filter(h => h.level === 'DE_MAT' || h.level === 'THEO_DOI');

  const dm = (typeof danhMuc === 'function' ? danhMuc() : []).map(p => ({ ...p, vcl: vieccanlam(p) }));
  const canchuy = dm.filter(p => p.vcl.m === 'thoat' || p.vcl.m === 'ha' || p.vcl.m === 'theo');

  const the = h => `
    <a class="ccard ${h.level === 'MUA' ? 'mua' : h.level === 'SAP_DU' ? 'sap' : ''}"
       href="#bieudo" onclick="_chartSym='${esc(h.sym)}'">
      <div class="cctop">
        <div><b class="ccsym">${esc(h.sym)}</b>
          <span class="muted">${esc((h.name || '').slice(0, 28))}</span></div>
        <span class="ccbadge">${h.level === 'MUA' ? '🟢 ĐỦ ĐIỂM MUA'
          : h.level === 'SAP_DU' ? '🟠 SẮP ĐỦ' : '🟡 THEO DÕI'}</span>
      </div>
      <div class="ccgia">${h.price} <span class="${h.pct >= 0 ? 'pos' : 'neg'}">${h.pct >= 0 ? '+' : ''}${h.pct}%</span></div>
      <div class="cclydo">${lydongan(h)}</div>
      ${h.level === 'MUA' ? `<div class="ccact">Cỡ đề xuất <b>${(42 * smul).toFixed(0)}% NAV</b> · vào lệnh trong chính phiên này</div>` : ''}
      ${h.miss && h.miss.length ? `<div class="ccthieu">Còn thiếu: ${h.miss.map(esc).join(' · ')}</div>` : ''}
    </a>`;

  root.innerHTML = `
  ${typeof bangSoLieuCu === 'function' ? bangSoLieuCu() : ''}

  <div class="denhero ${den}">
    <div>
      <div class="denlab">THỊ TRƯỜNG HÔM NAY</div>
      <div class="denten">${{ XANH: '🟢 XANH', VANG: '🟡 VÀNG', CAM: '🟠 CAM', DO: '🔴 ĐỎ' }[den]}</div>
      <div class="dennoi">${NOI[den]} · dùng tối đa <b>${(42 * smul).toFixed(0)}% NAV</b> mỗi lệnh</div>
    </div>
    <p class="dengiai">${GIAI[den]}</p>
  </div>

  <h2>Cơ hội hôm nay</h2>
  ${mua.length || sap.length ? `<div class="cgrid">
      ${mua.map(the).join('')}${sap.map(the).join('')}
    </div>` : `
    <div class="note"><b>Chưa có mã nào đủ hay sắp đủ điểm mua.</b>
    Đây là chuyện bình thường — hệ chỉ sinh khoảng ${(D.prod.metrics.per_year || 19).toFixed(0)} tín hiệu mỗi năm,
    trung bình một tín hiệu mỗi 11 phiên. Phần lớn thời gian nó được thiết kế để đứng yên.</div>`}
  ${dem.length ? `<p class="muted" style="margin-top:12px">Đang động đậy, chưa phải lệnh:
    ${dem.slice(0, 10).map(h => `<b>${esc(h.sym)}</b> ${h.pct >= 0 ? '+' : ''}${h.pct}%`).join(' · ')}
    — <a href="#cohoi">xem tất cả</a></p>` : ''}

  <h2>Đang cần chú ý</h2>
  ${!dm.length ? '<div class="note">Hệ thống chưa cầm mã nào.</div>'
   : !canchuy.length ? `<div class="note"><b>Không có gì phải làm.</b>
      ${dm.length} mã đang cầm đều bình thường, chưa mã nào chạm ngưỡng thoát.
      <a href="#danhmuc">Xem danh mục</a></div>`
   : `<div class="cgrid">${canchuy.map(p => `
      <a class="ccard vcl-${p.vcl.m}" href="#danhmuc">
        <div class="cctop">
          <div><b class="ccsym">${esc(p.sym)}</b> <span class="muted">${esc((p.name || '').slice(0, 26))}</span></div>
          <span class="ccbadge" style="color:var(${VCLMAU[p.vcl.m]})">${p.vcl.t}</span>
        </div>
        <div class="ccgia">${p.last != null ? (+p.last).toFixed(2) : '—'}
          <span class="${p.pnl >= 0 ? 'pos' : 'neg'}">${p.pnl >= 0 ? '+' : ''}${(p.pnl || 0).toFixed(1)}%</span></div>
        <div class="cclydo">${p.vcl.ly}</div>
        <div class="ccact">Việc cần làm: <b>${p.vcl.v}</b></div>
      </a>`).join('')}</div>`}

  <div class="note info" style="margin-top:22px"><b>Cách đọc trang này.</b>
  Giá và biểu đồ tự lấy mới trong phiên. Ngưỡng, điểm số và watchlist là ảnh chụp
  do dây chuyền chạy lúc 19h30 mỗi tối. Muốn biết vì sao một mã được chọn thì bấm
  vào nó — trang <b>Tra cứu mã</b> sẽ liệt kê đủ điều kiện nào đạt, điều kiện nào chưa.</div>`;
}

/* một câu lý do ngắn, rút từ chính bốn điều kiện — không bắt khách đọc bảng 8 dòng */
function lydongan(h) {
  const o = [];
  if (h.base != null && h.base <= 18) o.push(`nền chặt ${h.base}%`);
  if (h.volr >= 2) o.push(`vol ${h.volr}× TB20`);
  else if (h.volr >= 1.3) o.push(`vol nhích ${h.volr}×`);
  if (h.gtgd >= 15) o.push(`GTGD ${h.gtgd} tỷ`);
  if (h.ordimb != null && h.ordimb >= (h.ordimb_min || 1.2)) o.push('dòng tiền mua mạnh');
  if (h.score != null) o.push(`điểm ${Math.round(h.score)}`);
  return o.slice(0, 4).join(' · ') || '—';
}

/* ---------------------------------------------------------------------------
   2. CƠ HỘI — một danh sách, ba bộ lọc. Gộp Watchlist + Bộ lọc lại.
--------------------------------------------------------------------------- */
function pageCoHoi(root) {
  const L = (typeof LIVE !== 'undefined' && LIVE.data) ? LIVE.data : (D.live || { hits: [] });
  const Lk = D.lookup || {};
  // gộp: mã có tín hiệu hôm nay + mã đang chờ điểm mua trong bảng tra cứu
  const m = {};
  (L.hits || []).forEach(h => { m[h.sym] = { ...h }; });
  Object.entries(Lk).forEach(([s, x]) => {
    if (x.state !== 'cho' && x.state !== 'fa') return;
    if (m[s]) return;
    m[s] = { sym: s, name: x.name, level: 'CHO', price: x.price, pct: 0, score: x.score,
             base: x.base, need_px: x.need_px, need_vol: x.need_vol, miss: x.miss || [],
             fa: x.state === 'fa' };
  });
  const ds = Object.values(m);
  const bac = { MUA: 0, SAP_DU: 1, DE_MAT: 2, THEO_DOI: 3, CHO: 4 };
  ds.sort((a, b) => bac[a.level] - bac[b.level] || (b.score || 0) - (a.score || 0));

  root.innerHTML = `
  <h1>Cơ hội</h1>
  <p class="lead">Mọi mã hệ thống đang để mắt, xếp theo mức độ sẵn sàng. Bấm vào một mã
  để xem đủ lý do nó được chọn và điều kiện nào còn thiếu.</p>
  <div class="seg" id="chLoc" style="margin-bottom:14px">
    <button data-f="all" class="on">Tất cả <span class="muted">${ds.length}</span></button>
    <button data-f="MUA">🟢 Đủ điểm <span class="muted">${ds.filter(x => x.level === 'MUA').length}</span></button>
    <button data-f="SAP_DU">🟠 Sắp đủ <span class="muted">${ds.filter(x => x.level === 'SAP_DU').length}</span></button>
    <button data-f="CHO">🟡 Chờ điểm mua <span class="muted">${ds.filter(x => x.level === 'CHO' || x.level === 'DE_MAT' || x.level === 'THEO_DOI').length}</span></button>
  </div>
  <div id="chDs" class="cgrid"></div>`;

  const ve = f => {
    const l = f === 'all' ? ds
      : f === 'CHO' ? ds.filter(x => ['CHO', 'DE_MAT', 'THEO_DOI'].includes(x.level))
      : ds.filter(x => x.level === f);
    document.getElementById('chDs').innerHTML = !l.length
      ? '<div class="note">Không có mã nào ở nhóm này.</div>'
      : l.map(h => `
      <a class="ccard ${h.level === 'MUA' ? 'mua' : h.level === 'SAP_DU' ? 'sap' : ''}"
         href="#bieudo" onclick="_chartSym='${esc(h.sym)}'">
        <div class="cctop">
          <div><b class="ccsym">${esc(h.sym)}</b>
            <span class="muted">${esc((h.name || '').slice(0, 30))}</span></div>
          <span class="ccbadge">${{ MUA: '🟢 ĐỦ ĐIỂM MUA', SAP_DU: '🟠 SẮP ĐỦ',
            DE_MAT: '🟡 ĐANG TĂNG', THEO_DOI: '🟡 ĐỘNG ĐẬY', CHO: '⏳ CHỜ ĐIỂM MUA' }[h.level]}</span>
        </div>
        <div class="ccgia">${h.price != null ? h.price : '—'}
          ${h.pct ? `<span class="${h.pct >= 0 ? 'pos' : 'neg'}">${h.pct >= 0 ? '+' : ''}${h.pct}%</span>` : ''}</div>
        <div class="cclydo">${lydongan(h)}</div>
        ${h.fa ? '<div class="ccthieu"><b style="color:var(--warn)">Chưa đạt về cơ bản — hệ không mua</b></div>' : ''}
        ${h.need_px ? `<div class="ccact">Cần đóng cửa ≥ <b>${h.need_px}</b>${
          h.need_vol ? ` · KL ≥ <b>${(h.need_vol / 1e6).toFixed(1)} triệu</b>` : ''}</div>` : ''}
        ${h.miss && h.miss.length ? `<div class="ccthieu">Còn thiếu: ${h.miss.slice(0, 3).map(esc).join(' · ')}</div>` : ''}
      </a>`).join('');
  };
  ve('all');
  root.querySelectorAll('#chLoc button').forEach(b => b.onclick = () => {
    root.querySelectorAll('#chLoc button').forEach(z => z.classList.toggle('on', z === b));
    ve(b.dataset.f);
  });
}

/* ---------------------------------------------------------------------------
   5. HIỆU QUẢ & PHƯƠNG PHÁP — số đầu tiên, phương pháp mở ra khi hỏi.
--------------------------------------------------------------------------- */
function pageHieuQua(root) {
  const M = D.prod.metrics, BM = D.bench_metrics;
  const nam = (D.prod.curve.length / 250);
  const sg2 = v => (v >= 0 ? '+' : '−') + Math.abs(v * 100).toFixed(1) + '%';

  root.innerHTML = `
  ${typeof bangSoLieuCu === 'function' ? bangSoLieuCu() : ''}
  <div class="hero">
    <div class="badge">Kiểm nghiệm ${nam.toFixed(1)} năm · ${D.prod.curve.length} phiên · chốt ${D.asof}</div>
    <h1>Hệ thống này có đáng tin không?</h1>
    <p class="lead">Sáu con số dưới đây là toàn bộ câu trả lời ngắn. Chúng đến từ backtest
    chạy lại từng phiên một từ 02/01/2019, đã trừ phí <b>0,15% mua · 0,25% bán</b>,
    và không dùng thông tin nào của tương lai.</p>
  </div>

  <div class="tthai">
    <b>TRẠNG THÁI: NGHIÊN CỨU — CHƯA CHẠY TIỀN THẬT.</b>
    Đây là kết quả mô phỏng. Nó chưa được kiểm chứng bằng lệnh thật, và có ba nhóm
    câu hỏi lớn chưa trả lời được: dữ liệu có đúng point-in-time không, lệnh cận trần
    có khớp được thật không, và edge có sống qua nhiều chế độ thị trường khác nhau không.
    <a href="#kiemdinh">Xem bộ kiểm định →</a>
  </div>

  <div class="grid kpis" style="margin-top:18px">
    ${kpi('Lợi nhuận mỗi năm', sg2(M.cagr), `VN-Index cùng kỳ ${sg2(BM.cagr)}`, 'pos')}
    ${kpi('Sụt giảm tối đa', '−' + (M.maxdd * 100).toFixed(1) + '%', `VN-Index −${(BM.mdd * 100).toFixed(1)}%`, 'neg')}
    ${kpi('Tỷ lệ thắng', (M.winrate * 100).toFixed(0) + '%', 'thắng ít nhưng thắng đậm')}
    ${kpi('Lãi/lỗ mỗi lệnh', M.rr + '×', `thắng TB +${M.avg_win}% · thua TB ${M.avg_loss}%`)}
    ${kpi('Số lệnh', M.trades, `${M.per_year}/năm · khoảng 1 lệnh mỗi 11 phiên`)}
    ${kpi('Số năm kiểm nghiệm', nam.toFixed(1), 'chưa qua chu kỳ giảm dài kiểu 2008')}
  </div>

  <div class="note" style="margin-top:16px"><b>Đọc con số tỷ lệ thắng cho đúng.</b>
  Thắng chỉ ${(M.winrate * 100).toFixed(0)}% nghe như dở, nhưng mỗi lần thắng ăn
  <b>${M.rr} lần</b> mỗi lần thua. Tiền đến từ biên độ chứ không từ tần suất — và điều đó
  có nghĩa anh phải chịu được những chuỗi thua dài. Mô phỏng cho thấy chuỗi
  <b>15 lệnh thua liên tiếp</b> là chuyện bình thường về xác suất.</div>

  <h2>Phương pháp — mở ra khi anh muốn biết vì sao</h2>
  <p class="lead">Hệ thống không đoán thị trường. Nó chờ đúng một loại phiên:
  <b>phiên tiền lớn nhảy vào một cổ phiếu đã tích luỹ yên tĩnh</b>. Sai thì cắt trong
  3–4%, đúng thì gồng tới cùng.</p>

  <details class="dt"><summary><b>Hệ thống chọn mã thế nào</b> — chín lớp lọc, trượt lớp nào là dừng</summary>
    <div class="dtin">
      <ol class="dtol">
        <li><b>Vũ trụ</b> — chỉ TOP 110 mã thanh khoản nhất, xếp hạng lại từng phiên.</li>
        <li><b>Cổng rủi ro</b> — dòng tiền âm, không đủ trả lãi vay, nợ quá cao thì loại thẳng.</li>
        <li><b>Chấm điểm</b> — tăng trưởng lợi nhuận, doanh thu, ROE, sức mạnh giá. Sàn 45/100.</li>
        <li><b>Nền giá</b> — 30 phiên gần nhất phải tích luỹ trong biên độ hẹp.</li>
        <li><b>Điểm mua</b> — đủ cả 8 điều kiện trong <i>cùng một phiên</i>.</li>
        <li><b>Đèn thị trường</b> — bối cảnh chung quyết định đánh mạnh cỡ nào.</li>
        <li><b>Lọc ngành</b> — không dồn quá 30% NAV vào một nhóm ngành.</li>
        <li><b>Cỡ vị thế</b> — 42% NAV × hệ số đèn × hệ số rủi ro.</li>
        <li><b>Bộ thoát</b> — bảy luật, kiểm theo thứ tự mỗi phiên.</li>
      </ol>
      <p class="muted">Chi tiết đầy đủ từng lớp: <a href="#hethong">Hệ thống 9 lớp →</a></p>
    </div></details>

  <details class="dt"><summary><b>Khi nào hệ thống bán</b> — bảy cửa ra, và cửa nào thực sự hay dùng</summary>
    <div class="dtin">
      <div class="tblwrap"><table><thead><tr><th>Cửa ra</th>
        <th style="text-align:right">Số lệnh</th><th style="text-align:right">Lãi/lỗ trung vị</th></tr></thead><tbody>
        ${(D.prod.doors || []).map(d => `<tr><td>${esc(d.door)}</td>
          <td style="text-align:right">${d.n} <span class="muted">(${d.pct}%)</span></td>
          <td style="text-align:right" class="${d.median >= 0 ? 'pos' : 'neg'}">${d.median >= 0 ? '+' : ''}${d.median}%</td></tr>`).join('')}
      </tbody></table></div>
      <p class="muted">Đọc bảng này là hiểu cả hệ: van thời gian là cửa dùng nhiều nhất và
      nó chỉ mất vài phần trăm — đó là cơ chế giữ lỗ nhỏ. Tiền đến gần như trọn vẹn từ
      nhóm thoát bằng trailing khi đã lãi lớn.</p>
    </div></details>

  <details class="dt"><summary><b>Kết quả từng năm</b> — kể cả những năm hệ thống thua chỉ số</summary>
    <div class="dtin"><div class="tblwrap"><table><thead><tr><th>Năm</th>
      <th style="text-align:right">Hệ thống</th><th style="text-align:right">VN-Index</th>
      <th style="text-align:right">Chênh lệch</th></tr></thead><tbody>
      ${Object.keys(D.prod.yearly).map(y => {
        const a = D.prod.yearly[y], b = (D.bench_yearly || {})[y];
        return `<tr><td class="sym">${y}</td>
          <td style="text-align:right" class="${a >= 0 ? 'pos' : 'neg'}">${sg2(a)}</td>
          <td style="text-align:right" class="${b >= 0 ? 'pos' : 'neg'}">${b == null ? '—' : sg2(b)}</td>
          <td style="text-align:right">${b == null ? '—' : ((a - b) * 100).toFixed(1) + ' điểm'}</td></tr>`;
      }).join('')}
    </tbody></table></div>
    <p class="muted">Có năm hệ thống thua chỉ số rõ rệt. Đó là bản chất của hệ bắt sóng lớn:
    thị trường đi lên đều đặn, ít cây trần, cổ phiếu không tạo được nền chặt thì hệ đứng nhìn.</p>
    </div></details>

  <h2>Kiểm định nâng cao</h2>
  <p class="muted" style="margin-top:0">Phần dành cho người muốn tự bắt lỗi hệ thống.
  Khách bình thường không cần xem mỗi ngày.</p>
  <div class="lktrong">
    <a href="#kiemdinh"><b>Bộ kiểm định 8 bài</b><span>Walk-forward · Monte Carlo · trượt giá · bỏ deal lãi nhất · kiểm nhìn trước</span></a>
    <a href="#backtest"><b>Backtest chi tiết</b><span>Đường vốn, phân bố lệnh, các cấu hình đã thử</span></a>
    <a href="#bangchung"><b>Bằng chứng A/B</b><span>Từng luật bật/tắt riêng, kèm kết quả</span></a>
    <a href="#hethong"><b>Hệ thống 9 lớp</b><span>Toàn văn từng lớp và từng ngưỡng</span></a>
    <a href="#dongtien"><b>Dòng tiền lớn</b><span>Thước đo cỡ lệnh mua so cỡ lệnh bán</span></a>
    <a href="#tongquan"><b>Tổng quan chi tiết</b><span>Bản đầy đủ của trang này</span></a>
    <a href="#lenh"><b>Lịch sử lệnh</b><span>Toàn bộ ${M.trades} lệnh, lọc và sắp xếp được</span></a>
    <a href="#boloc"><b>Bộ lọc toàn thị trường</b><span>Điểm số của cả ${D.universe_n} mã</span></a>
  </div>

  <div class="note warn" style="margin-top:20px"><b>Đây là kết quả mô phỏng của một hệ thống cơ học,
  không phải khuyến nghị đầu tư.</b> Quá khứ không đảm bảo tương lai, và con số trên trang này
  chưa nên dùng làm cơ sở phân bổ vốn lớn.</div>`;
}
