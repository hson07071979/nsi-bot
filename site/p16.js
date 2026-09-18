/* ============================================================================
   BỐN BIỂU ĐỒ CƠ BẢN — bản vá 18/09/2026

   Quét thật 110 mã trong TOP thanh khoản, không sửa theo từng mã lẻ. Bốn ca vỡ
   tìm được, ba cái là lỗi, một cái là hiểu sai chú thích:

     1. 12/110 mã VẼ RA NGOÀI KHUNG ở biểu đồ Định giá.
        `opt.zero` ép mép dưới về 0, nhưng P/E ÂM vẫn được vẽ, mà CSS có
        `svg{overflow:visible}` — nên đường P/E chạy tuột ra khỏi thẻ.
        Nặng nhất: BSR −1740 (mã đang cầm), VPL −1551, DCL −1348.
        Chữa ở HAI lớp độc lập:
          · gốc  — P/E khi doanh nghiệp LỖ là con số vô nghĩa (P/E −1740 nghĩa
                   là "lỗ rất mỏng", không phải "rẻ"). Bỏ hẳn, đánh dấu quý đó
                   là "lỗ" thay vì vẽ một con số không đọc được.
          · chặn — thêm <clipPath>: dù sau này có lọt giá trị nào nữa thì nét vẽ
                   cũng bị cắt ở mép khung, không bao giờ tràn ra thẻ được.

     2. 8/110 mã có LNST bẹp thành gạch 1,5px ở biểu đồ Quy mô, vì doanh thu lớn
        gấp 40–98 lần (SHI 97,8× · PLX 48,6×). Chung một trục thì cột nhỏ biến
        mất. Chữa: tự động tách TRỤC PHẢI cho chuỗi nhỏ khi tỷ lệ ≥ 25 lần, và
        nói rõ "hai trục" ngay trên biểu đồ để không ai so chiều cao hai màu.

     3. `filter(v => v != null)` KHÔNG chặn được NaN — `NaN != null` là true.
        Hôm nay dữ liệu sạch (0 NaN) nhờ ba lớp hôm qua, nhưng hàm vẽ vẫn phải
        tự đứng được: đổi sang Number.isFinite.

     4. Biên ±150% chạm ở 78/110 mã — tức là TRẠNG THÁI BÌNH THƯỜNG, không phải
        ngoại lệ. Câu chú thích cố định "cột mờ = vượt biên" đang nói về 71% số
        mã mà không ai biết. Chữa: cột chạm biên có mũi nhọn ở đầu, và chú thích
        tự đếm đúng số cột bị cắt của CHÍNH mã đang xem.
   ========================================================================== */

/* số dùng được = có thật, hữu hạn. NaN và Infinity bị loại như thể thiếu số. */
const so = v => typeof v === 'number' && Number.isFinite(v);

let _cpId = 0;                        // mỗi biểu đồ một clipPath riêng

