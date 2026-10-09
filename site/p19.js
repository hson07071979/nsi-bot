/* ============================================================================
   LỚP QUAN SÁT (R27A, 27/09/2026) — CHỈ ĐỂ ĐỌC, KHÔNG PHẢI TÍN HIỆU.
   1. Đường đi sau breakout của vị thế đang nắm (T+1/T+2/T+3/T+5, lãi, đỉnh, MFE/MAE,
      giữ trên giá breakout, đỉnh mới, Cond9) + nhãn MÔ TẢ. Nhãn không đổi "Việc cần làm".
   2. GẦN ĐẠT — thiếu 1 cổng (7/8) hoặc 2 cổng mềm khi giá ĐÃ NỔ (6/8, R29): danh sách theo dõi. Không phải MUA, không vào sổ,
      không kêu chuông. R25: nhóm này không có lợi thế ngoài mẫu bền.
   Dữ liệu: D.observability (produce2 → observability.py), cập nhật mỗi tối.
============================================================================ */
const OBS = () => (D.observability && !D.observability.error) ? D.observability : null;
const obsPct = (x, d = 1) => x == null ? '—' : (x >= 0 ? '+' : '') + (Math.round(x * 1000) / 10).toFixed(d).replace('.', ',') + '%';
const obsMau = { RUN_FAST: '--good', HEALTHY_TREND: '--good', STALL: '--warn', WEAK_BREAKOUT: '--critical', NEW: '--text-muted' };

function obsPath(sym, entry) {
  const O = OBS(); if (!O || !O.config.show_path) return null;
  return (O.paths || {})[sym + '|' + entry] || null;
}

/* Lãi THỰC NHẬN của vị thế — cùng số với Danh mục (giá real-time, trừ phí mua + phí bán).
   Trước đây ô này lấy gain_now của bộ máy (giá đóng cửa tối qua, chưa trừ phí bán), nên
   BVH 09/10/2026 hiện +14,4% trong khi Danh mục hiện +12,5%. */
function obsLaiTN(sym, p) {
  try {
    const v = (typeof danhMuc === 'function' ? danhMuc() : []).find(x => x.sym === sym && x.pnl != null);
    if (v) return { v: v.pnl / 100, nhan: 'Lãi thực nhận (giá hiện tại)' };
  } catch (e) {}
  const g = p.gain_now;
  return { v: g == null ? null : (1 + g) * (1 - (typeof PHI_BAN !== 'undefined' ? PHI_BAN : 0.0025)) - 1,
           nhan: 'Lãi thực nhận (đóng cửa)' };
}

function obsPathCard(sym, entry, ten) {
  const p = obsPath(sym, entry); if (!p) return '';
  const co = x => x == null ? '—' : (x ? 'CÓ' : 'KHÔNG');
  const c9 = p.cond9_confirmed == null ? '—' : (p.cond9_confirmed ? 'ĐÃ XÁC NHẬN' : '<span style="color:var(--critical)">TRƯỢT</span>');
  const lb = p.diagnostic_label;
  const o = (k, v, cls) => `<div style="display:flex;justify-content:space-between;gap:10px"><span class="muted">${k}</span><b class="${cls || ''}">${v}</b></div>`;
  return `<div class="card" style="min-width:250px;flex:1 1 260px">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px">
      <b style="font-size:16px">${esc(sym)}</b>${ten ? `<span class="muted" style="font-size:12px">${esc(ten)}</span>` : ''}
      <span class="vclpill" style="color:var(${obsMau[lb] || '--text-muted'});border-color:color-mix(in srgb,var(${obsMau[lb] || '--text-muted'}) 45%,transparent)"
        title="Nhãn mô tả — không phải lệnh">${esc(p.diagnostic_label_vi || lb)}</span></div>
    <div style="font-size:13px;line-height:1.55">
      ${o('Breakout', `${ddmm(p.breakout_date)} @ ${dec(p.breakout_price / 1000)}`)}
      ${o('Số phiên từ breakout', p.days_since_breakout)}
      ${(() => { const l = obsLaiTN(sym, p); return o(l.nhan, obsPct(l.v), cls(l.v || 0)); })()}
      ${o('Đỉnh lãi (đóng cửa, theo luật)', obsPct(p.peak_gain))}
      ${o('MFE / MAE từ lúc mua', `${obsPct(p.mfe_since_entry)} / ${obsPct(p.mae_since_entry)}`)}
      ${o('T+1 · T+2 · T+3 · T+5', [p.ret_t1, p.ret_t2, p.ret_t3, p.ret_t5].map(x => obsPct(x)).join(' · '))}
      ${o('Giữ trên giá breakout', co(p.above_breakout_close))}
      ${o('Đỉnh mới sau breakout', co(p.new_high_since_breakout) + (p.days_since_last_high != null ? ` <span class="muted" style="font-weight:400">(đỉnh cách ${p.days_since_last_high} phiên)</span>` : ''))}
      ${o('Cond9', c9)}
    </div>
    <div class="muted" style="font-size:11px;margin-top:6px">CHỈ QUAN SÁT</div>
  </div>`;
}

