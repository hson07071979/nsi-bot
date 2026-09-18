/* ============================================================================
   LỚP ĐIỆN THOẠI + CÀI THÀNH APP
   Nạp SAU p7.js. Đây là file DUY NHẤT được phép nằm sau p7 — lý do: p7 phải chạy
   bộ điều hướng trước, vì file này ĐỌC `secs` và `go` mà p7 khai báo. Nó chỉ
   thêm giao diện, không định nghĩa trang nào, nên đặt sau không làm hỏng thứ tự.

   VÌ SAO KHÔNG DỰNG MỘT APP RIÊNG
   Bản mẫu app riêng đã dựng xong rồi và đã bỏ. Lý do bỏ: bốn tab anh Sơn cần
   (Hiệu suất, Watchlist, Chi tiết mã, So sánh ngành) cần tới 92% khối dữ liệu
   của trang — tức app riêng sẽ phải chép lại gần như toàn bộ trang web, rồi từ
   đó mọi lần đổi luật phải sửa hai nơi. Sổ kiến trúc đã ghi ba lần vấp đúng bẫy
   đó: "Watchlist nới hơn bộ máy", "lớp quét thiếu điều kiện 7 và DK5", "sổ ghi
   tiến lệch sổ chính". Một bộ code, một bộ luật.

   FILE NÀY LÀM BA VIỆC, KHÔNG HƠN
     1. đăng ký service worker  -> cài được vào màn hình chính, mất mạng vẫn mở
     2. thanh điều hướng dưới   -> chỉ hiện dưới 700px, tầm ngón cái
     3. mời cài app             -> hiện một lần, nhớ lựa chọn

   KHÔNG đụng tới bất kỳ hàm pageXxx nào. Trên máy tính, trang chạy y như cũ —
   toàn bộ lớp này ẩn bằng @media, không một pixel nào đổi.
   ========================================================================== */
