/* ============================================================================
   LỆNH BÁN — VIỆC TỪNG MÃ ĐANG CẦM (03/10/2026, anh Sơn)
   Mỗi tối máy chủ tính sẵn cho phiên tới (exit_rules.ke_hoach_ban, đúng luật thoát
   của hệ thống): giá ĐÓNG CỬA bao nhiêu thì BÁN HẾT ATC. Trong phiên trang so giá
   real-time VPS (15 giây/lần) với ngưỡng đó; giá xuống dưới ngưỡng thì kêu chuông.
   Mã trong Sổ tay của anh Sơn chỉ hiện ở trang quản trị.
   ========================================================================== */
const LB = { keu: new Set() };

function phienKeTiep(d) {               // ngày làm việc kế tiếp sau d (bỏ T7, CN)
  const t = new Date(d + 'T00:00:00Z');
  do { t.setUTCDate(t.getUTCDate() + 1); } while (t.getUTCDay() === 0 || t.getUTCDay() === 6);
  return t.toISOString().slice(0, 10);
}

function dongKeHoach() {
  const out = [], co = new Set();
  const them = (k, nguon, sh) => { if (!k || co.has(nguon + k.sym)) return; co.add(nguon + k.sym); out.push(Object.assign({ nguon, sh }, k)); };
  (((D.book || {}).positions) || []).forEach(p => them(p.ke_hoach, 'he', p.shares));
  (D.open_positions || []).forEach(p => them(p.ke_hoach, 'he', p.shares));
  if (typeof laQuanTri === 'function' && laQuanTri()) (D.ke_hoach_so_tay || []).forEach(k => them(k, 'sotay', k.sh));
  // mã sổ giao dịch thực tế mà sổ hệ thống không có: lấy dòng luật thoát của máy chủ
  const coMa = new Set(out.map(x => x.sym));
  (((typeof LIVE !== 'undefined' && LIVE.server) || {}).exits || []).forEach(x => {
    if (coMa.has(x.sym)) return;
    out.push({ sym: x.sym, nguon: 'so', server: x, gia_von: null, viec: x.exit_reason ? 'BAN' : 'GIU',
               ly_do: x.exit_reason || x.pending_exit || null, nguong: null, moc: {} });
  });
  return out;
}

function trangThaiBan(k) {
  const p = giaMoiNhat(k.sym);
  const t = (typeof gioVN === 'function') ? gioVN() : new Date();
  const ph = t.getHours() * 60 + t.getMinutes();
  const mo = (typeof phienMo === 'function') && phienMo();
  const atc = mo && ph >= 14 * 60 + 15;
  const so = v => v == null ? '—' : (+v).toFixed(2).replace('.', ',');
  const ly = k.ly_do ? String(k.ly_do) : '';
  let viec, mau = '--text-muted', duoi = false;
  if (k.viec === 'BAN') {
    viec = `BÁN HẾT ATC${ly ? ' — ' + ly : ''}`; mau = '--critical'; duoi = true;
  } else if (k.viec === 'CHUA_BAN_DUOC') {
    viec = `GIỮ — chưa bán được (bán được từ phiên thứ ${k.sell_from} sau ngày mua)${ly ? ' · ' + ly : ''}`;
  } else if (k.viec === 'NGUONG' && k.nguong != null) {
    duoi = p != null && p <= k.nguong;
    if (duoi) {
      viec = atc ? `BÁN HẾT ATC NGAY — giá ${so(p)} dưới ngưỡng ${so(k.nguong)} (${ly})`
                 : `⚠ GIÁ ĐANG DƯỚI NGƯỠNG — đóng cửa ≤ ${so(k.nguong)} thì BÁN HẾT ATC (${ly})`;
      mau = '--critical';
    } else {
      const cach = p ? (k.nguong / p - 1) * 100 : null;
      viec = `GIỮ — đóng cửa ≤ ${so(k.nguong)} thì BÁN HẾT ATC${cach != null ? ` (cách ${cach.toFixed(1).replace('.', ',')}%)` : ''} · ${ly}`;
      mau = cach != null && cach > -3 ? '--warn' : '--text-secondary';
    }
  } else if (k.server) {
    viec = k.server.action || 'GIỮ'; mau = k.server.exit_reason ? '--critical' : '--text-secondary';
    duoi = !!k.server.exit_reason;
  } else viec = 'GIỮ';
  const von = k.gia_von;
  const lai = (p != null && von) ? (p * (1 - (typeof PHI_BAN !== 'undefined' ? PHI_BAN : 0.0025)) / von - 1) * 100 : (k.server ? k.server.gain : null);
  return { p, lai, viec, mau, duoi };
}