function obsPathSection(dm) {
  const O = OBS(); if (!O || !O.config.show_path) return '';
  const cards = (dm || []).filter(p => p.nguon === 'auto' || p.nguon === 'ghitien').map(p => obsPathCard(p.sym, p.entry, p.name)).filter(Boolean);
  if (!cards.length) return '';
  return `<h2>Đường đi sau breakout <span class="muted" style="font-size:13px;font-weight:400">— chỉ để quan sát, không phải lệnh</span></h2>
    <div style="display:flex;gap:12px;flex-wrap:wrap">${cards.join('')}</div>`;
}

/* ---------- 7/8 ---------- */
function obsGateText(g) {
  const O = OBS(), CPc = D.cfg_prod || {};
  const so = (x, d = 2) => x == null ? '—' : String((Math.round(x * 10 ** d) / 10 ** d)).replace('.', ',');
  const pc = x => x == null ? '—' : so(x * 100, 1) + '%';
  const lab = (O.gate_labels[g.gate] || g.gate).replace('{top_n}', CPc.top_n).replace('{vol_floor}', so(CPc.vol_floor, 1))
    .replace('{gtgd_bn}', Math.round((CPc.gtgd_min || 0) / 1e9)).replace('{volat_pct}', so((CPc.volat_min || 0) * 100, 1))
    .replace('{base_pct}', Math.round((CPc.base_range || 0) * 100)).replace('{score_floor}', CPc.score_floor);
  let v = '';
  if (g.gate === 'uni') v = `hạng ${g.actual} / cần ≤ ${g.threshold}` + (!g.ok ? ` · còn cách ${g.actual - g.threshold} bậc` : '');
  else if (g.gate === 'pct') v = `${pc(g.actual)} / cần ≥ ${pc(g.threshold)}` + (!g.ok ? ` · thiếu ${so(-g.gap * 100, 1)} điểm %` : '');
  else if (g.gate === 'vol') v = `${so(g.actual, 2)}× / cần ≥ ${so(g.threshold, 1)}×` + (!g.ok ? ` · thiếu ${so(-g.gap, 2)}×` : '');
  else if (g.gate === 'gtgd') v = `${so(g.actual / 1e9, 1)} tỷ / cần ≥ ${so(g.threshold / 1e9, 0)} tỷ`;
  else if (g.gate === 'volat') v = `${pc(g.actual)} / cần ≥ ${pc(g.threshold)}`;
  else if (g.gate === 'base') v = `${pc(g.actual)} / cần ≤ ${pc(g.threshold)}` + (!g.ok ? ` · rộng hơn ${so(-g.gap * 100, 1)} điểm %` : '');
  else if (g.gate === 'risk') v = g.ok ? (g.actual == null ? 'qua' : (g.actual >= 0 ? `qua · CFO 4 quý +${so(g.actual / 1e9, 0)} tỷ` : `qua · CFO âm ${so(-g.actual / 1e9, 0)} tỷ nhưng ngành được miễn`))
    : `CFO 4 quý: ${so(g.actual / 1e9, 0)} tỷ / cần > 0 · âm ${so(-g.actual / 1e9, 0)} tỷ`;
  else if (g.gate === 'score') v = `${so(g.actual, 1)} / cần ≥ ${g.threshold}`;
  return { lab, v };
}

