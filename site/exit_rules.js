/* ============================================================================
   LUẬT THOÁT — bản JavaScript của exit_rules.py (TOP110 + S1, 26/09/2026).

   Một định nghĩa duy nhất bằng Python (exit_rules.py) chạy trong bộ máy, sổ ghi
   tiến và chuông Telegram. Trang web cần tự quyết khi có GIÁ TRONG PHIÊN, nên
   có bản sao này — và tests/test_exit_js.py chạy file này bằng node trên một lưới
   tình huống, bắt buộc ra ĐÚNG quyết định + ĐÚNG câu chữ như Python.
   Không có DOM ở đây; không đổi file này mà không đổi exit_rules.py.

   Đơn vị: gain, peak, floor là PHÂN SỐ (0,05 = 5%), cùng quy ước bộ máy:
   gain = giá đóng cửa ÷ (giá mua × (1 + phí mua)) − 1, peak = gain cao nhất theo
   giá đóng cửa từ sau ngày mua. Bán ATC tại giá đóng cửa, chỉ từ T+sell_from.
   KHÔNG có lệnh dừng trong phiên.
============================================================================ */
const ER_R_PROBE = 'Cond9 không xác nhận — bán lệnh thăm dò';
const ER_R_HARD = 'Hard stop −10%';
const ER_R_STOP = 'Cắt lỗ −7%';

function erPct(x, nd) {   // = exit_rules._pct: '%.{nd}f' % (x*100), dấu phẩy
  return (x * 100).toFixed(nd || 0).replace('.', ',');
}
function erTiers(C) {
  return ((C && C.profit_lock) || []).map(t => [+t[0], +t[1]]).sort((a, b) => a[0] - b[0]);
}
function erProfitFloor(peak, C) {
  let best = [null, null];
  for (const [a, b] of erTiers(C)) if (peak >= a - 1e-12 && (best[1] === null || b > best[1])) best = [a, b];
  return best;
}
function erLockReason(a, b) { return `Khoá lãi S1 (đỉnh ≥${erPct(a)}% → sàn +${erPct(b)}%)`; }
function erIsLock(r) { return String(r || '').startsWith('Khoá lãi S1'); }
function erG(C, k, mac) { return (C && C[k] != null) ? C[k] : mac; }

function erDecide(C, gain, peak, held, o) {
  o = o || {};
  const sf = parseInt(erG(C, 'sell_from', 2)) || 2;
  const hsFrom = parseInt(erG(C, 'hs_from', sf)) || sf;
  const [trig, floor] = erProfitFloor(peak, C);
  const out = { rule: null, phan: 1.0, sellable: held >= sf, pending: null, floor, trigger: trig,
                lock_active: floor !== null, sell_from: sf, held, gain, peak };
  const hard = erG(C, 'use_hard_stop', true) && gain <= erG(C, 'hard_stop', -0.10);
  const chain = (ign) => {
    const h = ign ? Math.max(held, sf) : held;
    if (o.probe_fail) return [ER_R_PROBE, 1.0];
    if (erG(C, 'use_hard_stop', true) && gain <= erG(C, 'hard_stop', -0.10) && h >= hsFrom) return [ER_R_HARD, 1.0];
    const moBy = erG(C, 'mo_by', null);
    if (moBy && moBy <= h && h <= erG(C, 'mo_window', 99) && peak < erG(C, 'mo_need', 0.0))
      return [`Momentum: không chạy (T+${moBy} chưa lên ${Math.round(erG(C, 'mo_need', 0) * 100)}%)`, 1.0];
    if (h >= 3 && gain <= erG(C, 'stop', -0.07)) return [ER_R_STOP, 1.0];
    if (erG(C, 'use_be', false) && peak >= erG(C, 'be_trigger', 0.08) && gain <= erG(C, 'be_level', 0.01))
      return [`Về bờ (đã lãi ${Math.floor(erG(C, 'be_trigger', 0.08) * 100)}%)`, 1.0];
    if (floor !== null && gain <= floor) return [erLockReason(trig, floor), 1.0];
    if (h >= erG(C, 't_valve', 4) && gain <= erG(C, 'valve_min', 0.0)) return [`Van thời gian T+${erG(C, 't_valve', 4)}`, 1.0];
    if (peak >= erG(C, 'big_win', 0.19) && (o.b10 || 0) >= erG(C, 'conf', 2)) return [`Trailing MA${erG(C, 'trail_fast', 10)} (lãi lớn)`, 1.0];
    if ((o.b20 || 0) >= erG(C, 'conf', 2)) return [`Trailing MA${erG(C, 'trail_ma', 30)}`, 1.0];
    if (erG(C, 'use_orange_cut', true) && o.light_today === 'CAM' && !o.part
        && (!erG(C, 'orange_cut_only_if_worse', true) || ['XANH', 'VANG'].includes(o.light_entry)))
      return ['Đèn Cam — hạ 1/3', 1 / 3];
    return [null, 1.0];
  };
  if (held >= sf || (hard && held >= hsFrom)) {
    [out.rule, out.phan] = chain(false);
  } else {
    const [r] = chain(true);
    if (r && !r.startsWith('Momentum') && !r.startsWith('Van thời gian')) out.pending = r;
  }
  return out;
}

function erActionText(d) {   // = exit_rules.action_text
  const g = d.gain, pk = d.peak, fl = d.floor, r = d.rule, pend = d.pending, sf = d.sell_from || 3;
  const sg = g >= 0 ? '+' : '';
  if (r && erIsLock(r)) return `BÁN ATC — KHOÁ LÃI: từng đạt +${erPct(pk, 1)}%, hiện còn ${sg}${erPct(g, 1)}%, sàn bảo vệ +${erPct(fl)}%`;
  if (r) return (d.phan < 1 ? 'HẠ 1/3 ATC — ' : 'BÁN ATC — ') + r;
  if (pend && erIsLock(pend)) {
    const con = Math.max(0, sf - (parseInt(d.held) || 0));
    return `CHỜ T+${sf} — KHOÁ LÃI ĐÃ THỦNG: từng đạt +${erPct(pk, 1)}%, hiện ${sg}${erPct(g, 1)}% ≤ sàn +${erPct(fl)}%; chưa bán được (còn ${con} phiên) — bán ATC T+${sf} nếu đóng cửa vẫn ≤ sàn`;
  }
  if (pend) return `CHỜ T+${sf} — ${pend} (chưa bán được, xét lại ATC T+${sf})`;
  if (d.lock_active) return `GIỮ — khoá lãi đang bật: đỉnh +${erPct(pk, 1)}%, sàn bảo vệ +${erPct(fl)}% (hiện ${sg}${erPct(g, 1)}%)`;
  return 'GIỮ';
}

if (typeof module !== 'undefined') module.exports = { erDecide, erActionText, erProfitFloor, erLockReason };