function bangLenhBan() {
  const ds = dongKeHoach();
  const phien = D.asof ? phienKeTiep(D.asof) : '';
  const so = v => v == null ? '—' : (+v).toFixed(2).replace('.', ',');
  const pc = v => v == null ? '—' : (v >= 0 ? '+' : '') + (+v).toFixed(1).replace('.', ',') + '%';
  if (!ds.length) return `<h2>🔻 Lệnh bán${phien ? ' — phiên ' + ddmm(phien) : ''}</h2>
    <div class="card"><p style="margin:0">Không cầm mã nào — không có lệnh bán.</p></div>`;
  const rows = ds.map(k => Object.assign({ k }, trangThaiBan(k)))
    .sort((a, b) => (b.duoi - a.duoi) || String(a.k.sym).localeCompare(b.k.sym));
  const nhan = { he: 'Hệ thống', so: 'Sổ thực tế', sotay: 'Sổ tay' };
  const moc = m => {
    const a = [];
    if (m.khoa_lai != null) a.push(`khoá lãi ${so(m.khoa_lai)}`);
    if (m.momentum != null) a.push(`cần lãi 1%: ${so(m.momentum)}`);
    if (m.cat_lo != null) a.push(`cắt lỗ ${so(m.cat_lo)}`);
    if (m.ma10 != null) a.push(`TB10 ${so(m.ma10)}`);
    if (m.ma30 != null) a.push(`TB30 ${so(m.ma30)}`);
    return a.join(' · ');
  };
  return `<h2>🔻 Lệnh bán — phiên ${ddmm(phien)}</h2>
    <div class="card tblwrap lban"><table><thead><tr>
      <th>Mã</th><th class="r">Giá vốn</th><th class="r">Giá hiện tại</th><th class="r">Lãi/lỗ</th>
      <th class="r">Đỉnh lãi</th><th class="r">Ngưỡng bán</th><th>Việc hôm nay</th></tr></thead><tbody>
      ${rows.map(x => `<tr class="${x.duoi ? 'lbdo' : ''}">
        <td class="sym">${esc(x.k.sym)}<div class="lbn ${x.k.nguon}">${nhan[x.k.nguon] || ''}</div></td>
        <td class="r">${so(x.k.gia_von)}</td>
        <td class="r"><b>${so(x.p)}</b></td>
        <td class="r ${x.lai == null ? '' : x.lai >= 0 ? 'pos' : 'neg'}">${pc(x.lai)}</td>
        <td class="r">${x.k.peak != null ? pc(x.k.peak) : '—'}</td>
        <td class="r"><b>${x.k.nguong != null ? '≤ ' + so(x.k.nguong) : (x.k.viec === 'BAN' ? 'mọi giá' : '—')}</b></td>
        <td style="white-space:normal;min-width:280px"><div style="color:var(${x.mau});font-weight:650">${esc(x.viec)}</div>
          ${x.k.moc && moc(x.k.moc) ? `<div class="muted" style="font-size:12px">${moc(x.k.moc)}</div>` : ''}</td></tr>`).join('')}
    </tbody></table></div>`;
}

/* chuông: giá real-time xuống dưới ngưỡng (hoặc mã phải bán hôm nay) -> kêu một lần mỗi mã mỗi phiên */
function kiemTraNguongBan() {
  if (typeof phienMo !== 'function' || !phienMo() || typeof reoChuong !== 'function') return;
  const hom = (typeof gioVN === 'function' ? gioVN() : new Date()).toISOString().slice(0, 10);
  const moi = [];
  dongKeHoach().forEach(k => {
    if (k.nguon === 'so') return;                 // sổ thực tế: chuongBan() của máy chủ đã lo
    const s = trangThaiBan(k);
    const key = 'LB:' + k.nguon + ':' + k.sym + ':' + hom;
    if (s.duoi && !LB.keu.has(key)) { LB.keu.add(key); moi.push({ sym: k.sym, price: s.p == null ? '' : s.p.toFixed(2), viec: s.viec }); }
  });
  if (moi.length) reoChuong(moi, 'ban');
}
setInterval(kiemTraNguongBan, 15000);