function obsGateList(r) {
  const O = OBS();
  const li = r.gates.map((g, k) => { const t = obsGateText(g);
    return `<div style="display:flex;gap:10px;padding:5px 0;border-bottom:1px solid var(--line)">
      <span style="min-width:22px">${g.ok ? '✅' : '❌'}</span><span style="min-width:34px" class="muted">Cổng ${k + 1}</span>
      <span style="flex:1">${esc(t.lab)}</span><span style="${g.ok ? '' : 'color:var(--critical);font-weight:650'}">${t.v}</span></div>`; }).join('');
  const c9 = r.cond9 == null ? 'chưa có số' : (r.cond9 ? `✅ ${String(r.ordimb).replace('.', ',')} ≥ ${String(r.ordimb_min).replace('.', ',')}` : `❌ ${String(r.ordimb).replace('.', ',')} < ${String(r.ordimb_min).replace('.', ',')}`);
  return `${li}<div style="display:flex;gap:10px;padding:6px 0"><span style="min-width:22px"></span><span class="muted">Cond9 (tối phiên ${ddmm(O.asof)}):</span><b>${c9}</b></div>
    <div class="muted" style="font-size:11.5px">Dữ liệu BCTC: ${esc(r.period || '—')} · hạng thanh khoản ${r.liquidity_rank} · ${esc(r.sector)}</div>`;
}

function obsWatch78Section() {
  const O = OBS(); if (!O || !O.config.show_7of8) return '';
  const W = O.watch78 || [];
  const near = W.filter(r => r.kind === 'NEAR'), c9x = W.filter(r => r.kind === 'COND9_FAIL');
  const n7 = near.filter(r => r.passed === 7), n6 = near.filter(r => r.passed === 6);
  const den = (D.regime[D.regime.length - 1] || {}).light;
  const card = (r, warn) => { const miss = r.gates.filter(x => !x.ok).map(obsGateText);
    return `<div class="card" style="flex:1 1 280px;min-width:260px;border-style:dashed;cursor:pointer" onclick="openChart('${r.symbol}')" title="Bấm để xem đủ 8 cổng">
      <div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:17px">${esc(r.symbol)}</b>
        <span class="muted" style="font-weight:700">${r.passed}/${r.total} CỔNG</span></div>
      <div style="font-size:13px;line-height:1.6;margin-top:4px">
        <div>CANSLIM <b>${String(r.score).replace('.', ',')}</b> ✅</div>
        ${miss.map(t => `<div>Thiếu: <b style="color:var(--critical)">${esc(t.lab)}</b> ❌</div><div class="muted">${t.v}</div>`).join('')}
        <div>Cond9: ${r.cond9 == null ? 'chưa có số' : (r.cond9 ? '✅' : '❌ (kể cả đủ cổng cũng chỉ là lệnh dò, bán T+3)')} · TOP hạng ${r.liquidity_rank} · đèn ${LIGHTNAME[den] || '—'}</div>
      </div>
      ${warn ? `<div style="margin-top:6px;color:var(--critical);font-weight:700">⚠ THIẾU COND9 — KHÔNG MUA</div>` : ''}
      <div style="margin-top:6px;font-size:12px;font-weight:700;letter-spacing:.04em" class="muted">${warn ? 'THEO DÕI — KHÔNG PHẢI MUA' : 'GẦN ĐẠT — KHÔNG PHẢI MUA'}</div></div>`; };
  const grid = rs => `<div style="display:flex;gap:12px;flex-wrap:wrap">${rs.map(r => card(r, false)).join('')}</div>`;
  return `<h2>2. Gần đạt — thiếu 1–2 cổng <span class="muted" style="font-size:13px;font-weight:400">(${near.length} mã · phiên ${ddmm(O.asof)} · chỉ theo dõi)</span></h2>
    <h3 style="margin:10px 0 8px">7/8 — thiếu 1 cổng (${n7.length})</h3>
    ${n7.length ? grid(n7) : '<div class="muted">Không có mã nào thiếu đúng 1 cổng ở phiên này.</div>'}
    <h3 style="margin:16px 0 8px">6/8 — đã nổ giá, thiếu 2 cổng (${n6.length})</h3>
    ${n6.length ? grid(n6) : '<div class="muted">Không có mã nào đã nổ giá mà thiếu 2 cổng ở phiên này.</div>'}
    ${c9x.length ? `<h3 style="margin:16px 0 8px;color:var(--critical)">Đủ cổng nhưng thiếu Cond9 (${c9x.length}) — không mua</h3>
    <div style="display:flex;gap:12px;flex-wrap:wrap;opacity:.8">${c9x.map(r => card(r, true)).join('')}</div>` : ''}`;
}

