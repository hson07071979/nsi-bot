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

  /* ---------- 1b. viên trạng thái thị trường ----------
     Lỗi 21/09 dạy hai lần cùng một bài: giờ phiên phải nằm ở MỌI lớp nhìn thấy
     được, không chỉ ở lớp gửi Telegram. Viên này đọc cùng một đồng hồ giờ Việt
     mà chuông đọc (gioVN của p13), nên không thể lệch nhau.
     Khung giờ HOSE: 9h00-9h15 ATO · 9h15-11h30 khớp lệnh · 11h30-13h00 nghỉ
     trưa · 13h00-14h30 khớp lệnh · 14h30-14h45 ATC · sau đó đóng.            */
  const _pill = document.getElementById('mktPill');
  if (_pill) {
    const _txt = document.getElementById('mktTxt');
    const _clk = document.getElementById('mktClk');
    const _sau = document.getElementById('mktSau');
    const hai = n => (n < 10 ? '0' : '') + n;

    // Dùng lại gioVN của p13 nếu có; không có thì tự tính, đừng để trang gãy.
    const gio = () => {
      if (typeof gioVN === 'function') { try { return gioVN(); } catch (e) { /* rơi xuống dưới */ } }
      const t = new Date();
      return new Date(t.getTime() + (t.getTimezoneOffset() + 420) * 60000);
    };

    function trangThai(t) {
      const d = t.getDay(), p = t.getHours() * 60 + t.getMinutes();
      if (d === 0 || d === 6) return { l: 'dong', t: 'ĐÓNG CỬA', m: d === 6 ? 'thứ Bảy' : 'Chủ nhật' };
      if (p < 540)             return { l: 'dong', t: 'CHƯA MỞ',  moLuc: 540 };
      if (p < 555)             return { l: 'atc',  t: 'ATO' };
      if (p < 690)             return { l: 'mo',   t: 'ĐANG MỞ' };
      if (p < 780)             return { l: 'trua', t: 'NGHỈ TRƯA', moLuc: 780 };
      if (p < 870)             return { l: 'mo',   t: 'ĐANG MỞ' };
      if (p < 885)             return { l: 'atc',  t: 'ATC' };
      return { l: 'dong', t: 'ĐÓNG CỬA', m: 'hết phiên' };
    }

    function ve() {
      const t = gio(), tt = trangThai(t);
      _pill.className = 'mkt ' + tt.l;
      _txt.textContent = tt.t;
      _clk.textContent = hai(t.getHours()) + ':' + hai(t.getMinutes()) + ':' + hai(t.getSeconds());
      let phu = tt.m || '';
      if (tt.moLuc != null) {
        const con = tt.moLuc - (t.getHours() * 60 + t.getMinutes());
        phu = con >= 60 ? 'mở sau ' + Math.floor(con / 60) + 'g' + hai(con % 60)
                        : 'mở sau ' + con + ' phút';
      }
      _sau.textContent = phu ? '· ' + phu : '';
    }

    ve();
    setInterval(ve, 1000);
  }

  /* ---------- 1c. bấm vào mã trong bảng là sang Chi tiết mã ----------
     Làm ở MỘT chỗ bằng uỷ quyền sự kiện, không sửa từng bảng. Lý do: ô mã
     (`td.sym` / `span.sym`) xuất hiện ở watchlist, bộ lọc, danh mục, chuông,
     lịch sử lệnh... sửa từng nơi là chín chỗ phải nhớ, bỏ sót một chỗ là
     người dùng bấm không ăn mà không biết vì sao.
     Chỉ ô nào có số liệu thật mới được gạch chân — gạch chân một mã bấm vào
     không ra gì còn khó chịu hơn là không gạch.                              */
  const coMa = s => {
    try { return !!((D.lookup || {})[s] || (D.candles || {})[s] || (D.funda || {})[s]); }
    catch (e) { return false; }
  };
  // Lấy đúng chữ mã: ô còn chứa chấm tím, nhãn "WL", nhãn "Chưa đăng"...
  const layMa = o => {
    const t = [...o.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
    const s = (t ? t.textContent : o.textContent).trim().split(/[\s·]+/)[0].toUpperCase();
    return /^[A-Z0-9]{3,4}$/.test(s) ? s : null;
  };
  const danhDau = () => {
    document.querySelectorAll('td.sym:not([data-ma]), span.sym:not([data-ma])').forEach(o => {
      const m = layMa(o);
      o.dataset.ma = (m && coMa(m)) ? m : '-';
      if (o.dataset.ma !== '-') {
        o.classList.add('malink');
        if (!o.title) o.title = o.dataset.ma + ' — bấm để mở Chi tiết mã';
      }
    });
  };

  document.addEventListener('click', ev => {
    const o = ev.target.closest && ev.target.closest('[data-ma]');
    if (!o || o.dataset.ma === '-') return;
    if (ev.target.closest('a, button, input, select')) return;   // đừng cướp nút sẵn có
    ev.preventDefault();
    const sym = o.dataset.ma;
    try { openChart(sym); } catch (e) { return; }
    // Đồng bộ luôn thanh tra cứu trên đỉnh, để hai chỗ không nói hai mã khác nhau.
    try { if (typeof nsiChonMa === 'function') nsiChonMa(sym, 'trang'); } catch (e) {}
  });

  // Bảng được vẽ lại mỗi lần đổi trang / sắp xếp lại cột -> phải đánh dấu lại.
  const goc = document.getElementById('main') || document.body;
  let hen = null;
  new MutationObserver(() => { clearTimeout(hen); hen = setTimeout(danhDau, 40); }).observe(goc, {childList: true, subtree: true});
  danhDau();

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
