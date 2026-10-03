
/* ==========================================================================
   p20 — LOI LE DE HIEU CHO KHACH (anh Son yeu cau 03/10/2026)
   Doi thuat ngu noi bo (Cond9/OrdImb/CANSLIM/NAV/MA10/T+3/S1/PF...) sang tieng
   Viet doi thuong TREN CAC TRANG KHACH. Chi doi CHU HIEN THI (text node + title),
   khong dong vao du lieu, ma tinh toan hay luat giao dich.
   Cac trang an (Kiem dinh, Backtest, So tay, Chan doan...) GIU nguyen thuat ngu.
   Muon them/sua mot cum tu: sua bang DICH ben duoi (cum dai dat TRUOC cum ngan).
   ========================================================================== */
const DICH = [
  // ---- Dieu kien 9 (co lenh mua so co lenh ban) ----
  [/Cond9 không xác nhận — bán lệnh thăm dò/g, 'Lệnh mua không lớn hơn lệnh bán — bán lệnh mua thử'],
  [/tối ĐK9 = ([\d.,]+) < ([\d.,]+): không xác nhận, bán ATC T\+(\d)/g,
   'tối hôm đó lệnh mua chỉ gấp $1 lần lệnh bán (cần ≥ $2): không đạt, bán ATC phiên thứ $3 sau ngày mua'],
  [/Điều kiện 9 = ([\d.,]+) < ([\d.,]+)/g, 'lệnh mua chỉ gấp $1 lần lệnh bán, cần ≥ $2'],
  [/Điều kiện 9 — cỡ lệnh mua so cỡ lệnh bán/g, 'điều kiện "lệnh mua lớn hơn lệnh bán"'],
  [/Điều kiện 9 \(dòng tiền\)/g, 'Lệnh mua lớn hơn lệnh bán'],
  [/OrdImb ([\d.,]+) ≥ ([\d.,]+)/g, 'lệnh mua gấp $1 lần lệnh bán (cần ≥ $2)'],
  [/OrdImb ([\d.,]+) < ([\d.,]+)/g, 'lệnh mua chỉ gấp $1 lần lệnh bán (cần ≥ $2)'],
  [/OrdImb ([\d.,]+)/g, 'lệnh mua gấp $1 lần lệnh bán'],
  [/Cond9: ❌ \(kể cả đủ cổng cũng chỉ là lệnh dò, bán T\+3\)/g,
   'Lệnh mua lớn hơn lệnh bán: ❌ (dù đủ các điều kiện khác cũng chỉ mua thử, bán ở phiên thứ 3)'],
  [/XÁC NHẬN ĐK9/g, 'XÁC NHẬN LỆNH MUA LỚN HƠN LỆNH BÁN'],
  [/ĐK9 TỐI NGÀY MUA/g, 'MUA > BÁN TỐI NGÀY MUA'],
  [/(?:Cond9|ĐK9|DK9|Điều kiện 9|OrdImb)/g, 'Lệnh mua lớn hơn lệnh bán'],
  // ---- mua do / lenh tham do ----
  [/MUA DÒ/g, 'MUA THỬ'], [/Mua dò/g, 'Mua thử'], [/mua dò/g, 'mua thử'],
  [/lệnh thăm dò/g, 'lệnh mua thử'], [/Lệnh thăm dò/g, 'Lệnh mua thử'],
  [/lệnh dò/g, 'lệnh mua thử'], [/Lệnh dò/g, 'Lệnh mua thử'], [/thăm dò/g, 'mua thử'],
  // ---- ly do ban (cua ra) ----
  [/Momentum: không chạy \(T\+3 chưa lên 1%\)/g, 'Không chạy: sau 3 phiên chưa từng lãi 1%'],
  [/Van thời gian T\+(\d)/g, 'Hết thời gian chờ: sau $1 phiên vẫn chưa lãi'],
  [/van thời gian/g, 'hết thời gian chờ'],
  [/Khoá lãi S1 \(đỉnh ≥(\d+)% → sàn \+(\d+)%\)/g, 'Khoá lãi (từng lãi ≥$1% → bán khi lãi lùi về +$2%)'],
  [/Trailing MA(\d+) \(lãi lớn\)/g, 'Chốt lời: giá gãy đường trung bình $1 phiên'],
  [/Trailing MA(\d+)/g, 'Giá gãy đường trung bình $1 phiên'],
  [/Đèn Cam — hạ 1\/3/g, 'Thị trường xấu đi — bán bớt 1/3'],
  [/Khoá lãi S1/g, 'Khoá lãi'], [/\bS1\b/g, 'khoá lãi'],
  [/Momentum 3 tháng/g, 'Đà tăng 3 tháng'], [/Momentum/g, 'Đà tăng'], [/momentum/g, 'đà tăng'],
  // ---- diem CANSLIM ----
  [/CHẤM ĐIỂM CANSLIM/g, 'CHẤM ĐIỂM CHẤT LƯỢNG'], [/Điểm CANSLIM tổng/g, 'Điểm chất lượng tổng'],
  [/Điểm CANSLIM/g, 'Điểm chất lượng'], [/CANSLIM đạt sàn/g, 'Điểm chất lượng đạt mức tối thiểu'],
  [/CANSLIM/g, 'Điểm chất lượng'],
  [/dòng "C — LNST quý YoY"/g, 'dòng "Lợi nhuận quý so cùng kỳ"'],
  [/^C — LNST quý YoY/g, 'Lợi nhuận quý so cùng kỳ'], [/^C — Doanh thu quý YoY/g, 'Doanh thu quý so cùng kỳ'],
  [/^A — CAGR LNST 3 năm/g, 'Lợi nhuận tăng bình quân 3 năm'], [/^A — ROE/g, 'ROE (lãi trên vốn chủ)'],
  [/^N — /g, ''], [/^S — Volume \/ TB20/g, 'Khối lượng so trung bình 20 phiên'],
  [/^L — RS Rating/g, 'Sức mạnh giá so thị trường'], [/^I — GTGD bình quân 20 phiên/g, 'Giá trị giao dịch trung bình 20 phiên'],
  // ---- von / tai khoan ----
  [/NAV 6 THÁNG/g, 'TÀI KHOẢN 6 THÁNG'], [/trên chuỗi NAV ngày/g, 'trên giá trị tài khoản từng ngày'],
  [/NAV riêng của sổ này/g, 'vốn riêng của sổ này'], [/NAV của sổ/g, 'vốn của sổ'],
  [/NAV hiện tại/g, 'tài khoản hiện tại'], [/% NAV/g, '% tài khoản'], [/\bNAV\b/g, 'giá trị tài khoản'],
  [/Cỡ vị thế/g, 'Cỡ mỗi lệnh'], [/lý thuyết (\d)/g, 'cỡ chuẩn $1'],
  // ---- duong trung binh / thi truong ----
  [/G1 · chỉ số đều trọng số so MA200/g, 'Chỉ số chung (mọi mã tính đều nhau) so với trung bình 200 phiên'],
  [/G2 · VN-Index so MA50/g, 'VN-Index so với trung bình 50 phiên'],
  [/G3 · ngày phân phối/g, 'Số ngày bị bán mạnh'], [/MFE \/ MAE/g, 'Lãi cao nhất / lỗ sâu nhất'],
  [/\bMA(\d+)\b/g, 'trung bình $1 phiên'],
  [/vol\/TB20/gi, 'khối lượng / TB 20 phiên'], [/× TB20/g, '× trung bình 20 phiên'],
  [/Biên độ dao động TB20/g, 'Mức dao động giá trung bình 20 phiên'], [/TB20/g, 'trung bình 20 phiên'],
  [/T\+1 · T\+2 · T\+3 · T\+5/g, 'Sau 1 · 2 · 3 · 5 phiên'],
  [/bán ATC T\+(\d)/g, 'bán ATC phiên thứ $1 sau ngày mua'], [/\bT\+(\d+)\b/g, 'phiên thứ $1 sau ngày mua'],
  // ---- breakout / cong / thanh khoan ----
  [/Số phiên từ breakout/g, 'Số phiên từ ngày bùng nổ'], [/Giữ trên giá breakout/g, 'Giữ trên giá ngày bùng nổ'],
  [/Đỉnh mới sau breakout/g, 'Đỉnh mới sau ngày bùng nổ'], [/sau breakout/g, 'sau ngày bùng nổ'],
  [/Breakout/g, 'Ngày bùng nổ'], [/breakout/g, 'bùng nổ'],
  [/chỉ giao dịch TOP (\d+) mã thanh khoản nhất/g, 'chỉ giao dịch $1 mã có thanh khoản cao nhất'],
  [/Thuộc TOP thanh khoản/g, 'Thuộc nhóm thanh khoản cao'], [/TOP hạng (\d+)/g, 'hạng thanh khoản $1'],
  [/Bảng R29 ở trang Kiểm định đo xem cổng nào hay bỏ sót winner\.?/g, ''],
  [/cổng rủi ro tài chính/gi, 'kiểm tra sức khoẻ tài chính'], [/CỔNG RỦI RO/g, 'SỨC KHOẺ TÀI CHÍNH'],
  [/[Cc]ổng rủi ro/g, m => m[0] === 'C' ? 'Kiểm tra sức khoẻ tài chính' : 'kiểm tra sức khoẻ tài chính'],
  [/CỔNG SÀNG LỌC/g, 'ĐIỀU KIỆN SÀNG LỌC'], [/cổng sàng lọc/g, 'điều kiện sàng lọc'],
  [/(\d)\/8 cổng/gi, '$1/8 điều kiện'], [/thiếu (\d+) cổng/g, 'thiếu $1 điều kiện'],
  [/mọi cổng/g, 'mọi điều kiện'], [/một cổng/g, 'một điều kiện'], [/đủ cổng/g, 'đủ điều kiện'],
  [/cổng nào/g, 'điều kiện nào'], [/cổng dòng tiền/g, 'điều kiện dòng tiền'], [/cổng/gi, 'điều kiện'],
  [/bộ máy chín lớp/g, 'hệ thống'], [/qua đủ chín lớp/g, 'qua đủ mọi điều kiện'], [/chín lớp/g, 'hệ thống'], [/bộ máy/g, 'hệ thống'],
  // ---- tai chinh ----
  [/CFO < 0/g, 'Dòng tiền kinh doanh âm'], [/CFO 12T/g, 'DÒNG TIỀN KD 12 THÁNG'], [/\bCFO\b/g, 'dòng tiền kinh doanh'],
  [/ICR ([\d.,]+) < ([\d.,]+)/g, 'Khả năng trả lãi vay $1 < $2'], [/\bICR\b/g, 'TRẢ LÃI VAY'],
  [/NPL ([\d.,]+%) > ([\d.,]+%)/g, 'Nợ xấu $1 > $2'], [/\bNPL\b/g, 'Nợ xấu'], [/\bCAR\b/g, 'An toàn vốn'],
  [/D\/E/g, 'NỢ/VỐN'],
  [/LNST YoY \(ĐK5\)/g, 'Lợi nhuận so cùng kỳ'], [/\(ĐK5\)/g, ''],
  [/DTHU YOY/g, 'DOANH THU SO CÙNG KỲ'], [/LNST YOY/g, 'LỢI NHUẬN SO CÙNG KỲ'],
  [/%YoY Doanh thu/g, '% Doanh thu so cùng kỳ'], [/%YoY LNST/g, '% Lợi nhuận so cùng kỳ'],
  [/LNST quý YoY/g, 'lợi nhuận quý so cùng kỳ'], [/ YoY/g, ' so cùng kỳ'], [/YoY/g, 'so cùng kỳ'],
  [/LNST \(tỷ đồng\)/g, 'Lợi nhuận sau thuế (tỷ đồng)'], [/\+\/− LNST/g, '+/− Lợi nhuận'],
  [/\bLNST\b/g, 'lợi nhuận sau thuế'],
  [/RS \(sức mạnh giá\)/g, 'Sức mạnh giá'], [/(^|[^A-Za-z])RS(?![A-Za-z])/g, '$1SỨC MẠNH GIÁ'],
  // ---- hieu suat ----
  [/Profit Factor/g, 'Tổng lãi ÷ tổng lỗ'], [/(^|[^A-Za-z])PF(?![A-Za-z])/g, '$1Lãi÷lỗ'],
  [/Sharpe/g, 'Độ ổn định lợi nhuận'], [/[Dd]rawdown/g, 'mức sụt giảm lớn nhất'],
  [/(^|[^A-Za-z])DD(?![A-Za-z])/g, '$1Sụt giảm lớn nhất'], [/CAGR/g, 'Lãi kép mỗi năm'],
  [/(\d) deal mỗi năm/g, '$1 giao dịch mỗi năm'], [/\bdeal\b/g, 'giao dịch'],
  [/[Bb]acktest/g, 'mô phỏng quá khứ'], [/R:R/g, 'Lãi TB ÷ lỗ TB'], [/[Ww]inrate/g, 'Tỷ lệ thắng'],
  // ---- linh tinh ----
  [/Sổ ghi tiến \(portfolio\.json\)/g, 'Sổ giao dịch thực tế'],
  [/\(portfolio\.json — sổ riêng/g, '(sổ riêng'], [/portfolio\.json/g, 'sổ giao dịch thực tế'],
  [/sổ ghi tiến/gi, 'sổ giao dịch thực tế'],
  [/real-time/g, 'trực tiếp'], [/Real-time/g, 'Trực tiếp'],
  [/^\s*Watchlist\s*$/g, 'Theo dõi'], [/Watchlist/g, 'Danh sách theo dõi'], [/WATCHLIST/g, 'DANH SÁCH THEO DÕI'], [/watchlist/g, 'danh sách theo dõi'],
  [/\bvol (\d)/g, 'khối lượng $1'], [/VOL\b/g, 'KHỐI LƯỢNG'], [/\bVolume\b/g, 'Khối lượng'],
  [/GTGD/g, 'GT giao dịch'],
  // cot/loc 'Dong tien' o bang = co lenh mua chia co lenh ban (khong phai dong tien kinh doanh)
  [/^\s*Dòng tiền\s*$/i, 'Mua ÷ bán'], [/^Dòng tiền (≥|≤)/i, 'Mua ÷ bán $1'], [/\bDThu\b/gi, 'Doanh thu'],
];

function dichChu(s) {
  if (!s || !/[A-Za-zĐđ]/.test(s)) return s;
  let o = s;
  for (const [re, to] of DICH) {
    re.lastIndex = 0;
    if (!re.flags.includes('i')) { o = o.replace(re, to); continue; }
    // cum khong phan biet hoa/thuong: giu kieu chu HOA cua ban goc
    o = o.replace(re, (m, ...g) => {
      const r = typeof to === 'function' ? to(m, ...g) : to.replace(/\$(\d)/g, (_, k) => g[k - 1] ?? '');
      const cap = m.charAt(0) !== m.charAt(0).toLowerCase();
      return (m === m.toUpperCase() && m !== m.toLowerCase()) ? r.toUpperCase() : (cap ? r.charAt(0).toUpperCase() + r.slice(1) : r);
    });
  }
  return o;
}

(function caiDichChu() {
  const AN = new Set((typeof PAGES !== 'undefined' ? PAGES : []).filter(p => p[3]).map(p => p[0]));
  const trangAn = () => AN.has((location.hash || '').replace(/^#/, '').split(/[?&]/)[0]);
  const BO = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'INPUT', 'CODE', 'PRE', 'svg']);
  let dang = false, hen = null;
  function chay() {
    hen = null;
    if (trangAn() || dang) return;
    dang = true;
    try {
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode(n) {
          for (let e = n.parentElement; e && e !== document.body; e = e.parentElement) {
            if (BO.has(e.tagName) || e.classList.contains('khong-dich') || e.isContentEditable) return NodeFilter.FILTER_REJECT;
          }
          return NodeFilter.FILTER_ACCEPT;
        }
      });
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        const v = n.nodeValue, m = dichChu(v);
        if (m !== v) n.nodeValue = m;
      }
      document.querySelectorAll('[title]').forEach(e => {
        const v = e.getAttribute('title'), m = dichChu(v);
        if (m !== v) e.setAttribute('title', m);
      });
    } finally { dang = false; }
  }
  const hoan = () => { if (!hen) hen = setTimeout(chay, 60); };
  new MutationObserver(ms => { if (!dang) hoan(); })
    .observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  window.addEventListener('hashchange', hoan);
  document.addEventListener('DOMContentLoaded', hoan);
  hoan();
})();