function cotKep(host, labels, series, opt = {}) {
  const W = FCW, H = FCH, PL = 54, PR = 10, PT = 14, PB = 34;
  const tran = opt.cap || null;
  const kep = v => tran ? Math.max(-tran, Math.min(tran, v)) : v;

  // ---- có cần trục phải không? ----
  // Chuỗi nhỏ bị nuốt khi chuỗi lớn gấp >= 25 lần. Đo trên biên độ thật, không
  // phải trên giá trị lớn nhất, để chuỗi có số âm cũng đo đúng.
  const bien = s => {
    const v = (s.v || []).filter(so);
    return v.length ? Math.max(...v.map(Math.abs)) : 0;
  };
  let hai = false;
  if (series.length === 2 && opt.truc2 !== false && !tran) {
    const a = bien(series[0]), b = bien(series[1]);
    hai = a > 0 && b > 0 && (a / b >= 25 || b / a >= 25);
  }

  // ---- thang đo: một thang chung, hoặc một thang cho mỗi trục ----
  const thang = ss => {
    const v = ss.flatMap(s => (s.v || []).filter(so)).map(kep);
    if (!v.length) return null;
    let hi = Math.max(...v, 0), lo = Math.min(...v, 0);
    const pad = (hi - lo) * 0.12 || Math.abs(hi) * 0.12 || 1;
    hi += pad;
    // Chỉ nới mép dưới khi thật sự có giá trị âm. Không thì trục hiện "−2427 tỷ
    // doanh thu" — một con số không tồn tại, chỉ là khoảng đệm bị dán nhãn.
    lo = lo < 0 ? lo - pad : 0;
    // Đã cắt ở ±cap thì TRỤC cũng không được in số vượt quá cap — chú thích ghi
    // "chạm biên ±150%" mà trục hiện −186% là hai con số nói hai chuyện khác nhau.
    // PHẢI kẹp SAU dòng nới mép dưới: kẹp trước thì dòng đó trừ thêm pad lần nữa
    // và biên lại vọt ra ngoài. Đã vấp đúng thứ tự này một lần.
    if (tran) { hi = Math.min(hi, tran); lo = Math.max(lo, -tran); }
    return { hi, lo };
  };
  const T = hai ? [thang([series[0]]), thang([series[1]])] : [thang(series)];
  if (!T[0]) { host.innerHTML = '<p class="muted" style="margin:0">Chưa có số liệu.</p>'; return; }
  if (hai && !T[1]) hai = false;

  const PR2 = hai ? 48 : PR;                       // chừa chỗ cho trục phải
  const n = labels.length, nS = series.length;
  const X = i => PL + (i + 0.5) * (W - PL - PR2) / n;
  const Yk = (v, k) => {
    const t = T[hai ? k : 0];
    return PT + (1 - (v - t.lo) / (t.hi - t.lo)) * (H - PT - PB);
  };
  const bw = (W - PL - PR2) / n * 0.66 / nS;
  const cp = 'cpk' + (++_cpId);
  const fmt = opt.fmt || (x => x.toFixed(0));
  const fmt2 = opt.fmt2 || fmt;

  let s = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" font-family="inherit">
    <defs><clipPath id="${cp}"><rect x="${PL}" y="${PT - 2}" width="${W - PL - PR2}" height="${H - PT - PB + 2}"/></clipPath></defs>`;

  // lưới + trục trái (luôn theo thang 0)
  for (let k = 0; k <= 3; k++) {
    const v = T[0].lo + (T[0].hi - T[0].lo) * k / 3, y = Yk(v, 0);
    s += `<line x1="${PL}" x2="${W - PR2}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="1"/>
          <text x="${PL - 7}" y="${y + 4}" text-anchor="end" font-size="11" fill="var(${hai ? series[0].color : '--text-muted'})">${fmt(v)}</text>`;
  }
  // trục phải, chỉ khi tách hai thang
  if (hai) {
    for (let k = 0; k <= 3; k++) {
      const v = T[1].lo + (T[1].hi - T[1].lo) * k / 3, y = Yk(v, 1);
      s += `<text x="${W - PR2 + 7}" y="${y + 4}" text-anchor="start" font-size="11" fill="var(${series[1].color})">${fmt2(v)}</text>`;
    }
  }
  if (T[0].lo < 0 && T[0].hi > 0)
    s += `<line x1="${PL}" x2="${W - PR2}" y1="${Yk(0, 0)}" y2="${Yk(0, 0)}" stroke="var(--text-muted)" stroke-width="1.2" opacity=".55"/>`;

  // ---- cột ----
  let nCat = 0, nCo = 0;
  s += `<g clip-path="url(#${cp})">`;
  series.forEach((se, k) => {
    (se.v || []).forEach((v0, i) => {
      if (!so(v0)) return;
      nCo++;
      const cut = tran && Math.abs(v0) > tran;
      if (cut) nCat++;
      const v = cut ? Math.sign(v0) * tran : v0;
      const x = X(i) - (nS * bw) / 2 + k * bw;
      const y = Math.min(Yk(v, k), Yk(0, k)), h = Math.max(1.5, Math.abs(Yk(v, k) - Yk(0, k)));
      const w = bw * 0.86;
      const tip = `<title>${labels[i]} · ${esc(se.name)}: ${(opt.fmtV || fmt)(v0)}${cut ? ' (vượt biên, cột bị cắt)' : ''}</title>`;
      if (cut) {
        // Cột chạm biên có ĐẦU NHỌN — nhìn là biết bị cắt, không phải đoán qua độ mờ.
        const len = v0 > 0 ? y : y + h, mui = v0 > 0 ? len + 7 : len - 7;
        s += `<path d="M ${x} ${v0 > 0 ? y + 7 : y} h ${w} ${v0 > 0 ? `v ${h - 7} h ${-w} Z` : `v ${h - 7} l ${-w / 2} 7 l ${-w / 2} -7 Z`}"
               fill="var(${se.color})" opacity=".45">${tip}</path>
              <path d="M ${x} ${v0 > 0 ? y + 7 : y + h - 7} l ${w / 2} ${v0 > 0 ? -7 : 7} l ${w / 2} ${v0 > 0 ? 7 : -7} Z"
               fill="var(${se.color})" opacity=".95">${tip}</path>`;
      } else {
        s += `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="var(${se.color})" rx="1" opacity=".92">${tip}</rect>`;
      }
    });
  });
  s += '</g>';

  // Nhãn quý: 12 nhãn trong 560 đơn vị thì chật, nên xoay nghiêng cho dễ đọc
  // thay vì để chúng dính vào nhau.
  labels.forEach((l, i) => {
    s += `<text x="${X(i)}" y="${H - PB + 16}" text-anchor="end" font-size="10.5" fill="var(--text-muted)"
           transform="rotate(-38 ${X(i)} ${H - PB + 16})">${l}</text>`;
  });
  s += '</svg>';

  // chú thích tự đếm — nói đúng chuyện của CHÍNH mã đang xem
  let ghi = '';
  if (tran && nCat) ghi = `<b>${nCat}/${nCo} cột chạm biên ±${tran}%</b> — đầu nhọn là cột bị cắt, thường do nền cùng kỳ gần bằng không. Số thật xem ở bảng dưới.`;
  else if (hai) ghi = `<b>Hai trục khác nhau.</b> ${esc(series[0].name)} đọc ở trục trái, ${esc(series[1].name)} ở trục phải — chênh nhau trên ${Math.round(Math.max(bien(series[0]) / bien(series[1]), bien(series[1]) / bien(series[0])))} lần nên chung một trục thì cột nhỏ biến mất. <b>Đừng so chiều cao hai màu với nhau.</b>`;
  host.innerHTML = s + (ghi ? `<p class="muted" style="margin:6px 0 0;font-size:12px">${ghi}</p>` : '');
}

function duongQuy(host, labels, series, opt = {}) {
  const W = FCW, H = FCH, PL = 54, PT = 18, PB = 34;
  // `zero: true` nghĩa là "đại lượng này KHÔNG âm được về bản chất" — P/E, P/B.
  // P/E của quý LỖ thì âm, mà P/E −1740 không có nghĩa "rẻ gấp 1740 lần": càng lỗ
  // ít thì con số càng âm to. Đó là một đại lượng không tồn tại, và chính nó kéo
  // đường P/E của 12/110 mã chạy ra ngoài thẻ (BSR −1740 · VPL −1551 · DCL −1348).
  // Cách đúng, cũng là cách mọi bảng điện chuyên nghiệp làm: quý lỗ thì để TRỐNG.
  let nBo = 0;
  const boQuy = new Array(labels.length).fill(false);
  if (opt.zero) {
    series = series.map(s2 => ({ ...s2, v: (s2.v || []).map((v, i) => {
      if (so(v) && v <= 0) { nBo++; boQuy[i] = true; return null; }
      return v;
    }) }));
  }
  if (!series.flatMap(s2 => (s2.v || []).filter(so)).length) {
    host.innerHTML = '<p class="muted" style="margin:0">Chưa có số liệu.</p>'; return;
  }

  // ---- P/E và P/B KHÔNG được dùng chung một trục -------------------------
  // Sai lầm 18/09: chung trục thì với VND (P/E tới 23,5 · P/B quanh 1,2) đường P/B
  // bị ép thành một vạch nằm sát đáy, không đọc được gì. Bản trước em dán một câu
  // "chỉ so được hình dáng" rồi bỏ qua — đó là viết lời bào chữa chứ không phải sửa.
  // Cùng một bệnh với biểu đồ Quy mô, và cùng một thuốc: tách trục.
  const bien = s2 => { const v = (s2.v || []).filter(so); return v.length ? Math.max(...v.map(Math.abs)) : 0; };
  let hai = false;
  if (series.length === 2 && opt.truc2 !== false) {
    const a = bien(series[0]), b = bien(series[1]);
    hai = a > 0 && b > 0 && (a / b >= 6 || b / a >= 6);
  }
  const thang = ss => {
    const v = ss.flatMap(s2 => (s2.v || []).filter(so));
    if (!v.length) return null;
    let hi = Math.max(...v), lo = Math.min(...v);
    const pad = (hi - lo) * 0.18 || Math.abs(hi) * 0.1 || 1;
    hi += pad;
    // `zero` chỉ được ép sàn 0 khi KHÔNG có giá trị âm nào. Bản cũ ép vô điều
    // kiện, nên P/E âm vẫn vẽ nhưng nằm dưới đáy khung và chạy ra ngoài thẻ.
    lo = (opt.zero && lo >= 0) ? 0 : lo - pad;
    return { hi, lo };
  };
  const T = hai ? [thang([series[0]]), thang([series[1]])] : [thang(series)];
  if (hai && (!T[0] || !T[1])) hai = false;
  const PR = hai ? 46 : 14;
  const n = labels.length;
  const X = i => PL + (i + 0.5) * (W - PL - PR) / n;
  const Yk = (v, k) => {
    const t = T[hai ? k : 0];
    return PT + (1 - (v - t.lo) / (t.hi - t.lo)) * (H - PT - PB);
  };
  const Y = v => Yk(v, 0);
  const f = opt.fmt || (x => x.toFixed(1));
  const f2 = opt.fmt2 || f;
  // Nhãn trục chỉ có 47 đơn vị. "74808.41" của NVB dài 51 đơn vị nên đè lên chính
  // biểu đồ. Quá dài thì rút gọn k/tr — con số đầy đủ vẫn nằm ở bảng 12 quý bên dưới.
  const RONG = 47;
  const gon = (v, ff) => {
    const t = ff(v);
    if (t.length * 11 * 0.58 <= RONG) return t;
    const a = Math.abs(v);
    if (a >= 1e6) return (v / 1e6).toFixed(1) + 'tr';
    if (a >= 1e3) return (v / 1e3).toFixed(1) + 'k';
    return v.toFixed(0);
  };
  const cp = 'cpd' + (++_cpId);

  let s = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" font-family="inherit">
    <defs><clipPath id="${cp}"><rect x="${PL}" y="${PT - 4}" width="${W - PL - PR}" height="${H - PT - PB + 8}"/></clipPath></defs>`;
  for (let k = 0; k <= 3; k++) {
    const v = T[0].lo + (T[0].hi - T[0].lo) * k / 3, y = Yk(v, 0);
    s += `<line x1="${PL}" x2="${W - PR}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-width="1"/>
          <text x="${PL - 7}" y="${y + 4}" text-anchor="end" font-size="11" fill="var(${hai ? series[0].color : '--text-muted'})">${gon(v, f)}</text>`;
  }
  if (hai) {
    for (let k = 0; k <= 3; k++) {
      const v = T[1].lo + (T[1].hi - T[1].lo) * k / 3, y = Yk(v, 1);
      s += `<text x="${W - PR + 7}" y="${y + 4}" text-anchor="start" font-size="11" fill="var(${series[1].color})">${gon(v, f2)}</text>`;
    }
  }
  // cột mờ đánh dấu quý KHÔNG có số (lỗ, hoặc chưa công bố) — để chỗ trống trên
  // đường không bị đọc nhầm thành "đi ngang". Có dán chữ, không thì nhìn như
  // một vệt xám vô nghĩa giữa biểu đồ.
  (opt.trong || boQuy).forEach((co, i) => {
    if (!co) return;
    const w = (W - PL - PR) / n;
    s += `<rect x="${X(i) - w / 2}" y="${PT}" width="${w}" height="${H - PT - PB}"
           fill="var(--text-muted)" opacity=".10"><title>${labels[i]} · ${esc(opt.trongVi || 'quý lỗ — không có P/E')}</title></rect>
          <text x="${X(i)}" y="${PT + 12}" text-anchor="middle" font-size="9.5" font-weight="700"
           fill="var(--text-muted)" opacity=".85">lỗ</text>`;
  });

  // Gom mọi nhãn nổi vào một danh sách rồi mới đẩy tránh nhau — vẽ ngay tại chỗ
  // là cách sinh ra cảnh "5.8" nằm đè lên "6.6".
  const nhan = [];
  if (so(opt.tb)) {
    s += `<line x1="${PL}" x2="${W - PR}" y1="${Y(opt.tb)}" y2="${Y(opt.tb)}" stroke="var(--text-muted)"
           stroke-width="1.1" stroke-dasharray="5 4" opacity=".65"/>`;
    nhan.push({ y: Y(opt.tb) - 6, x: W - PR - 3, neo: 'end', chu: 'TB ' + f(opt.tb), mau: 'var(--text-muted)', dam: 600 });
  }
  s += `<g clip-path="url(#${cp})">`;
  series.forEach((se, k) => {
    const ff = (hai && k === 1) ? f2 : f;
    let d = '', bat = false;
    (se.v || []).forEach((v, i) => { if (!so(v)) { bat = false; return; } d += (bat ? 'L' : 'M') + X(i) + ' ' + Yk(v, k); bat = true; });
    if (d) s += `<path d="${d}" fill="none" stroke="var(${se.color})" stroke-width="1.9" stroke-linejoin="round"/>`;
    (se.v || []).forEach((v, i) => {
      if (!so(v)) return;
      // Điểm ĐỨNG MỘT MÌNH (hai bên đều trống) không có đoạn thẳng nào nối vào,
      // nên vẽ bằng chấm thường thì trông như bụi trên màn hình — đã bị hiểu nhầm
      // đúng một lần. Cho nó vòng tròn để rõ đó là một quý có số thật.
      const le = !so((se.v || [])[i - 1]) && !so((se.v || [])[i + 1]);
      s += le
        ? `<circle cx="${X(i)}" cy="${Yk(v, k)}" r="4.2" fill="var(--surface-1)" stroke="var(${se.color})" stroke-width="2.2"><title>${labels[i]} · ${esc(se.name)}: ${ff(v)} (quý đứng một mình, hai bên không có số)</title></circle>`
        : `<circle cx="${X(i)}" cy="${Yk(v, k)}" r="2.6" fill="var(${se.color})"><title>${labels[i]} · ${esc(se.name)}: ${ff(v)}</title></circle>`;
    });
    const cuoi = [...(se.v || [])].reverse().find(so);
    if (so(cuoi)) {
      const i = se.v.lastIndexOf(cuoi);
      nhan.push({ y: Yk(cuoi, k) - 8, x: Math.min(X(i) + 6, W - PR), neo: 'end', chu: ff(cuoi), mau: `var(${se.color})`, dam: 700 });
    }
  });
  s += '</g>';
  // đẩy tránh nhau: nhãn nào cách nhãn trước dưới 13 đơn vị thì đùn xuống
  nhan.sort((a, b) => a.y - b.y);
  for (let k = 1; k < nhan.length; k++) {
    if (nhan[k].y - nhan[k - 1].y < 13) nhan[k].y = nhan[k - 1].y + 13;
  }
  nhan.forEach(t => {
    // viền nền cùng màu trang: chữ nằm trên đường kẻ vẫn đọc được
    s += `<text x="${t.x}" y="${Math.max(PT + 10, Math.min(t.y, H - PB - 2))}" text-anchor="${t.neo}" font-size="12" font-weight="${t.dam}"
           fill="${t.mau}" stroke="var(--surface-1)" stroke-width="3.2" paint-order="stroke"
           stroke-linejoin="round">${t.chu}</text>`;
  });
  labels.forEach((l, i) => {
    s += `<text x="${X(i)}" y="${H - PB + 16}" text-anchor="end" font-size="10.5" fill="var(--text-muted)"
           transform="rotate(-38 ${X(i)} ${H - PB + 16})">${l}</text>`;
  });
  s += '</svg>';

  const ghi = [];
  if (nBo) ghi.push(`<b>${nBo}/${labels.length} quý doanh nghiệp lỗ</b> nên không có P/E — cột tô mờ có chữ "lỗ" là những quý đó.`);
  if (hai) ghi.push(`<b>Hai trục riêng.</b> ${esc(series[0].name)} đọc ở trục trái, ${esc(series[1].name)} ở trục phải — màu số trên trục khớp màu đường.`);
  host.innerHTML = s + (ghi.length
    ? `<p class="muted" style="margin:6px 0 0;font-size:12px">${ghi.join(' ')}</p>` : '');
}