function obsSignalsSection() {
  const S = D.signals_today || [];
  return `<h2>1. Đủ điều kiện — tín hiệu chính thức <span class="muted" style="font-size:13px;font-weight:400">(${S.length} mã)</span></h2>
    ${S.length ? `<div style="display:flex;gap:10px;flex-wrap:wrap">${S.map(s => `<div class="card" style="cursor:pointer;border-color:var(--good)" onclick="openChart('${s.sym}')">
      <b style="font-size:16px">${esc(s.sym)}</b> <span class="muted">· điểm ${String(s.score).replace('.', ',')} · ${s.cond9_ok ? 'Cond9 ✅' : 'Cond9 ❌ (lệnh dò, bán T+3)'}</span></div>`).join('')}</div>`
      : '<div class="muted">Phiên này bộ máy không có tín hiệu mua.</div>'}`;
}

function obsDetail(sym) {
  const O = OBS(); if (!O) return '';
  let h = '';
  const r = (O.watch78 || []).find(x => x.symbol === sym);
  if (r) h += `<div class="card" style="border-style:dashed;margin-top:10px"><div style="font-weight:800;letter-spacing:.03em;margin-bottom:6px">
      ${r.cond9 === false ? '<span style="color:var(--critical)">⚠ THIẾU COND9 — KHÔNG MUA · </span>' : ''}${r.kind === 'NEAR' ? `${r.passed}/${r.total} — GẦN ĐẠT — KHÔNG PHẢI MUA` : `THEO DÕI ${r.passed}/${r.total} — CHƯA PHẢI TÍN HIỆU MUA`}</div>${obsGateList(r)}</div>`;
  const held = (typeof danhMuc === 'function' ? danhMuc() : []).find(x => x.sym === sym && (x.nguon === 'auto' || x.nguon === 'ghitien'));
  if (held) { const c = obsPathCard(sym, held.entry); if (c) h += `<h3 style="margin:14px 0 8px">Đường đi sau breakout</h3><div style="display:flex">${c}</div>`; }
  return h;
}


/* ---------- R29 (28/09/2026): MISSED-WINNER AUDIT — chỉ đo, không đổi luật ----------
   Các mã "gần nổ" trượt ĐÚNG 1 cổng, chia theo cổng và khoảng cách tới ngưỡng, so với tín hiệu
   PROD. Dữ liệu: D.missed_audit (produce2 → missed.py). Mức tín hiệu, không phải deal. */
