/* ============================================================================
   CHẨN ĐOÁN & KIỂM TOÁN (trang quản trị, ẩn khỏi menu) — audit 23/09/2026
   Nguồn: D.data_health (data/data_health.json), LIVE.server.source_health
   (live.json), D.audit (evidence/audit_summary.json). Chỉ đọc, không tính lại luật.
   Biểu đồ: SVG thuần, viewBox co giãn theo chiều rộng, KHÔNG dùng
   preserveAspectRatio="none" (chữ không bị bóp méo).
   ========================================================================== */
function _pc1(x) { return x == null ? '—' : (x * 100).toFixed(1).replace('.', ',') + '%'; }
function _n2(x) { return x == null ? '—' : String(x).replace('.', ','); }

function _barsSVG(rows, key, opt) {
  // rows: [{name, [key]}], horizontal bars, labels outside the bars
  opt = opt || {};
  const W = 640, rh = 22, pad = 190, H = rows.length * rh + 8;
  const vals = rows.map(r => +r[key] || 0);
  const mx = Math.max(...vals.map(Math.abs), 1e-9);
  const sc = v => (W - pad - 70) * Math.abs(v) / mx;
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;height:auto" role="img">
    ${rows.map((r, i) => {
      const v = +r[key] || 0, y = i * rh + 4, hl = opt.hl && opt.hl(r);
      return `<text x="${pad - 8}" y="${y + 15}" text-anchor="end" font-size="12" fill="currentColor">${esc(r.name)}</text>
        <rect x="${pad}" y="${y + 3}" width="${sc(v)}" height="${rh - 8}" rx="3"
          fill="${hl ? 'var(--s1)' : (v < 0 ? 'var(--bad)' : 'var(--s2)')}" opacity="${hl ? 1 : .75}"></rect>
        <text x="${pad + sc(v) + 6}" y="${y + 15}" font-size="12" fill="currentColor">${opt.fmt ? opt.fmt(v) : v}</text>`;
    }).join('')}</svg>`;
}

function _tbl(rows, cols) {
  return `<div class="card tblwrap"><table><thead><tr>${cols.map(c =>
    `<th style="text-align:${c.r ? 'right' : 'left'}">${c.t}</th>`).join('')}</tr></thead><tbody>
    ${rows.map(r => `<tr>${cols.map(c => `<td style="text-align:${c.r ? 'right' : 'left'}"${
      c.cls ? ` class="${c.cls(r)}"` : ''}>${c.f(r)}</td>`).join('')}</tr>`).join('')}
    </tbody></table></div>`;
}

const _MCOLS = [
  { t: 'Biến thể', f: r => esc(r.name) },
  { t: 'Tổng LN', r: 1, f: r => _pc1(r.ret) },
  { t: 'MaxDD', r: 1, f: r => _pc1(r.dd) },
  { t: 'PF', r: 1, f: r => _n2(r.pf) },
  { t: 'Sharpe', r: 1, f: r => _n2(r.sh) },
  { t: 'Deal', r: 1, f: r => r.deals },
  { t: '2019–22', r: 1, f: r => _pc1(r.r1) },
  { t: '2023–26', r: 1, f: r => _pc1(r.r2) },
];

function pageChanDoan(root) {
  const H = D.data_health || {};
  const A = D.audit || null;
  const sv = (typeof LIVE !== 'undefined' && LIVE.server) || {};
  const sh = sv.source_health || null;
  const src = Object.keys(H).map(k => Object.assign({ key: k }, H[k]));
  const st = s => s === 'OK' ? 'pos' : (s ? 'neg' : 'muted');

  let h = `<h1>Chẩn đoán dữ liệu &amp; kiểm toán</h1>
  <p class="lead">Trang quản trị. <b>Không có tín hiệu</b> và <b>thiếu dữ liệu</b> là hai chuyện khác nhau —
  trang này cho biết mỗi nguồn đang ở trạng thái nào. Cấu hình PROD đang chạy:
  <code>${esc((D.cfg_prod || {}).prod_config_hash || '?')}</code>.</p>

  <h2>Nguồn dữ liệu (bản dựng tối)</h2>
  ${src.length ? _tbl(src, [
    { t: 'Nguồn', f: r => `<b>${esc(r.key)}</b><div class="muted" style="font-size:12px">${esc(r.source || '')}</div>` },
    { t: 'Trạng thái', f: r => `<b>${esc(r.status || '—')}</b>`, cls: r => st(r.status) },
    { t: 'Độ phủ', r: 1, f: r => _pc1(r.coverage) },
    { t: 'Phiên mới nhất', f: r => esc(r.latest_session || r.freshness || '—') },
    { t: 'Thiếu', r: 1, f: r => r.missing_is != null ? `KQKD ${r.missing_is} · LCTT ${r.missing_cf}` : (r.missing_listed ? r.missing_listed.length : '—') },
    { t: 'Thành công gần nhất', f: r => esc((r.last_success || '').replace('T', ' ').slice(0, 16)) },
    { t: 'Lỗi gần nhất', f: r => `<span class="muted" style="font-size:12px">${esc(String(r.last_error || (r.http_errors ? r.http_errors + ' lỗi HTTP' : '')).slice(0, 80))}</span>` },
  ]) : '<div class="note">Bản dựng này chưa ghi data/data_health.json.</div>'}

  <h2>Bộ quét trong phiên (live.json)</h2>
  ${sh ? `<div class="grid kpis">
      ${kpi('Trạng thái', sv.status || '—', sv.session || '', sv.status === 'OK' ? 'pos' : 'neg')}
      ${kpi('Độ phủ giá', _pc1(sh.coverage), `${sh.scanned}/${sh.expected} mã`)}
      ${kpi('Có dòng tiền (Đ.kiện 9)', _pc1(sh.ordimb_coverage), 'BuyCount/SellCount tại lần quét')}
      ${kpi('Đặc tả tín hiệu', sh.spec_ok ? 'khớp' : 'THIẾU', sv.prod_config_hash || '', sh.spec_ok ? 'pos' : 'neg')}
    </div>
    ${(sh.missing || []).length ? `<div class="note">Mã chưa lấy được: ${esc(sh.missing.slice(0, 60).join(' '))}</div>` : ''}`
    : '<div class="note">Chưa nạp live.json (mở trang trên web thật để xem).</div>'}`;

  if (!A) { root.innerHTML = h + '<div class="note">Thiếu evidence/audit_summary.json.</div>'; return; }
  const b0 = A.baseline0 || {};
  const cur = (A.fixes || []).find(x => x.name === 'max_n_in_loop') || {};
  h += `
  <h2>BASELINE_0 và PROD sau kiểm toán (trùng từng lệnh)</h2>
  <div class="grid kpis">
    ${kpi('BASELINE_0', _pc1(b0.ret), `DD ${(b0.dd*100).toFixed(2).replace('.',',')}% · PF ${_n2(b0.pf)} · Sharpe ${_n2(b0.sharpe)} · ${b0.deals} deal`)}
    ${kpi('PROD mới', _pc1(cur.ret), `DD ${((cur.dd||0)*100).toFixed(2).replace('.',',')}% · PF ${_n2(cur.pf)} · Sharpe ${_n2(cur.sh)} · ${cur.deals} deal`)}
    ${kpi('Pyramid', 'Giữ luật cũ', 'trần ngành chỉ áp cho lệnh mới; bắt áp cho lệnh nhồi: +579,1%')}
  </div>
  ${_tbl(A.fixes || [], _MCOLS)}

  <h2>Parity live ↔ backtest</h2>
  <div class="grid kpis">
    ${kpi('Bản cũ: bắt được', `${A.parity_old.recall}/${A.parity_old.entries}`, 'lệnh của bộ máy mà live báo MUA')}
    ${kpi('Bản cũ: MUA sai 2023–26', A.parity_old.false_mua_2023_2026, `${A.parity_old.false_mua_cond9_fail} lệnh trượt Điều kiện 9`, 'neg')}
    ${A.parity_new ? kpi('Bản mới (signal_spec)', _pc1(A.parity_new.agree), `${A.parity_new.both} khớp · ${A.parity_new.engine_only} chỉ engine · ${A.parity_new.live_only} chỉ live`, 'pos') : ''}
  </div>

  <h2>Khớp lệnh — mua được ở đâu?</h2>
  ${_barsSVG(A.execution || [], 'ret', { fmt: _pc1, hl: r => r.name.startsWith('CUR') })}
  ${_tbl(A.execution || [], _MCOLS)}
  <h2>Bỏ lỡ lệnh thắng lớn nhất</h2>
  ${_tbl(A.forced_miss || [], _MCOLS)}

  <h2>Cổng CFO — HARD / OFF / WARN / SECTOR / REPEAT</h2>
  ${_barsSVG((A.cfo || []).filter(r => !/slip|next/.test(r.name)), 'ret', { fmt: _pc1, hl: r => r.name === 'CFO_HARD' })}
  ${_tbl(A.cfo || [], _MCOLS)}
  <div class="note">Nhóm chỉ bị chặn vì CFO (${A.cfo_cohort.n} deal): tỷ lệ thắng ${_pc1(A.cfo_cohort.winrate)},
    PF ${_n2(A.cfo_cohort.pf)}, trung vị ${_n2(A.cfo_cohort.median)}%, lệnh lỗ nặng nhất ${_n2(A.cfo_cohort.worst)}%,
    ${_pc1(A.cfo_cohort.top1_share)} lãi gộp nằm ở 1 deal. <b>Quyết định: giữ CFO_HARD.</b></div>

  <h2>Xếp hạng khi nhiều mã cùng nổ</h2>
  ${_tbl(A.ranking || [], _MCOLS)}

  <h2>Tập trung lợi nhuận</h2>
  ${_barsSVG(Object.entries(A.concentration || {}).map(([k, v]) => ({ name: k.replace('top', 'Top '), v })), 'v', { fmt: _pc1 })}

  <h2>Sụt giảm — block bootstrap theo lợi suất ngày</h2>
  ${_tbl(Object.entries(A.bootstrap || {}).filter(([k]) => k.startsWith('block')).map(([k, v]) => Object.assign({ k }, v)), [
    { t: 'Khối', f: r => r.k.replace('block', '') + ' phiên' },
    { t: 'p50', r: 1, f: r => _pc1(r.p50) }, { t: 'p75', r: 1, f: r => _pc1(r.p75) },
    { t: 'p90', r: 1, f: r => _pc1(r.p90) }, { t: 'p95', r: 1, f: r => _pc1(r.p95) },
    { t: 'p99', r: 1, f: r => _pc1(r.p99) }, { t: 'Tệ nhất', r: 1, f: r => _pc1(r.worst) },
    { t: 'P(DD>15%)', r: 1, f: r => _pc1(r.P_dd_gt_15) }, { t: 'P(DD>20%)', r: 1, f: r => _pc1(r.P_dd_gt_20) },
    { t: 'P(DD>25%)', r: 1, f: r => _pc1(r.P_dd_gt_25) }, { t: 'P(DD>30%)', r: 1, f: r => _pc1(r.P_dd_gt_30) },
  ])}

  <h2>Điều kiện 9 có quan sát được trong phiên không?</h2>
  ${(A.cond9_obs || []).length ? _tbl(A.cond9_obs, [
    { t: 'Thời điểm', f: r => esc(r.at) },
    { t: 'Nhận', r: 1, f: r => `${r.received}/${r.expected}` },
    { t: 'Có BuyCount', r: 1, f: r => r.has_BuyCount },
    { t: 'Có SellCount', r: 1, f: r => r.has_SellCount },
    { t: 'OrdImb tính được', r: 1, f: r => `${r.ordimb_avail} (${_pc1(r.ordimb_cov)})` },
  ]) : '<div class="note">Chưa có số đo trong phiên. live_scan.py ghi obs/flow_YYYY-MM.jsonl mỗi lần quét.</div>'}`;
  root.innerHTML = h;
}