(function () {
  'use strict';

  /* ---------- 1. service worker ---------- */
  // Chỉ chạy trên https thật. Mở bằng file:// trên máy thì bỏ qua, không báo lỗi.
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        /* Chưa upload sw.js lên repo public thì im lặng bỏ qua — trang vẫn chạy
           đủ, chỉ là chưa cài được vào màn hình chính. */
      });
    });
  }

  /* ---------- 2. thanh điều hướng dưới ---------- */
  // Năm ô. Bốn trang hay mở nhất lúc 14h, cộng một nút mở ngăn còn lại.
  const DUOI = [
    ['chuong',    'Chuông',    '<path d="M18 8A6 6 0 1 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>'],
    ['danhmuc',   'Danh mục',  '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>'],
    ['watchlist', 'Watchlist', '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="2.6"/>'],
    ['hieusuat',  'Hiệu suất', '<path d="M3 3v18h18"/><path d="m7 14 3.5-4 3 2.5L20 6"/>'],
  ];
  // Ngăn "Thêm": những trang vẫn cần nhưng không phải thứ mở mỗi ngày.
  const THEM = [
    ['bieudo',    'Chi tiết mã',         'nến, 4 biểu đồ cơ bản, bảng 12 quý'],
    ['nganh',     'So sánh trong ngành', 'phân tán ROE × P/B và thanh khoảng 12 quý'],
    ['boloc',     'Bộ lọc',              'chấm điểm toàn bộ HOSE + HNX'],
    ['lenh',      'Lịch sử lệnh',        'toàn bộ lệnh đã vào và ra từ 2019'],
  ];

  // Trang nào không tồn tại (file chưa nạp) thì bỏ khỏi thanh, đừng để nút chết.
  const co = id => typeof secs !== 'undefined' && secs && secs[id];
  const duoi = DUOI.filter(x => co(x[0]));
  const them = THEM.filter(x => co(x[0]));
  if (!duoi.length) return;

  const nav = document.createElement('nav');
  nav.className = 'dnav';
  nav.innerHTML =
    duoi.map(([id, ten, svg]) =>
      `<button data-di="${id}"><span class="ic"><svg viewBox="0 0 24 24">${svg}</svg></span>${ten}</button>`).join('') +
    (them.length
      ? `<button data-them="1"><span class="ic"><svg viewBox="0 0 24 24"><circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/></svg></span>Thêm</button>`
      : '');
  document.body.appendChild(nav);

  const ngan = document.createElement('div');
  ngan.className = 'dngan';
  ngan.innerHTML =
    `<div class="dngan-nen" data-dong="1"></div>
     <div class="dngan-hop">
       <div class="dngan-keo"></div>
       ${them.map(([id, ten, mo]) =>
         `<button data-di="${id}"><b>${ten}</b><span>${mo}</span></button>`).join('')}
       <button data-dong="1" class="dngan-huy">Đóng</button>
     </div>`;
  document.body.appendChild(ngan);

  const moNgan = mo => {
    ngan.classList.toggle('on', mo);
    document.body.style.overflow = mo ? 'hidden' : '';
  };

  // Tô sáng ô đang mở. Trang nằm trong ngăn "Thêm" thì tô ô Thêm — đỡ phải đoán
  // mình đang đứng ở đâu.
  const idThem = new Set(them.map(x => x[0]));
  function toSang(id) {
    nav.querySelectorAll('button').forEach(b => {
      b.classList.toggle('on', b.dataset.di === id || (b.dataset.them && idThem.has(id)));
    });
  }

  nav.querySelectorAll('[data-di]').forEach(b =>
    b.onclick = () => { go(b.dataset.di); toSang(b.dataset.di); });
  nav.querySelectorAll('[data-them]').forEach(b => b.onclick = () => moNgan(true));
  ngan.querySelectorAll('[data-di]').forEach(b =>
    b.onclick = () => { moNgan(false); go(b.dataset.di); toSang(b.dataset.di); });
  ngan.querySelectorAll('[data-dong]').forEach(b => b.onclick = () => moNgan(false));

  // Bấm nút Back của trình duyệt cũng phải tô lại cho đúng.
  window.addEventListener('hashchange', () => toSang((location.hash || '').slice(1)));
  toSang((location.hash || '').slice(1) || (typeof HOME !== 'undefined' ? HOME : 'hieusuat'));

  /* ---------- 3. mời cài app ---------- */
  const KHOA = 'nsi_pwa_moi';
  const daTuChoi = () => { try { return localStorage.getItem(KHOA) === 'thoi'; } catch (e) { return false; } };
  const nho = v => { try { localStorage.setItem(KHOA, v); } catch (e) { /* chế độ riêng tư */ } };
  const daCai = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

  function veMoi(noiDung, nut) {
    if (daCai() || daTuChoi() || document.querySelector('.dmoi')) return null;
    const b = document.createElement('div');
    b.className = 'dmoi';
    b.innerHTML = `<div>${noiDung}</div>
      <div class="dmoi-nut">${nut}<button class="btn ghost" data-thoi="1">Để sau</button></div>`;
    document.body.appendChild(b);
    b.querySelector('[data-thoi]').onclick = () => { nho('thoi'); b.remove(); };
    return b;
  }

  // Android / Chrome: trình duyệt tự hỏi được, mình chỉ giữ lời mời lại để hiện
  // đúng lúc thay vì bật ngay khi vừa mở trang.
  let loiMoi = null;
  window.addEventListener('beforeinstallprompt', ev => {
    ev.preventDefault();
    loiMoi = ev;
    const b = veMoi(
      '<b>Cài vào màn hình chính</b><br>Mở thẳng như một app, không thanh địa chỉ, mất mạng vẫn xem được bản lần trước.',
      '<button class="btn" data-cai="1">Cài</button>');
    if (b) b.querySelector('[data-cai]').onclick = async () => {
      b.remove();
      loiMoi.prompt();
      const kq = await loiMoi.userChoice;
      nho(kq.outcome === 'accepted' ? 'xong' : 'thoi');
      loiMoi = null;
    };
  });

  // iPhone: Safari KHÔNG có beforeinstallprompt. Bắt buộc người dùng tự bấm
  // Chia sẻ -> Thêm vào MH chính. Nói thẳng ra thay vì để anh Sơn tự mò.
  const laIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
                (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (laIOS && !daCai()) {
    setTimeout(() => veMoi(
      '<b>Cài vào màn hình chính</b><br>Bấm nút <b>Chia sẻ</b> ở thanh dưới Safari, kéo xuống chọn <b>Thêm vào MH chính</b>.',
      ''), 2500);
  }
})();