/* ============================================================================
   SO SÁNH TRONG NGÀNH — kiểu Khoa Nguyen
   Tên file p16.js (p13/p14/p15 đã có chủ). Nạp SAU p9.js (dùng `so`, `_cpId`),
   TRƯỚC p7.js (p7 chạy bộ điều hướng ngay khi nạp xong).

   HAI KHỐI TÁCH HẲN NHAU, cố ý:

     1. PHÂN TÁN — "ngay lúc này, mã nào rẻ so với mã nào".
        Hai đường đứt là TRUNG VỊ ngành. Vùng tô xanh là góc đáng đào: định giá
        dưới trung vị mà hiệu quả trên trung vị. Không kẻ lưới, không đổi cỡ
        điểm theo vốn hoá, chỉ 3 vạch mỗi trục — mọi nét thừa đều làm chậm việc
        đọc, mà việc đọc ở đây chỉ có một câu hỏi: nó nằm góc nào.

     2. THANH KHOẢNG — "so với CHÍNH NÓ trong quá khứ thì đang ở đâu".
        Mỗi mã một thanh, xanh (đáy khoảng) sang đỏ (đỉnh khoảng), chấm đen là
        vị trí hiện tại, vạch dọc mảnh là trung vị ngành.

   Nhồi thanh khoảng vào trong biểu đồ phân tán là cách nhanh nhất để không đọc
   được cái nào — đã thử, đã bỏ.

   QUY TẮC GHÉP TRỤC — chốt 17/09, không ghép bừa:
     P/B đi với ROE                vì P/B hợp lý ≈ (ROE − g)/(r − g)
     P/E đi với TĂNG TRƯỞNG LNST   logic PEG
   Lấy ROE làm trục tung cho ngành đang so bằng P/E là ghép SAI.

   BA CHỖ DỮ LIỆU KHÔNG CHO LÀM ĐÚNG Ý — ghi thẳng lên trang, không giấu:
     1. Dầu khí lẽ ra là EV/EBITDA × biên EBITDA. Dữ liệu trang KHÔNG có EBITDA
        lẫn nợ ròng, nên đang vẽ TẠM bằng P/B × ROE.
     2. Khoảng chỉ được 12 QUÝ, không phải 5 năm — `funda` giữ đúng 12 quý. Ghi
        đúng "12 quý", không ghi 5 năm.
     3. Đa ngành không phải nhóm ICB. Danh sách dưới đây do người chọn.

   MẪU NHỎ: dưới 6 mã thì trung vị chỉ là "con số ở giữa mấy con số". Vẫn vẽ,
   nhưng dán băng cảnh báo — im lặng ở đây là nói dối bằng cách bỏ sót.
   ========================================================================== */