function missedAuditSection() {
  const A = D.missed_audit; if (!A || A.error) return A && A.error ? `<div class="note warn">Bảng R29 lỗi: ${esc(A.error)}</div>` : '';
  const per = [['all', 'Toàn kỳ'], ['2019-2022', '2019–22'], ['2023-now', '2023 → nay'], ['oos', 'Ngoài mẫu (từ ' + ddmm(A.oos_from) + ')']];
  const pc = x => x == null ? '—' : (x >= 0 ? '+' : '−') + Math.abs(x * 100).toFixed(1).replace('.', ',') + '%';
  const nn = x => x == null ? '—' : String(x).replace('.', ',');
  const base = (A.table.SIGNAL || {})['all'] || {};
  const row = (g, k) => { const s = A.table[g][k] || {}; if (!s.n) return '';
    const sig = g === 'SIGNAL', small = (s.n10 || 0) < 30;
    const better = !sig && s.pf10 != null && base.pf10 != null && s.pf10 >= base.pf10;
    return `<tr style="${sig ? 'font-weight:700;background:color-mix(in srgb,var(--good) 8%,transparent)' : ''}">
      <td>${esc(A.group_vi[g])}</td><td style="text-align:right">${s.n}${small && !sig ? ' <span class="muted" title="Dưới 30 sự kiện — mẫu nhỏ, đừng kết luận">*</span>' : ''}</td>
      <td style="text-align:right" class="${(s.avg3 || 0) >= 0 ? 'pos' : 'neg'}">${pc(s.avg3)}</td>
      <td style="text-align:right" class="${(s.avg5 || 0) >= 0 ? 'pos' : 'neg'}">${pc(s.avg5)}</td>
      <td style="text-align:right" class="${(s.avg10 || 0) >= 0 ? 'pos' : 'neg'}">${pc(s.avg10)}</td>
      <td style="text-align:right">${pc(s.med10)}</td><td style="text-align:right">${s.win10 == null ? '—' : Math.round(s.win10 * 100) + '%'}</td>
      <td style="text-align:right;${better ? 'color:var(--warn);font-weight:700' : ''}">${nn(s.pf10)}</td>
      <td style="text-align:right">${s.run10 == null ? '—' : Math.round(s.run10 * 100) + '%'}</td></tr>`; };
  const table = k => `<div class="card tblwrap"><table><thead><tr><th>Nhóm (trượt đúng 1 cổng)</th><th style="text-align:right">Số lần</th>
      <th style="text-align:right">TB T+3</th><th style="text-align:right">TB T+5</th><th style="text-align:right">TB T+10</th>
      <th style="text-align:right">Trung vị T+10</th><th style="text-align:right">Thắng T+10</th><th style="text-align:right">PF T+10</th>
      <th style="text-align:right" title="Tỷ lệ có đóng cửa cao nhất ≥ +10% trong 10 phiên">Chạy ≥10%</th></tr></thead>
      <tbody>${A.groups.map(g => row(g, k)).join('')}</tbody></table></div>`;
  const rec = (A.recent || []).slice(-15).reverse();
  return `<h2 style="margin-top:34px">R29 — Hệ đang bỏ lỡ winner vì cổng nào?</h2>
    <p class="muted" style="margin-top:0">Mỗi phiên từ 2019, lấy các mã đạt mọi cổng bắt buộc (TOP ${(D.cfg_prod || {}).top_n}, vốn hoá, GTGD, biến động)
    nhưng <b>trượt đúng 1 cổng</b>, chia theo cổng và khoảng cách tới ngưỡng. Lợi nhuận tính từ giá đóng cửa phiên đó (khớp ATC, đã trừ phí)
    tới T+3 / T+5 / T+10. Một mã tính một lần trong ${A.cooldown} phiên. <b>Chỉ đo — không đổi luật.</b>
    Nhóm nào có PF T+10 ≥ tín hiệu thật được tô vàng. <b>*</b> = dưới 30 sự kiện: mẫu nhỏ, chưa đủ để kết luận.
    Chỉ nên nghĩ tới nới một cổng khi nhóm của nó tốt đều ở CẢ HAI giai đoạn <b>và</b> ở phần ngoài mẫu.</p>
    ${per.map(([k, t]) => `<h3 style="margin:14px 0 6px">${t}</h3>${(A.table.SIGNAL[k] || {}).n || A.groups.some(g => (A.table[g][k] || {}).n)
      ? table(k) : '<div class="muted">Chưa có sự kiện nào (phần ngoài mẫu sẽ đầy dần mỗi tối).</div>'}`).join('')}
    <h3 style="margin:18px 0 6px">15 lần gần nhất</h3>
    <div class="card tblwrap"><table><thead><tr><th>Phiên</th><th>Mã</th><th>Trượt cổng</th><th style="text-align:right">T+3</th>
      <th style="text-align:right">T+5</th><th style="text-align:right">T+10</th></tr></thead><tbody>
      ${rec.map(e => `<tr style="cursor:pointer" onclick="openChart('${e.sym}')"><td>${ddmm(e.date)}</td><td><b>${esc(e.sym)}</b></td>
        <td>${esc(A.group_vi[e.group])}</td><td style="text-align:right">${pc(e.t3)}</td><td style="text-align:right">${pc(e.t5)}</td>
        <td style="text-align:right">${pc(e.t10)}</td></tr>`).join('')}</tbody></table></div>
    <div class="muted" style="font-size:11.5px">${esc(A.note)} Dữ liệu tới ${ddmm(A.asof)}.</div>`;
}
