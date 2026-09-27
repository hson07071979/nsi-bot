/* ============================================================================
   LỚP QUAN SÁT (R27A, 27/09/2026) — CHỈ ĐỂ ĐỌC, KHÔNG PHẢI TÍN HIỆU.
   1. Đường đi sau breakout của vị thế đang nắm (T+1/T+2/T+3/T+5, lãi, đỉnh, MFE/MAE,
      giữ trên giá breakout, đỉnh mới, Cond9) + nhãn MÔ TẢ. Nhãn không đổi "Việc cần làm".
   2. GẦN ĐẠT — thiếu đúng 1 cổng (7/8): danh sách theo dõi. Không phải MUA, không vào sổ,
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
      ${o('Đang', obsPct(p.gain_now), cls(p.gain_now || 0))}
      ${o('Đỉnh lãi (đóng cửa)', obsPct(p.peak_gain))}
      ${o('MFE / MAE từ lúc mua', `${obsPct(p.mfe_since_entry)} / ${obsPct(p.mae_since_entry)}`)}
      ${o('T+1 · T+2 · T+3 · T+5', [p.ret_t1, p.ret_t2, p.ret_t3, p.ret_t5].map(x => obsPct(x)).join(' · '))}
      ${o('Giữ trên giá breakout', co(p.above_breakout_close))}
      ${o('Đỉnh mới sau breakout', co(p.new_high_since_breakout) + (p.days_since_last_high != null ? ` <span class="muted" style="font-weight:400">(đỉnh cách ${p.days_since_last_high} phiên)</span>` : ''))}
      ${o('Cond9', c9)}
    </div>
    <div class="muted" style="font-size:11px;margin-top:6px">CHỈ QUAN SÁT — không dùng để mua thêm, bán hay đổi cỡ lệnh. Việc cần làm xem ở bảng trên.</div>
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
  else if (g.gate === 'risk') v = g.ok ? 'qua' : `CFO 4 quý: ${so(g.actual / 1e9, 0)} tỷ / cần > 0 · âm ${so(-g.actual / 1e9, 0)} tỷ`;
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
  const near = W.filter(r => r.kind === 'NEAR' && r.cond9 !== false), c9x = W.filter(r => r.kind === 'COND9_FAIL' || (r.kind === 'NEAR' && r.cond9 === false));
  const den = (D.regime[D.regime.length - 1] || {}).light;
  const card = (r, warn) => { const g = r.gates.find(x => !x.ok); const t = g ? obsGateText(g) : null;
    return `<div class="card" style="flex:1 1 280px;min-width:260px;border-style:dashed;cursor:pointer" onclick="openChart('${r.symbol}')" title="Bấm để xem đủ 8 cổng">
      <div style="display:flex;justify-content:space-between;align-items:center"><b style="font-size:17px">${esc(r.symbol)}</b>
        <span class="muted" style="font-weight:700">${r.passed}/${r.total} CỔNG</span></div>
      <div style="font-size:13px;line-height:1.6;margin-top:4px">
        <div>CANSLIM <b>${String(r.score).replace('.', ',')}</b> ✅</div>
        ${t ? `<div>Thiếu: <b style="color:var(--critical)">${esc(t.lab)}</b> ❌</div><div class="muted">${t.v}</div>` : ''}
        <div>Cond9: ${r.cond9 == null ? 'chưa có số' : (r.cond9 ? '✅' : '❌')} · TOP hạng ${r.liquidity_rank} · đèn ${LIGHTNAME[den] || '—'}</div>
      </div>
      ${warn ? `<div style="margin-top:6px;color:var(--critical);font-weight:700">⚠ THIẾU COND9 — KHÔNG MUA</div>` : ''}
      <div style="margin-top:6px;font-size:12px;font-weight:700;letter-spacing:.04em" class="muted">THEO DÕI — KHÔNG PHẢI MUA</div></div>`; };
  return `<h2>2. Gần đạt — thiếu 1 cổng <span class="muted" style="font-size:13px;font-weight:400">(${near.length} mã · phiên ${ddmm(O.asof)} · chỉ theo dõi)</span></h2>
    <p class="muted" style="margin-top:0;font-size:12.5px">Đạt 7/8 cổng, CANSLIM đạt sàn, dữ liệu đủ. Không phải tín hiệu: không vào sổ, không kêu chuông, không đặt lệnh. Khi đủ cổng còn thiếu, mã tự vào pipeline bình thường. Nghiên cứu R25: nhóm này KHÔNG tốt hơn nhóm đủ 8/8.</p>
    <div style="display:flex;gap:12px;flex-wrap:wrap">${near.map(r => card(r, false)).join('') || '<div class="muted">Không có mã nào thiếu đúng 1 cổng ở phiên này.</div>'}</div>
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
      ${r.cond9 === false ? '<span style="color:var(--critical)">⚠ THIẾU COND9 — KHÔNG MUA · </span>' : ''}THEO DÕI ${r.passed}/${r.total} — CHƯA PHẢI TÍN HIỆU MUA</div>${obsGateList(r)}</div>`;
  const held = (typeof danhMuc === 'function' ? danhMuc() : []).find(x => x.sym === sym && (x.nguon === 'auto' || x.nguon === 'ghitien'));
  if (held) { const c = obsPathCard(sym, held.entry); if (c) h += `<h3 style="margin:14px 0 8px">Đường đi sau breakout</h3><div style="display:flex">${c}</div>`; }
  return h;
}