const NGANH_DA = ['VIC', 'MSN', 'GEX', 'PAN', 'HAG', 'TCH'];   // <-- sửa ở đây

const NGANH = [
  { id: 'nganhang', ten: 'Ngân hàng', icb: ['Ngân hàng'], x: 'pb', y: 'roe',
    vi: 'P/B là chuẩn mực của nhóm này. Lợi nhuận méo theo chu kỳ trích lập dự phòng — muốn giấu lãi thì trích mạnh, muốn làm đẹp sổ thì trích ít — nên E biến động và P/E mất ý nghĩa. Vốn chủ mới là gốc.' },
  { id: 'chungkhoan', ten: 'Chứng khoán', icb: ['Dịch vụ tài chính'], x: 'pb', y: 'roe',
    vi: 'Vốn chủ quyết định cho vay margin được bao nhiêu và sức chứa tự doanh tới đâu — đó là trần tăng trưởng thật của một công ty chứng khoán.' },
  { id: 'bds', ten: 'Bất động sản', icb: ['Bất động sản'], x: 'pb', y: 'roe',
    vi: 'P/B là thước <b>ít tệ nhất</b>, không phải thước đúng. Book value ghi đất theo giá gốc nên hiểu thấp giá trị thật; doanh thu dồn cục theo kỳ bàn giao nên một quý đẹp không nói lên gì.',
    thieu: 'Thước ghép lẽ ra có thêm <b>người mua trả tiền trước ÷ vốn hoá</b> — cho biết đã bán được bao nhiêu hàng chưa ghi nhận. Trường đó chưa có trong dữ liệu trang.' },
  { id: 'banle', ten: 'Bán lẻ', icb: ['Bán lẻ'], x: 'pe', y: 'npat_yoy',
    vi: 'Biên mỏng nên P/E phải đi cùng <b>tốc độ tăng trưởng</b> (logic PEG): P/E 25 với tăng trưởng 40% rẻ hơn P/E 12 với tăng trưởng 0%.',
    thieu: 'Hai chỗ chưa đúng hẳn: <b>(1)</b> trục tung là tăng trưởng <b>LNST</b> chứ chưa phải <b>EPS</b> — hai cái lệch nhau khi doanh nghiệp phát hành thêm cổ phiếu; <b>(2)</b> nhóm này thuê mặt bằng nặng nên đáng lẽ xem kèm <b>EV/EBITDA</b>, mà dữ liệu trang chưa có EBITDA.' },
  { id: 'daukhi', ten: 'Dầu khí', icb: ['Dầu khí'], x: 'pb', y: 'roe', tam: true,
    vi: 'Thước đúng của nhóm này là <b>EV/EBITDA</b>, <b>không</b> phải P/E — lợi nhuận nhảy theo giá dầu và theo đánh giá lại tồn kho, nên một năm lãi đậm không có nghĩa doanh nghiệp tốt lên.',
    thieu: '<b>Biểu đồ dưới đang vẽ bằng thước TẠM (P/B × ROE).</b> Dữ liệu trang không có EBITDA lẫn nợ ròng nên chưa dựng được EV/EBITDA — phải thêm hai trường đó vào <code>fetch_funda.py</code>. Từ giờ tới lúc đó, đọc như ước lượng thô, đừng dùng để kết luận rẻ hay đắt.' },
  { id: 'danganh', ten: 'Đa ngành', tay: NGANH_DA, x: 'pb', y: 'roe', sotp: true,
    vi: 'P/E gộp của một tập đoàn nhiều mảng gần như vô nghĩa: cộng lợi nhuận mảng bất động sản với mảng sản xuất rồi chia cho một mức giá chung thì ra một con số không mô tả cái gì cả.',
    thieu: 'Thước đúng là <b>SOTP</b> — định giá riêng từng mảng rồi cộng lại, trừ nợ ròng công ty mẹ. Việc đó <b>không vẽ được bằng một biểu đồ hai trục</b> và cũng không tự động hoá được: phải bóc thuyết minh từng doanh nghiệp bằng tay. Biểu đồ dưới chỉ cho thấy cả nhóm đang nằm ở đâu, <b>không phải định giá</b>.' },
];

function _cuoiSo(a) { for (let i = (a || []).length - 1; i >= 0; i--) if (so(a[i])) return a[i]; return null; }
function _trungVi(a) {
  const v = a.filter(so).slice().sort((x, y) => x - y);
  if (!v.length) return null;
  const m = v.length >> 1;
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

function nganhSoLieu(cf) {
  const rows = (D.screener || {}).rows || [], F = D.funda || {}, L = D.lookup || {};
  const ds = cf.tay ? rows.filter(r => cf.tay.includes(r.sym))
                    : rows.filter(r => cf.icb.includes(r.sector));
  return ds.map(r => {
    const f = F[r.sym] || {};
    // P/E chỉ có nghĩa khi CÓ LÃI — quý lỗ cho P/E âm, một con số không đọc được.
    const chuoi = (cf.x === 'pe' ? (f.pe || []).map(v => (so(v) && v > 0) ? v : null) : (f.pb || [])).filter(so);
    const x = cf.x === 'pe' ? _cuoiSo((f.pe || []).map(v => (so(v) && v > 0) ? v : null)) : _cuoiSo(f.pb);
    const roe = so(r.roe) ? r.roe : _cuoiSo(f.roe);
    const y = cf.y === 'roe' ? roe : (so(r.npat_yoy) ? r.npat_yoy : null);
    const lo = chuoi.length ? Math.min(...chuoi) : null, hi = chuoi.length ? Math.max(...chuoi) : null;
    return {
      sym: r.sym, ten: (L[r.sym] || {}).name || '', mktcap: r.mktcap, roe, x, y, lo, hi,
      nq: chuoi.length, rev_yoy: so(r.rev_yoy) ? r.rev_yoy : null,
      tim: !!r.tim, tim_vi: r.tim_vi, blocked: !!r.blocked, block: r.block,
      // vị trí trong khoảng của chính nó, 0 = đáy khoảng, 1 = đỉnh khoảng
      vt: (so(x) && so(lo) && so(hi) && hi > lo) ? (x - lo) / (hi - lo) : null,
    };
  });
}

/* ---------- 1. PHÂN TÁN — ít nét nhất có thể ---------- */
function nganhPhanTan(host, ds, cf) {
  const W = 560, H = 330, PL = 46, PR = 34, PT = 26, PB = 40;
  const co = ds.filter(d => so(d.x) && so(d.y));
  if (co.length < 2) { host.innerHTML = '<p class="muted" style="margin:0">Không đủ mã có số liệu để vẽ.</p>'; return; }
  const xs = co.map(d => d.x), ys = co.map(d => d.y);
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const px = (x1 - x0) * 0.16 || Math.abs(x1) * 0.16 || 1;
  const py = (y1 - y0) * 0.18 || Math.abs(y1) * 0.18 || 1;
  x0 = Math.max(0, x0 - px); x1 += px; y0 = Math.min(0, y0 - py); y1 += py;
  const X = v => PL + (v - x0) / (x1 - x0) * (W - PL - PR);
  const Y = v => PT + (1 - (v - y0) / (y1 - y0)) * (H - PT - PB);
  const mx = _trungVi(xs), my = _trungVi(ys);
  const fx = cf.x === 'pe' ? (v => v.toFixed(1)) : (v => v.toFixed(2).replace('.', ','));
  const fy = v => v.toFixed(0) + '%';
  const tenX = cf.x === 'pe' ? 'P/E' : 'P/B';
  const tenY = cf.y === 'roe' ? 'ROE' : 'LNST YoY';
  const reHon = d => d.x <= mx && d.y >= my;          // góc đáng đào

  // Không kẻ lưới. Ba vạch mỗi trục, đặt ở mép. Người đọc cần biết mã nào nằm
  // góc nào, không cần đọc toạ độ chính xác của từng điểm.
  let s = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" font-family="inherit">
    <rect x="${PL - 8}" y="${PT - 14}" width="${W - PL - PR + 20}" height="${H - PT - PB + 26}" rx="8"
     fill="var(--surface-2)" opacity=".45"/>
    <rect x="${PL - 8}" y="${PT - 14}" width="${X(mx) - PL + 8}" height="${Y(my) - PT + 14}"
     fill="var(--good)" opacity=".13"/>
    <text x="${PL + 2}" y="${PT + 2}" font-size="13" font-weight="800" fill="var(--good)" letter-spacing=".04em">RẺ · SINH LỜI TỐT</text>`;

  // vạch trục: đáy, giữa, đỉnh
  [y0, (y0 + y1) / 2, y1].forEach(v =>
    s += `<text x="${PL - 12}" y="${Y(v) + 4}" text-anchor="end" font-size="12" font-weight="600" fill="var(--text-muted)">${fy(v)}</text>`);
  [x0, (x0 + x1) / 2, x1].forEach(v =>
    s += `<text x="${X(v)}" y="${H - PB + 22}" text-anchor="middle" font-size="12" font-weight="600" fill="var(--text-muted)">${fx(v)}</text>`);
  s += `<text x="${PL - 12}" y="${PT - 6}" text-anchor="end" font-size="14" font-weight="800" fill="var(--text-secondary)">${tenY}</text>
        <text x="${W - PR + 8}" y="${H - PB + 22}" text-anchor="start" font-size="14" font-weight="800" fill="var(--text-secondary)">${tenX}</text>`;

  // hai đường trung vị
  s += `<line x1="${X(mx)}" x2="${X(mx)}" y1="${PT - 14}" y2="${H - PB + 6}" stroke="var(--text-muted)" stroke-width="1.2" stroke-dasharray="5 4" opacity=".7"/>
        <line x1="${PL - 8}" x2="${W - PR + 12}" y1="${Y(my)}" y2="${Y(my)}" stroke="var(--text-muted)" stroke-width="1.2" stroke-dasharray="5 4" opacity=".7"/>
        <text x="${X(mx) + 6}" y="${H - PB + 1}" font-size="11.5" font-weight="650" fill="var(--text-muted)">${tenX} trung vị ${fx(mx)}</text>
        <text x="${W - PR + 12}" y="${Y(my) + 15}" text-anchor="end" font-size="11.5" font-weight="650" fill="var(--text-muted)">${tenY} trung vị ${fy(my)}</text>`;

  // điểm — cùng một cỡ. Đổi cỡ theo vốn hoá chỉ thêm một chiều mà không ai đọc.
  const nh = co.map(d => ({ d, x: X(d.x), y: Y(d.y) - 11, tren: true })).sort((a, b) => a.y - b.y);
  for (let k = 1; k < nh.length; k++) {
    const t = nh[k], p = nh[k - 1];
    if (Math.abs(t.x - p.x) < 40 && t.y - p.y < 15) { t.y = Y(t.d.y) + 18; t.tren = false; }
  }
  co.forEach(d => {
    const mau = d.blocked ? '--critical' : (reHon(d) ? '--good' : '--text-muted');
    s += `<circle cx="${X(d.x)}" cy="${Y(d.y)}" r="5.5" fill="var(${mau})" style="cursor:pointer"
           onclick="openChart('${d.sym}')"><title>${d.sym} — ${esc(d.ten)}
${tenX}: ${fx(d.x)}   ${tenY}: ${fy(d.y)}${d.tim ? '\nĐèn tím — ' + esc(d.tim_vi || '') : ''}${d.blocked ? '\nCổng rủi ro CHẶN: ' + esc(d.block || '') : ''}</title></circle>`;
  });
  nh.forEach(t => {
    const mau = t.d.blocked ? '--critical' : (reHon(t.d) ? '--good' : '--text-secondary');
    s += `<text x="${t.x}" y="${Math.max(PT - 2, Math.min(t.y, H - PB + 2))}" text-anchor="middle" font-size="13.5"
           font-weight="780" fill="var(${mau})" stroke="var(--surface-1)" stroke-width="3.2" paint-order="stroke"
           stroke-linejoin="round" style="cursor:pointer" onclick="openChart('${t.d.sym}')">${t.d.sym}${t.d.tim ? ' ●' : ''}</text>`;
  });
  host.innerHTML = s + '</svg>';
}

/* ---------- 2. THANH KHOẢNG — mỗi mã một dòng ---------- */
let _ngSap = 'y';     // y | re | dat

function nganhThanhKhoang(host, ds, cf) {
  const co = ds.filter(d => so(d.x) && so(d.lo) && so(d.hi));
  if (!co.length) { host.innerHTML = '<p class="muted" style="margin:0">Chưa có khoảng lịch sử cho nhóm này.</p>'; return; }
  const mx = _trungVi(ds.map(d => d.x));
  const fx = cf.x === 'pe' ? (v => v.toFixed(1)) : (v => v.toFixed(2).replace('.', ','));
  const tenX = cf.x === 'pe' ? 'P/E' : 'P/B';
  const tenY = cf.y === 'roe' ? 'ROE' : 'LNST YoY';
  const nq = Math.max(...co.map(d => d.nq));
  const rs = [...co].sort((a, b) =>
    _ngSap === 're' ? a.x - b.x : _ngSap === 'dat' ? b.x - a.x : (b.y ?? -1e9) - (a.y ?? -1e9));

  const vitri = d => d.vt == null ? '' :
    d.vt <= 0.15 ? '<span style="color:var(--good)">sát đáy khoảng</span>'
    : d.vt >= 0.85 ? '<span style="color:var(--critical)">sát đỉnh khoảng</span>'
    : d.vt <= 0.40 ? 'nửa dưới khoảng' : d.vt >= 0.60 ? 'nửa trên khoảng' : 'giữa khoảng';

  host.innerHTML = rs.map(d => {
    const p = Math.max(0, Math.min(1, d.vt ?? 0)) * 100;
    const pm = (so(mx) && d.hi > d.lo) ? Math.max(0, Math.min(1, (mx - d.lo) / (d.hi - d.lo))) * 100 : null;
    return `<div class="ngrow" onclick="openChart('${d.sym}')" title="${esc(d.ten)}">
      <div class="ngsym"><b>${d.sym}</b>${d.tim ? '<span style="color:var(--s7)"> ●</span>' : ''}${
        d.blocked ? '<span class="pill DO" style="font-size:9.5px;margin-left:4px">chặn</span>' : ''}
        <span class="ngroe">${tenY} ${so(d.y) ? (d.y >= 0 ? '' : '−') + Math.abs(d.y).toFixed(1) + '%' : '—'}</span></div>
      <div class="ngbar">
        <div class="ngtrack"></div>
        ${pm == null ? '' : `<i class="ngmed" style="left:${pm.toFixed(1)}%" title="trung vị ngành ${fx(mx)}"></i>`}
        <i class="ngdot" style="left:${p.toFixed(1)}%"></i>
        <span class="nglo">${fx(d.lo)}</span><span class="nghi">${fx(d.hi)}</span>
      </div>
      <div class="ngnow"><b>${fx(d.x)}</b><span>${vitri(d)}</span></div>
    </div>`;
  }).join('') +
  `<p class="muted" style="margin:12px 0 0;font-size:12px">Mỗi thanh chạy từ <b style="color:var(--good)">${tenX} thấp nhất</b>
   tới <b style="color:var(--critical)">${tenX} cao nhất</b> của chính mã đó trong <b>${nq} quý</b> gần nhất; chấm đen là ${tenX} hiện tại,
   vạch mảnh là trung vị ngành ${fx(mx)}. Đây là so mã với <b>chính nó</b> — khác hẳn biểu đồ trên, nơi so mã với <b>hàng xóm cùng ngành</b>.
   <b>Sát đáy khoảng không có nghĩa là rẻ</b>: cả ngành cùng rơi thì mã nào cũng sát đáy.</p>`;
}

/* ---------- trang ---------- */
let _nganhId = null;

function pageNganh(root) {
  const cf = NGANH.find(x => x.id === _nganhId) || NGANH[0];
  _nganhId = cf.id;
  const ds = nganhSoLieu(cf).sort((a, b) => (b.mktcap || 0) - (a.mktcap || 0));
  const co = ds.filter(d => so(d.x) && so(d.y));
  const mx = _trungVi(co.map(d => d.x)), my = _trungVi(co.map(d => d.y));
  const fx = cf.x === 'pe' ? (v => v.toFixed(1)) : (v => v.toFixed(2).replace('.', ','));
  const tenX = cf.x === 'pe' ? 'P/E' : 'P/B';
  const tenY = cf.y === 'roe' ? 'ROE' : 'LNST YoY';
  const nq = Math.max(...ds.map(d => d.nq), 0);
  const dao = co.filter(d => d.x <= mx && d.y >= my);

  root.innerHTML = `
  <h1>So sánh trong ngành</h1>
  <p class="lead">Một mã chỉ <b>đắt</b> hay <b>rẻ</b> khi đặt cạnh mã cùng ngành. Hai khối dưới đây trả lời hai câu khác nhau —
  <b>so với hàng xóm</b>, và <b>so với chính nó</b>. Đừng gộp hai câu đó làm một.</p>

  <div class="seg" id="ngSeg" style="margin-bottom:14px"></div>

  ${ds.length < 6 ? `<div class="note" style="border-color:var(--critical);background:color-mix(in srgb,var(--critical) 9%,transparent)">
    <b>Mẫu quá nhỏ — chỉ ${ds.length} mã.</b> Trung vị của ${ds.length} mã không phải một phân phối, nó chỉ là con số nằm giữa ${ds.length} con số.
    Nhìn tương quan thì được; kết luận "rẻ hơn ngành" thì <b>không</b>. Vũ trụ giao dịch là TOP ${D.universe_n} mã thanh khoản nhất nên nhóm này vốn chỉ có bấy nhiêu.</div>` : ''}
  ${cf.thieu ? `<div class="note" style="margin-top:12px">${cf.thieu}</div>` : ''}

  <h2 style="margin-top:22px">${tenY} so với ${tenX} hiện tại</h2>
  <p class="muted" style="margin-top:0">Vùng xanh là góc đáng đào: <b>${tenX} dưới trung vị</b> mà <b>${tenY} trên trung vị</b> —
  trả ít hơn hàng xóm cho một doanh nghiệp làm tốt hơn hàng xóm. Bấm vào mã để mở Chi tiết mã.</p>
  <div class="card"><div id="ngChart"></div></div>
  ${dao.length ? `<div class="note info" style="margin-top:12px"><b>${dao.length}/${co.length} mã đang nằm trong vùng xanh:</b>
    ${dao.sort((a, b) => b.y - a.y).map(d => `<b>${d.sym}</b> (${tenX} ${fx(d.x)} · ${tenY} ${d.y.toFixed(1)}%)`).join(' · ')}.
    Đây là <b>chỗ để bắt đầu đọc</b>, không phải danh sách mua — hệ thống vẫn chỉ vào lệnh khi mã qua đủ chín lớp.</div>`
    : `<div class="note" style="margin-top:12px">Không mã nào nằm trong vùng xanh — trong nhóm này, mã nào ${tenY} cao thì ${tenX} cũng cao. Thị trường đang định giá khá nhất quán.</div>`}

  <h2 style="margin-top:26px">Khoảng ${tenX} ${nq} quý</h2>
  <p class="muted" style="margin-top:0">Mỗi mã so với <b>chính nó</b>: thanh chạy từ ${tenX} thấp nhất tới cao nhất trong ${nq} quý gần nhất, chấm đen là hiện tại.</p>
  <div class="seg" id="ngSort" style="margin-bottom:10px"></div>
  <div class="card" id="ngKhoang"></div>

  <details style="margin-top:22px">
    <summary class="muted" style="cursor:pointer">Bảng số đầy đủ (${ds.length} mã)</summary>
    <div class="card tblwrap" style="margin-top:10px"><table id="ngTbl"><thead><tr>
      <th data-k="sym">Mã</th><th data-k="ten">Doanh nghiệp</th>
      <th data-k="mktcap" style="text-align:right">Vốn hoá</th>
      <th data-k="x" style="text-align:right">${tenX}</th>
      <th data-k="lo" style="text-align:right">Thấp ${nq}q</th>
      <th data-k="hi" style="text-align:right">Cao ${nq}q</th>
      <th data-k="y" style="text-align:right">${tenY}</th>
      <th data-k="rev_yoy" style="text-align:right">DThu YoY</th>
      <th data-k="x" style="text-align:right">So trung vị</th>
      <th>Ghi chú</th></tr></thead><tbody id="ngBody"></tbody></table></div>
  </details>

  <div class="note" style="margin-top:18px"><b>Vì sao ngành này dùng ${tenX} ghép với ${tenY}.</b> ${cf.vi}
    ${cf.tam ? '<br><br><b style="color:var(--warn)">Ngành này đang dùng thước TẠM</b> — đọc băng ở trên trước khi kết luận gì.' : ''}</div>`;

  const seg = document.getElementById('ngSeg');
  NGANH.forEach(x => {
    const b = el('button', x.id === cf.id ? 'on' : '', x.ten);
    b.onclick = () => { _nganhId = x.id; root.innerHTML = ''; pageNganh(root); };
    seg.appendChild(b);
  });
  const ss = document.getElementById('ngSort');
  [['y', 'Theo ' + tenY], ['re', 'Rẻ nhất trước'], ['dat', 'Đắt nhất trước']].forEach(([k, lab]) => {
    const b = el('button', _ngSap === k ? 'on' : '', lab);
    b.onclick = () => { _ngSap = k; ss.querySelectorAll('button').forEach(z => z.classList.remove('on')); b.classList.add('on');
      nganhThanhKhoang(document.getElementById('ngKhoang'), ds, cf); };
    ss.appendChild(b);
  });

  nganhPhanTan(document.getElementById('ngChart'), ds, cf);
  nganhThanhKhoang(document.getElementById('ngKhoang'), ds, cf);

  let sk = 'mktcap', sd = -1;
  const rend = () => {
    const rs = [...ds].sort((a, b) => {
      const p = a[sk], q2 = b[sk];
      if (typeof p === 'string') return p.localeCompare(q2) * sd;
      return ((p ?? -1e18) > (q2 ?? -1e18) ? 1 : (p ?? -1e18) < (q2 ?? -1e18) ? -1 : 0) * sd;
    });
    document.getElementById('ngBody').innerHTML = rs.map(d => {
      const dx = (so(d.x) && so(mx)) ? d.x / mx - 1 : null;
      const ghi = [];
      if (d.blocked) ghi.push(`<span class="pill DO">${esc(d.block || 'chặn')}</span>`);
      if (d.tim) ghi.push(`<span title="${esc(d.tim_vi || '')}" style="color:var(--s7)">● đèn tím</span>`);
      if (!so(d.x)) ghi.push(`<span class="muted">không có ${tenX}${cf.x === 'pe' ? ' (đang lỗ)' : ''}</span>`);
      return `<tr>
        <td class="sym" style="cursor:pointer" onclick="openChart('${d.sym}')">${d.sym}</td>
        <td class="muted" style="font-size:13px">${esc((d.ten || '').slice(0, 30))}</td>
        <td style="text-align:right">${d.mktcap ? num(d.mktcap, 0) : '—'}</td>
        <td style="text-align:right;font-weight:650;color:var(--text-primary)">${so(d.x) ? fx(d.x) : '—'}</td>
        <td style="text-align:right" class="muted">${so(d.lo) ? fx(d.lo) : '—'}</td>
        <td style="text-align:right" class="muted">${so(d.hi) ? fx(d.hi) : '—'}</td>
        <td style="text-align:right;font-weight:640" class="${so(d.y) ? cls(d.y) : ''}">${so(d.y) ? (d.y >= 0 ? '+' : '') + d.y.toFixed(1) + '%' : '—'}</td>
        <td style="text-align:right" class="${so(d.rev_yoy) ? cls(d.rev_yoy) : ''}">${so(d.rev_yoy) ? (d.rev_yoy >= 0 ? '+' : '') + d.rev_yoy.toFixed(1) + '%' : '—'}</td>
        <td style="text-align:right" class="${dx == null ? 'muted' : (dx <= 0 ? 'pos' : 'neg')}">${dx == null ? '—' : (dx >= 0 ? '+' : '') + (dx * 100).toFixed(0) + '%'}</td>
        <td>${ghi.join(' ') || '<span class="muted">—</span>'}</td></tr>`;
    }).join('');
  };
  document.querySelectorAll('#ngTbl thead th').forEach(th => th.onclick = () => {
    const k = th.dataset.k; if (!k) return; sd = (k === sk) ? -sd : -1; sk = k; rend();
  });
  rend();
}

/* ============================================================================
   ĐỒNG BỘ MÃ giữa THANH TRA CỨU và TRANG CHI TIẾT MÃ  (sửa 18/09/2026)

   Lỗi: gõ "VND" vào thanh tra cứu trên đỉnh thì thanh đó đổi, nhưng bốn biểu đồ
   bên dưới vẫn là của mã cũ (BSR). Cuộn xuống một đoạn là ô nhập riêng của trang
   khuất đi — trên màn chỉ còn chữ VND, không cách nào biết biểu đồ là mã khác.
   Đúng họ lỗi đã ghi trong sổ: "nhìn như FPT mà số là của ORS".

   Hai ô nhập trên cùng một màn hình mà không nói chuyện với nhau là cái bẫy, dù
   mỗi ô tự nó chạy đúng. Từ giờ chọn mã ở đâu cũng đổi cả hai.

   Khai báo bằng `function` nên được kéo lên đầu phạm vi — p9.js và p10.js nạp
   TRƯỚC file này vẫn gọi được lúc chạy.
   ========================================================================== */
// Cờ chặn gọi vòng ĐẶT NGAY TRÊN HÀM, không dùng `let` ở phạm vi ngoài.
// Lý do đã vấp: IIFE thanh tra cứu trong p10.js chạy NGAY LÚC NẠP và gọi hàm này,
// tức trước khi p16.js (nạp sau) kịp khởi tạo biến — `let` lúc đó còn trong vùng
// chết, chạm vào là ném ReferenceError và chết cả trang. Thuộc tính của hàm thì
// hàm được kéo lên đầu phạm vi nên lúc nào cũng có.
function nsiChonMa(sym, tu) {
  if (!sym || nsiChonMa._dang) return;      // chặn gọi vòng: thanh -> trang -> thanh
  // `typeof x` KHÔNG cứu được biến let/const đang trong vùng chết — chạm vào là
  // ném ReferenceError. Mà hàm này bị gọi lúc p10.js nạp, tức TRƯỚC khi p7.js
  // khai báo `secs` và p9.js khai báo `_chartSym`. Nên mọi lần đọc biến của file
  // khác đều phải bọc try/catch. Đã vấp đúng chỗ này hai lần trong một buổi.
  const doc = f => { try { return f(); } catch (e) { return null; } };
  nsiChonMa._dang = true;
  try {
    if (tu !== 'thanh' && typeof window._lkShow === 'function') {
      try { document.getElementById('lkIn').value = sym; } catch (e) {}
      try { window._lkShow(sym); } catch (e) {}
    }
    if (tu !== 'trang') {
      const S  = doc(() => secs);
      const LK = doc(() => (D.lookup || {}));
      const cu = doc(() => _chartSym);
      if (S && S.bieudo && S.bieudo.rendered && LK && LK[sym] && cu !== sym) {
        try { _chartSym = sym; veLaiTrang('bieudo'); } catch (e) {}
      }
    }
  } finally { nsiChonMa._dang = false; }
}
