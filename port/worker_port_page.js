/* ============================================================================
   TRANG /port — Lọc port · chỉ trang quản trị nsi-quantri
   Gắn giống /daily: trong serveSite(), sau bước kiểm admin:
     if (ADMIN && (url.pathname === '/port' || url.pathname.startsWith('/port/'))) return handlePort(req, env)
   và thêm ở đầu file Worker:  import { handlePort } from './port_page.js'   (hoặc dán cả file này vào cuối)

   Dữ liệu: KV binding SLIDES (đã có, namespace nsi-slides), khóa port/bundle — do workflow "Lọc port" của nsi-bot ghi.
   Không cần token mới. Dữ liệu port là RIÊNG TƯ: chỉ đọc sau bước kiểm admin, không có đường công khai.
   Đường:
     GET /port        trang
     GET /port/data   JSON gói
   Bản 22/10/2026: thêm Sổ giả lập (mua bán + NAV), Đọc BCTC, Nhận định hằng ngày; viết lại toàn bộ lời lẽ.
   ========================================================================== */

export async function handlePort(req, env) {
  const url = new URL(req.url)
  const p = url.pathname.replace(/\/+$/, '') || '/port'
  if (req.method !== 'GET') return pErr(405, 'chỉ đọc')
  if (p === '/port') {
    return new Response(PORT_HTML, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } })
  }
  if (p === '/port/data') {
    if (!env.SLIDES) return pErr(500, 'Worker chưa gắn KV binding SLIDES')
    const v = await env.SLIDES.get('port/bundle', { type: 'text' })
    if (v === null) return pErr(404, 'chưa có gói port — chạy workflow "Lọc port" trong nsi-bot')
    return new Response(v, { headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } })
  }
  return pErr(404, 'không có đường này')
}

function pErr(code, msg) {
  return new Response(JSON.stringify({ loi: msg }), { status: code, headers: { 'content-type': 'application/json; charset=utf-8' } })
}

const PORT_HTML = `<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Lọc port</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1f23;--mut:#6b6f76;--line:#e4e2dc;--acc:#1f5f8b;--up:#167a3e;--dn:#b42318;--warn:#a15c07;--chip:#eef2f6;--vni:#9aa0a6}
@media (prefers-color-scheme:dark){:root{--bg:#16181b;--card:#1f2226;--ink:#e8e6e3;--mut:#9aa0a6;--line:#33373c;--acc:#5aa2d6;--up:#4cc27a;--dn:#f0766b;--warn:#e0a54a;--chip:#2a2e33;--vni:#7d838a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1100px;margin:0 auto;padding:16px}a{color:var(--acc)}h1{font-size:22px;margin:4px 0}h2{font-size:18px;margin:20px 0 8px}h3{font-size:15px;margin:14px 0 6px}
.mut{color:var(--mut);font-size:13px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.pill{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;font-weight:600;background:var(--chip);margin-right:4px}
.up{color:var(--up)}.dn{color:var(--dn)}.warn{color:var(--warn)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.tabs button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer}
.tabs button.on{background:var(--acc);border-color:var(--acc);color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.kpi div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.kpi b{display:block;font-size:20px}
.chain{display:grid;gap:6px}.chain div{border-left:3px solid var(--acc);padding:2px 0 2px 10px}.chain b{display:block;font-size:12.5px;color:var(--mut)}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;vertical-align:top;white-space:nowrap}
td.w{white-space:normal;min-width:220px}th{cursor:pointer;user-select:none;position:sticky;top:0;background:var(--card)}td.r,th.r{text-align:right}
.may{border:1px solid var(--line);border-radius:10px;padding:10px 12px}.may.nguoc{border-color:var(--dn);border-width:2px}
.flag{background:color-mix(in srgb,var(--dn) 12%,transparent);color:var(--dn);border-radius:8px;padding:6px 10px;margin:6px 0;font-weight:600}
.ok{background:color-mix(in srgb,var(--up) 12%,transparent);color:var(--up);border-radius:8px;padding:6px 10px;margin:6px 0}
input,select{font:inherit;padding:4px 8px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
input[type=number]{width:84px}.f{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}.f label{font-size:13px}
.btn{border:0;background:var(--acc);color:#fff;border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer}.btn.g{background:var(--chip);color:var(--ink)}
ul{margin:4px 0;padding-left:20px}details summary{cursor:pointer;font-weight:600}.nb{font-size:11px;color:var(--warn);font-weight:600}
svg text{fill:var(--mut);font-size:11px}
</style></head><body><div class="wrap">
<div><h1>Lọc port</h1><div class="mut">Danh mục đầu tư dài hạn cho khách · mỗi luận điểm được 3 bộ máy (Bot, Bản tin sáng, Daily Market) phản biện và cả bốn đều bị chấm bằng giá thật · chỉ trang quản trị ·
<a href="/daily">Daily</a> · <a href="/tin">Bản tin sáng</a></div><div id="meta" class="mut"></div></div>
<div class="tabs" id="tabs"></div><div id="app" class="card">Đang tải…</div></div>
<script>
const $=s=>document.querySelector(s), esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TABS=[['dm','Danh mục'],['gl','Sổ giả lập'],['so','Từng mã'],['bc','Đọc BCTC'],['nd','Nhận định hằng ngày'],['db','3 máy nói gì'],['loc','Lọc cơ bản'],['hoc','Ai đoán đúng']];
const CH={1:['tăng','up'],'-1':['giảm','dn'],0:['trung lập','mut']}, CHP={tang:1,giam:-1,trung_lap:0};
const CHN={tang:['tăng','up'],giam:['giảm','dn'],ngang:['đi ngang','mut']};
const TT={nghien_cuu:'Đang nghiên cứu',trong_port:'Đang trong danh mục',loai:'Đã loại',dong:'Đã đóng'};
const BEN={bull:'phe lạc quan',bear:'phe thận trọng',trong_tai:'người phân xử',anh_son:'anh Sơn',claude:'Claude'};
const KHAU=[['vi_mo','Vĩ mô'],['nganh','Ngành'],['doanh_nghiep','Doanh nghiệp'],['mo_hinh_kd','Kiếm tiền bằng gì'],['lanh_dao','Ban lãnh đạo'],['chuoi_gia_tri','Vị trí trong chuỗi giá trị'],['dan_nguoc_vi_mo','Tác động ngược lại nền kinh tế']];
let B=null, tab='dm', chon=null, sortK='np4_yoy', sortD=-1;
try{tab=localStorage.getItem('port-tab')||'dm'}catch(e){}
const chip=c=>{const x=CH[String(c)]||CH[0];return '<span class="pill '+x[1]+'">'+x[0]+'</span>'};
const chipN=c=>{const x=CHN[c]||CHN.ngang;return '<span class="pill '+x[1]+'">'+x[0]+'</span>'};
const n=(v,d=1)=>v==null||v===''?'—':(typeof v==='number'?v.toLocaleString('vi-VN',{maximumFractionDigits:d}):esc(v));
const pct=v=>v==null?'—':'<span class="'+(v>0?'up':v<0?'dn':'')+'">'+(v>0?'+':'')+n(v,Math.abs(v)<1?2:1)+'%</span>';
const ty=v=>v==null?'—':n(v,0)+' tỷ';
const tr=v=>v==null?'—':n(v/1e6,1)+' tr';
/* nhãn luận điểm cũ (FACT/OBSERVATION/…) không hiện ra nữa — chỉ để code kiểm */
const bo=s=>String(s==null?'':s).replace(/^(FACT|OBSERVATION|INTERPRETATION|HYPOTHESIS|CONFIRMATION)\\s*:\\s*/i,'');
function list(a){a=(a||[]).filter(Boolean);return a.length?'<ul>'+a.map(x=>'<li>'+esc(bo(typeof x==='string'?x:(x.noi_dung||JSON.stringify(x))))+(x&&x.bang_chung&&x.bang_chung.length?'<div class="mut">Dựa trên: '+x.bang_chung.map(b=>esc(bo(b))).join(' · ')+'</div>':'')+'</li>').join('')+'</ul>':'<span class="mut">—</span>'}
function veTabs(){$('#tabs').innerHTML=TABS.map(t=>'<button class="'+(t[0]===tab?'on':'')+'" data-t="'+t[0]+'">'+t[1]+'</button>').join('');
  document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{tab=b.dataset.t;try{localStorage.setItem('port-tab',tab)}catch(e){};ve()})}
function chonMa(){const L=B.luan_diem||[];if(!L.length)return'';
  return '<div class="f" style="margin-bottom:8px"><label>Mã <select id="chon">'+L.map(x=>'<option '+(x.luan.ma===chon?'selected':'')+' value="'+esc(x.luan.ma)+'">'+esc(x.luan.ma)+' · '+esc(TT[x.luan.trang_thai]||x.luan.trang_thai)+'</option>').join('')+'</select></label>'
  +L.map(x=>x.ho_so.chua_tra_loi.length?'<span class="pill dn">'+esc(x.luan.ma)+': còn '+x.ho_so.chua_tra_loi.length+' máy nói ngược chưa được trả lời</span>':'').join('')+'</div>'}
function cur(){return (B.luan_diem||[]).find(x=>x.luan.ma===chon)}
function rong(){return '<p><b>Chưa có luận điểm nào.</b> Anh nhắn Claude trong chat dự án (ví dụ "phân tích FPT cho port"). Claude viết luận điểm, đẩy vào nhánh port-data, workflow tự chấm và dựng trang.</p>'}

/* ---------------- biểu đồ NAV so với VN-Index (cùng gốc 100) ---------------- */
function veNav(nav){if(!nav||nav.length<2)return '<p class="mut">Cần ít nhất 2 phiên để vẽ.</p>';
  const W=760,H=220,P=34,a=nav.map(r=>r.nav/nav[0].nav*100),v=nav.map(r=>r.vni&&nav[0].vni?r.vni/nav[0].vni*100:null);
  const all=a.concat(v.filter(x=>x!=null)),lo=Math.min(...all)-0.5,hi=Math.max(...all)+0.5,X=i=>P+i*(W-2*P)/(nav.length-1),Y=y=>H-P+(-(y-lo)/(hi-lo))*(H-2*P);
  const path=arr=>arr.map((y,i)=>y==null?'':(i?'L':'M')+X(i).toFixed(1)+','+Y(y).toFixed(1)).join('');
  const g=[lo,(lo+hi)/2,hi].map(y=>'<line x1="'+P+'" x2="'+(W-P)+'" y1="'+Y(y)+'" y2="'+Y(y)+'" stroke="var(--line)"/><text x="2" y="'+(Y(y)+4)+'">'+y.toFixed(1)+'</text>').join('');
  return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" aria-label="NAV sổ giả lập so với VN-Index">'+g
   +'<path d="'+path(v)+'" fill="none" stroke="var(--vni)" stroke-width="1.6" stroke-dasharray="4 3"/><path d="'+path(a)+'" fill="none" stroke="var(--acc)" stroke-width="2.2"/>'
   +'<text x="'+P+'" y="'+(H-8)+'">'+esc(nav[0].ngay)+'</text><text x="'+(W-P-64)+'" y="'+(H-8)+'">'+esc(nav[nav.length-1].ngay)+'</text></svg>'
   +'<div class="mut"><span style="color:var(--acc);font-weight:700">━</span> Sổ giả lập &nbsp; <span style="color:var(--vni);font-weight:700">┅</span> VN-Index · cả hai quy về 100 ở ngày đầu</div>'}


/* ---------------- giải ngân (giai_ngan.py, R38–R40) + điểm 70/30 (R39) ---------------- */
const MUC={mua:'up',ban:'dn',ngung:'dn',ra_soat:'dn',hoan:'warn',cho:'mut',giu:'up',cho_luot:'warn',cho_gia:'mut'};
function gn(){const T=B.trang_thai_tt||{},N=B.nhiet||{},L=(B.luan_diem||[]).filter(x=>x.giai_ngan&&x.giai_ngan.ty_trong_muc_tieu);if(!L.length&&!T.ten)return '';
  let h='<div class="card"><h3>Kế hoạch giải ngân hôm nay</h3><div class="f"><span>Thị trường: <b>'+esc(T.ten||'?')+'</b> (VN-Index '+n(T.vni,1)+', '+n(T.dd)+'% so với đỉnh 250 phiên '+n(T.dinh_250,1)+')</span><span>Chia <b>'+(T.so_dot||'?')+' đợt</b> '+(T.ty_le||[]).map(x=>Math.round(x*100)+'%').join('/')+'</span><span>Rủi ro cả danh mục nếu mọi mã chạm mức bán: <b class="'+(N.vuot?'dn':'')+'">'+n(N.hien_tai,2)+'% tài khoản</b> (trần '+n(N.tran)+'%; khi mua đủ tối đa '+n(N.khi_du_ty_trong,1)+'%)</span>'+(B.luot?'<span>Đang nắm <b>'+n(B.luot.dang_nam,0)+'/8</b> mã · mở mới 20 phiên qua <b>'+n(B.luot.mo_gan,0)+'/2</b> · còn <b>'+n(B.luot.slot,0)+'</b> lượt'+(B.luot.uu_tien&&B.luot.uu_tien.length?' · thứ tự ưu tiên: '+B.luot.uu_tien.map(esc).join(' → '):'')+'</span>':'')+'</div>'
  +'<p class="mut">Cả danh mục: chỉ mở mã mới khi VN-Index thấp hơn đỉnh 250 phiên từ 10%; tối đa 2 mã mới mỗi 20 phiên, ưu tiên điểm 70/30 cao; tối đa 8 mã, mỗi mã ≤ 12,5% tài khoản. Từng mã: hoảng loạn (VN-Index thấp hơn đỉnh từ 20%) chia 2 đợt 60/40, còn lại 3 đợt; đợt sau khi giá đi ngang 20 phiên; giá chạy +10% trước đợt 2 thì mua nửa phần còn lại ngay, nửa khi hồi về MA20; thấp hơn giá vốn 7% thì ngừng mua thêm và xem lại luận điểm; thấp hơn 15% thì bán hết.</p>'
  +(N.vi_pham_tran_ma&&N.vi_pham_tran_ma.length?'<div class="flag">Vượt 12,5% tài khoản/mã: '+N.vi_pham_tran_ma.map(esc).join(', ')+'</div>':'')
  +'<div class="scroll"><table><tr><th>Mã</th><th class="r">Mục tiêu % tài khoản</th><th class="r">Đã mua</th><th class="r">Giá vốn</th><th class="r">Lãi/lỗ</th><th class="r">Ngừng mua dưới</th><th class="r">Bán hết dưới</th><th class="r">Điểm 70/30</th><th>Việc tiếp theo</th></tr>'
  +L.map(x=>{const g=x.giai_ngan,d=x.diem_70_30||{};return '<tr><td><b>'+esc(x.luan.ma)+'</b></td><td class="r">'+n(g.ty_trong_muc_tieu)+'%</td><td class="r">'+n(g.da_giai_ngan)+'%</td><td class="r">'+n(g.gia_von,2)+'</td><td class="r">'+pct(g.lai_lo_pct)+'</td><td class="r">'+n(g.gia_ngung_mua,2)+'</td><td class="r">'+n(g.gia_ban,2)+'</td><td class="r"><b>'+n(d.tong,0)+'</b> <span class="mut">('+n(d.pitch,0)+'+'+n(d.ket_qua,0)+')</span></td><td class="w"><b class="'+(MUC[g.muc]||'')+'">'+esc(g.hanh_dong)+'</b></td></tr>'}).join('')+'</table></div><p class="mut">Bảng này theo sổ lệnh thật anh ghi. Sổ giả lập (tab bên cạnh) chạy cùng quy tắc bằng tiền giả.</p></div>';
  return h}
function d7030(x){const d=x.diem_70_30;if(!d)return '';const c=d.chi_tiet||{};
  return '<div class="grid"><div class="card"><h3>Lập luận '+n(d.pitch,0)+'/70</h3><ul><li>Rẻ so với chính nó: '+n(c.dinh_gia,0)+'/20 <span class="mut">(P/E, P/B ÷ mức thường thấy 3 năm = '+n(c.dinh_gia_rel,2)+')</span></li><li>Trạng thái thị trường: '+n(c.thi_truong,0)+'/20</li><li>Lập luận đủ chặt: '+n(c.lap_luan,0)+'/15</li><li>Vì sao thị trường định giá sai: '+n(c.dinh_gia_sai,0)+'/15'+(c.dinh_gia_sai_ly_do?' <span class="mut">— '+esc(c.dinh_gia_sai_ly_do)+'</span>':'')+'</li></ul></div>'
   +'<div class="card"><h3>Kết quả kinh doanh '+n(d.ket_qua,0)+'/30</h3><ul><li>Lợi nhuận 4 quý: '+n(c.loi_nhuan,0)+'/10</li><li>ROE: '+n(c.roe,0)+'/10</li><li>Mốc BCTC K2: '+n(c.k2,0)+'/10</li></ul><p class="mut">Kiểm lịch sử (R39): tăng trưởng lợi nhuận/doanh thu gần như không dự báo được giá vì ai cũng thấy; rẻ so với chính nó và trạng thái thị trường mới là phần có lợi thế.</p></div></div>'}

/* ---------------- Danh mục ---------------- */
function dm(){const d=B.danh_muc||{},g=(B.gia_lap||{}).tong_ket||{};let h='<h2 style="margin-top:0">Danh mục</h2>';
  if(g.co_du_lieu)h+='<div class="kpi"><div>NAV sổ giả lập<b>'+n(g.nav/1e6,1)+' triệu</b><span class="mut">vốn đầu 1.000 triệu</span></div><div>Lãi/lỗ<b>'+pct(g.lai_pct)+'</b><span class="mut">từ '+esc(g.tu)+'</span></div><div>VN-Index cùng kỳ<b>'+pct(g.vni_pct)+'</b></div><div>Hơn/kém VN-Index<b>'+pct(g.vuot_vni)+'</b></div><div>Tiền mặt<b>'+n(g.tien_mat_pct)+'%</b></div></div>';
  if(d.quan_diem)h+='<div class="card"><h3>Quan điểm đầu tư</h3><div style="white-space:pre-wrap">'+esc(d.quan_diem)+'</div></div>';
  if((d.vi_tri||[]).length)h+='<h3>Mã đang trong danh mục</h3><div class="scroll"><table><tr><th>Mã</th><th class="r">Tỷ trọng</th><th>Vai trò</th><th>Vì sao chọn</th><th class="r">Giá</th><th class="r">Mục tiêu 1</th><th class="r">Mục tiêu 2</th><th>Máy nói ngược</th></tr>'+d.vi_tri.map(v=>{const x=(B.luan_diem||[]).find(z=>z.luan.ma===v.ma),m=((B.muc_tieu_de_xuat||{})[v.ma]||{}).da_duyet||{};
    return '<tr><td><b>'+esc(v.ma)+'</b></td><td class="r">'+n(v.ty_trong)+'%</td><td>'+esc(v.vai_tro)+'</td><td class="w">'+esc(v.ly_do)+'</td><td class="r">'+(x?n(x.gia,2):'')+'</td><td class="r">'+n(m.t1,2)+'</td><td class="r">'+n(m.t2,2)+'</td><td>'+(x?(x.ho_so.nguoc.map(k=>'<span class="pill dn">'+esc(B.ten_may[k]||k)+'</span>').join('')||'<span class="up">không</span>'):'<span class="warn">chưa có luận điểm</span>')+'</td></tr>'}).join('')+'</table></div>';
  if((d.hang_cho||[]).length)h+='<h3>Hàng chờ</h3><ul>'+d.hang_cho.map(x=>'<li><b>'+esc(x.ma)+'</b> — '+esc(x.ly_do)+'</li>').join('')+'</ul>';
  if(d.quy_tac_giai_ngan)h+='<details class="card"><summary>Quy tắc giải ngân anh đã chốt</summary><ul>'+Object.entries(d.quy_tac_giai_ngan).map(([k,v])=>'<li><b>'+esc({dot_sau:'Đợt sau',chay:'Khi giá chạy',hoang_loan:'Khi thị trường hoảng loạn',con_lai:'Bình thường',ban:'Bán hết',muc_tieu:'Chốt lời',co:'Cờ xem lại',review:'Lịch review',nguon:'Nguồn',da_bo:'Đã bỏ'}[k]||k)+':</b> '+esc(v)+'</li>').join('')+'</ul></details>';
  h+=gn();
  if(d.pitch)h+='<div class="card"><h3>Lời giới thiệu cho khách</h3><div style="white-space:pre-wrap">'+esc(d.pitch)+'</div><p class="mut">Không trích tin nhóm Zalo kín. Kiểm tra quy định nội dung của công ty trước khi gửi.</p></div>';
  if((d.rui_ro||[]).length)h+='<div class="card"><h3>Rủi ro của cả danh mục</h3>'+list(d.rui_ro)+'</div>';
  const L=B.luan_diem||[];h+='<h3>Tất cả luận điểm</h3>'+(L.length?'<div class="scroll"><table><tr><th>Mã</th><th>Trạng thái</th><th>Port nghĩ</th><th class="r">Giá</th><th>Bot</th><th>Bản tin</th><th>Daily</th><th>Đủ để xuống tiền?</th><th class="r">Hơn VN-Index 20 phiên</th></tr>'+L.map(x=>{const m=x.ho_so.may;
    return '<tr><td><b>'+esc(x.luan.ma)+'</b></td><td>'+esc(TT[x.luan.trang_thai]||x.luan.trang_thai)+'</td><td>'+chip(CHP[x.luan.chieu]||0)+'</td><td class="r">'+n(x.gia,2)+'</td>'+['bot','tin','daily'].map(k=>'<td>'+chip(m[k].chieu)+(m[k].nguoc_port?(x.ho_so.chua_tra_loi.includes(k)?' <b class="dn" title="chưa trả lời">!</b>':' <span class="mut">đã trả lời</span>'):'')+'</td>').join('')
    +'<td>'+(x.san_sang?'<span class="'+(x.san_sang.ket_luan==='ĐỦ ĐỂ XUỐNG TIỀN'?'up':'warn')+'">'+esc(x.san_sang.ket_luan)+'</span>':'—')+'</td><td class="r">'+pct(x.ket_qua&&x.ket_qua['20p'])+'</td></tr>'}).join('')+'</table></div>':rong());
  return h}

/* ---------------- Sổ giả lập ---------------- */
const LYDO_CO={lo_10:'lỗ từ 10%',thung_ho_tro:'thủng hỗ trợ'};
function gl(){const G=B.gia_lap||{},g=G.tong_ket||{},L=G.luat||{};let h='<h2 style="margin-top:0">Sổ giả lập mua bán</h2><p class="mut">Sổ chạy bằng tiền giả theo đúng quy tắc giải ngân của anh, khớp ở giá đóng cửa, có phí. Không phải lệnh thật. Sổ chỉ ghi tiếp, không sửa lại các phiên đã qua.</p>';
  if(!g.co_du_lieu)return h+'<p>Chưa có phiên nào.</p>';
  h+='<div class="kpi"><div>NAV<b>'+n(g.nav/1e6,1)+' triệu</b><span class="mut">vốn đầu 1.000 triệu</span></div><div>Lãi/lỗ<b>'+pct(g.lai_pct)+'</b></div><div>VN-Index cùng kỳ<b>'+pct(g.vni_pct)+'</b></div><div>Hơn/kém VN-Index<b>'+pct(g.vuot_vni)+'</b></div><div>Sụt giảm lớn nhất<b>'+pct(g.sut_giam_lon_nhat)+'</b></div><div>Tiền mặt<b>'+n(g.tien_mat_pct)+'%</b></div></div>';
  h+='<div class="card">'+veNav(G.nav)+'</div>';
  if((g.co_mo||[]).length)h+=g.co_mo.map(c=>'<div class="flag">Cờ xem lại '+esc(c.ma)+' ('+esc(LYDO_CO[c.loai]||c.loai)+', '+esc(c.ngay)+'): '+esc(c.noi_dung)+'</div>').join('');
  h+='<h3>Đang cầm</h3>'+((g.vi_the||[]).length?'<div class="scroll"><table><tr><th>Mã</th><th class="r">Số cổ phiếu</th><th class="r">Giá vốn</th><th class="r">Giá</th><th class="r">Lãi/lỗ</th><th class="r">% tài khoản</th><th>Đã mua</th><th>Mục tiêu</th><th>Từ ngày</th></tr>'+g.vi_the.map(v=>'<tr><td><b>'+esc(v.ma)+'</b></td><td class="r">'+n(v.cp,0)+'</td><td class="r">'+n(v.gia_von,2)+'</td><td class="r">'+n(v.gia,2)+'</td><td class="r">'+pct(v.lai_pct)+'</td><td class="r">'+n(v.ty_trong)+'%</td><td>'+v.so_dot+'/'+v.ke_hoach+' đợt</td><td>'+(v.da_t2?'đã chốt ở mục tiêu 1 và 2':v.da_t1?'đã chốt ở mục tiêu 1':'chưa chạm')+'</td><td>'+esc(v.ngay_mo)+'</td></tr>').join('')+'</table></div>':'<p class="mut">Không cầm mã nào.</p>');
  const Lh=(G.lenh||[]).slice().reverse();
  h+='<h3>Lịch sử lệnh ('+Lh.length+')</h3>'+(Lh.length?'<div class="scroll" style="max-height:50vh"><table><tr><th>Ngày</th><th>Mã</th><th>Lệnh</th><th class="r">Số cổ phiếu</th><th class="r">Giá</th><th class="r">Tiền</th><th class="r">Phí</th><th class="r">Lãi/lỗ</th><th>Vì sao</th></tr>'+Lh.map(l=>'<tr><td>'+esc(l.ngay)+'</td><td><b>'+esc(l.ma)+'</b></td><td class="'+(l.loai==='MUA'?'up':'dn')+'">'+esc(l.loai)+(l.dot?' · '+esc(l.dot):'')+'</td><td class="r">'+n(l.cp,0)+'</td><td class="r">'+n(l.gia,2)+'</td><td class="r">'+tr(l.tien)+'</td><td class="r">'+tr(l.phi)+'</td><td class="r">'+(l.lai!=null?tr(l.lai)+' ('+pct(l.lai_pct)+')':'')+'</td><td class="w">'+esc(l.ly_do)+'</td></tr>').join('')+'</table></div>':'<p class="mut">Chưa có lệnh.</p>');
  h+='<details class="card"><summary>Luật của sổ</summary><ul>'
   +'<li>Vốn 1 tỷ, phí mua 0,15%, phí bán 0,25% (đã gồm thuế), tiền mặt không có lãi. Khớp ở giá đóng cửa của phiên sau ngày quyết định.</li>'
   +'<li>Chỉ mua mã nằm trong danh mục và đang ở trạng thái "đang trong danh mục". Tỷ trọng = tỷ trọng anh ghi × NAV lúc vào đợt 1.</li>'
   +'<li>Bình thường chia 3 đợt bằng nhau. Khi VN-Index thấp hơn đỉnh 250 phiên từ 20% trở lên (hoảng loạn) thì 2 đợt 60/40.</li>'
   +'<li>Đợt sau: giá đi ngang 20 phiên kể từ đợt trước (biên ≤ 8%, đầu–cuối ≤ 4%, nửa sau không tạo đáy mới); quá 120 phiên không có nền thì mua nốt. Giá chạy +10% so với đợt 1 thì mua ngay nửa phần còn lại, nửa kia khi giá hồi về MA20 (quá 60 phiên thì mua nốt).</li>'
   +'<li>Chạm mục tiêu 1: bán 1/3; chạm mục tiêu 2: bán thêm 1/3; từ lúc chạm mục tiêu 1 không mua thêm.</li>'
   +'<li>Giá đóng cửa thấp hơn giá vốn từ 15%: bán hết. Luận điểm bị loại hoặc mã ra khỏi danh mục: bán hết.</li>'
   +'<li>Thấp hơn giá vốn từ 10%, hoặc thủng hỗ trợ của Daily: chỉ treo cờ xem lại, không bán.</li></ul></details>';
  return h}

/* ---------------- Từng mã ---------------- */
const KQ={'ĐẠT':'up','VÔ HIỆU':'dn','HẾT HẠN':'warn'};
function mucTieu(x){const t=x.luan,d=(B.muc_tieu_de_xuat||{})[t.ma],M=x.muc_tieu_cham||[];let h='';
  if(M.length)h+='<div class="scroll"><table><tr><th>Mục tiêu</th><th class="r">Giá</th><th>Lấy từ đâu</th><th class="r">Cách giá lúc ghi</th><th class="r">Khả năng chạm trong 60 / 120 phiên</th><th>Trạng thái</th></tr>'+M.map(m=>'<tr><td>'+esc(m.id==='T1'?'Mục tiêu 1':m.id==='T2'?'Mục tiêu 2':m.id)+'</td><td class="r">'+n(m.gia,2)+'</td><td class="w">'+esc(m.nguon)+'</td><td class="r">'+pct(m.cach_pct)+'</td><td class="r">'+(m.p60!=null?n(m.p60*100,0)+'%':'—')+' / '+(m.p120!=null?n(m.p120*100,0)+'%':'—')+'</td><td>'
   +(m.trang_thai==='dong'?'<b class="'+(KQ[m.ket_qua]||'')+'">'+esc(m.ket_qua==='ĐẠT'?'đã chạm':m.ket_qua==='HẾT HẠN'?'hết hạn':m.ket_qua)+'</b> '+esc(m.ngay_dong||''):'chưa chạm · '+n(m.phien,0)+' phiên · còn '+pct(m.con_cach_pct))+'</td></tr>').join('')+'</table></div>';
  else h+='<p class="warn">Chưa có mục tiêu đã duyệt — sổ giả lập chưa chốt lời được cho mã này.</p>';
  if(d&&(d.t1||d.t2))h+='<p class="mut">Code đề xuất: mục tiêu 1 <b>'+n(d.t1&&d.t1.gia,2)+'</b> ('+esc(d.t1&&d.t1.nguon)+', '+(d.t1?pct(d.t1.cach_pct):'—')+') · mục tiêu 2 <b>'+n(d.t2&&d.t2.gia,2)+'</b> ('+esc(d.t2&&d.t2.nguon)+', '+(d.t2?pct(d.t2.cach_pct):'—')+'). Claude duyệt rồi mới ghi vào luận điểm.</p>'
   +'<details><summary>Các mốc code đã gom</summary><ul>'+(d.moc||[]).map(m=>'<li>'+n(m.gia,2)+' '+pct(m.cach_pct)+' — '+esc(m.nguon)+'</li>').join('')+'</ul></details>';
  return h}
function sanSang(x){const s=x.san_sang;if(!s)return '';return '<div class="'+(s.ket_luan==='ĐỦ ĐỂ XUỐNG TIỀN'?'ok':'flag')+'">'+esc(s.ket_luan)+' ('+s.dat+'/'+s.tong+' mục đạt)</div><ul>'+s.muc.map(m=>'<li><b class="'+(m.dat?'up':'dn')+'">'+(m.dat?'✓':'✗')+'</b> '+esc(m.ten)+(m.ghi_chu?' <span class="mut">— '+esc(m.ghi_chu)+'</span>':'')+'</li>').join('')+'</ul>'+((s.dieu_kien_vao||[]).length?'<b>Điều kiện vào riêng của mã này</b><ul>'+s.dieu_kien_vao.map(m=>'<li><b class="'+(m.dat?'up':'dn')+'">'+(m.dat?'✓':'✗')+'</b> '+esc(m.ten)+' <span class="mut">— '+esc(m.ghi_chu)+'</span></li>').join('')+'</ul>':'')+'<p class="mut">Danh sách này do code kiểm xem lập luận có đủ phần chưa — đủ phần không có nghĩa là chắc thắng. Tỷ lệ đúng thật nằm ở tab "Ai đoán đúng".</p>'}
function so(){const x=cur();if(!x)return rong();const t=x.luan,h0=x.ho_so;let h=chonMa();
  h+='<h2 style="margin-top:0">'+esc(t.ma)+' <span class="mut">'+esc(h0.nganh||'')+'</span></h2><div><span class="pill">'+esc(TT[t.trang_thai]||t.trang_thai)+'</span>'+chip(CHP[t.chieu]||0)+'<span class="pill">nắm giữ '+esc(t.ky_han||'—')+'</span><span class="pill">giá '+n(x.gia,2)+'</span><span class="mut">mở '+esc(t.ngay_mo||'')+' · cập nhật '+esc(t.cap_nhat||'')+'</span></div>';
  if(t.pitch)h+='<div class="card"><h3>Nói ngắn cho khách</h3><div style="white-space:pre-wrap">'+esc(t.pitch)+'</div></div>';
  if(x.thieu.length)h+='<div class="flag">Lập luận còn thiếu: '+x.thieu.map(esc).join(' · ')+'</div>';
  h+='<h3>Từ vĩ mô xuống doanh nghiệp</h3><div class="chain">'+KHAU.map(k=>'<div><b>'+k[1]+'</b>'+(esc(bo((t.chuoi||{})[k[0]]))||'<span class="warn">chưa viết</span>')+'</div>').join('')+'</div>';
  h+='<h3>Các ý chính</h3>'+list(t.luan_diem);
  h+='<div class="grid"><div><h3>Định giá</h3>'+esc(t.dinh_gia||'—')+'</div><div><h3>Khi nào bỏ luận điểm</h3>'+esc(t.vo_hieu||'—')+'</div></div>';
  h+='<h3>Mục tiêu giá</h3>'+mucTieu(x);
  h+='<h3>Đủ để xuống tiền chưa?</h3>'+sanSang(x);
  h+='<h3>Điểm 70% lập luận / 30% kết quả kinh doanh</h3>'+d7030(x);
  if(x.giai_ngan)h+='<h3>Giải ngân</h3><p><b class="'+(MUC[x.giai_ngan.muc]||'')+'">'+esc(x.giai_ngan.hanh_dong)+'</b></p>';
  h+='<h3>Mốc để code tự chấm</h3>'+((x.kiem_chung||[]).length?'<div class="scroll"><table><tr><th>Mốc</th><th>Nội dung</th><th>Trạng thái</th><th>Kết quả</th></tr>'+x.kiem_chung.map(k=>'<tr><td>'+esc(k.id)+'</td><td class="w">'+esc(k.noi_dung)+'</td><td>'+(k.trang_thai==='mo'?'đang chờ'+(k.phien!=null?' · '+k.phien+'/'+(k.han_phien||'')+' phiên':'')+(k.ghi_chu?' · '+esc(k.ghi_chu):''):'đã chấm '+esc(k.ngay_dong||''))+'</td><td>'+(k.ket_qua?'<b class="'+(k.ket_qua==='ĐÚNG'?'up':'dn')+'">'+esc(k.ket_qua)+'</b>'+(k.gia_tri!=null?' ('+n(k.gia_tri)+')':''):'')+'</td></tr>').join('')+'</table></div>':'<span class="warn">chưa có mốc</span>');
  if(x.ket_qua)h+='<p>Từ ngày vào danh mục '+esc(x.ket_qua.ngay_vao)+': hơn VN-Index sau 20 phiên '+pct(x.ket_qua['20p'])+' · sau 60 phiên '+pct(x.ket_qua['60p'])+'</p>';
  if(t.bai_hoc)h+='<h3>Bài học</h3><div>'+esc(t.bai_hoc)+'</div>';
  return h}

/* ---------------- Đọc BCTC ---------------- */
const NHOM={loi:['kinh doanh chính','up'],tai_chinh:['tài chính',''],mot_lan:['một lần','warn'],du_phong:['dự phòng','dn'],khac:['khác','mut']};
function bc(){const x=cur();let h=chonMa();if(!x)return h+rong();const s=(B.bctc||{})[x.luan.ma];
  h+='<h2 style="margin-top:0">'+esc(x.luan.ma)+': lợi nhuận tăng/giảm vì đâu</h2>';
  if(!s)return h+'<p class="mut">Chưa có BCTC chi tiết của mã này (cần file BCTC mà dây chuyền hằng ngày tải về).</p>';
  if(s.loi_doc)return h+'<p class="flag">'+esc(s.loi_doc)+'</p>';
  h+='<p class="mut">Quý '+esc(s.moi_nhat)+' (công bố '+esc(s.cong_bo)+') so với '+esc(s.so_voi||'—')+'. Số do code tách từ BCTC, đơn vị tỷ đồng.</p>';
  h+='<div class="card"><ul>'+(s.cau_chuyen||[]).map(c=>'<li>'+esc(c)+'</li>').join('')+'</ul></div>';
  if(s.lntt!=null)h+='<div class="kpi"><div>Lãi trước thuế<b>'+ty(s.lntt)+'</b><span class="mut">cùng kỳ '+ty(s.lntt_cung_ky)+'</span></div><div>Phần kinh doanh chính<b>'+ty(s.loi)+'</b><span class="mut">'+(s.loi_yoy!=null?pct(s.loi_yoy)+' so cùng kỳ':'cùng kỳ '+ty(s.loi_cung_ky))+'</span></div><div>Khoản một lần<b>'+ty(s.mot_lan_ty)+'</b><span class="mut">'+(s.mot_lan_pct_lntt!=null?n(s.mot_lan_pct_lntt)+'% lãi trước thuế':'')+'</span></div><div>Lãi trước thuế nếu bỏ khoản một lần<b>'+ty(s.lntt_bo_mot_lan)+'</b></div></div>';
  if((s.cau_noi||[]).length)h+='<h3>Từng khoản so với cùng kỳ</h3><div class="scroll"><table><tr><th>Khoản</th><th>Loại</th><th class="r">Quý này</th><th class="r">Cùng kỳ</th><th class="r">Chênh lệch</th><th>Ghi chú</th></tr>'+s.cau_noi.map(k=>{const g=NHOM[k.nhom]||['',''];return '<tr><td>'+esc(k.ten)+'</td><td><span class="pill '+g[1]+'">'+g[0]+'</span></td><td class="r">'+n(k.nay,0)+'</td><td class="r">'+n(k.cung_ky,0)+'</td><td class="r '+(k.chenh>0?'up':k.chenh<0?'dn':'')+'">'+(k.chenh>0?'+':'')+n(k.chenh,0)+'</td><td class="w mut">'+esc(k.ghi_chu||'')+'</td></tr>'}).join('')+'</table></div>';
  const Q=s.quy||[];if(Q.length)h+='<h3>12 quý gần nhất</h3><div class="scroll"><table><tr><th>Quý</th><th class="r">Lãi trước thuế</th><th class="r">Kinh doanh chính</th><th class="r">Khoản một lần</th><th class="r">Dự phòng</th><th class="r">Lãi sau thuế (công ty mẹ)</th><th class="r">Tiền từ kinh doanh</th></tr>'+Q.slice().reverse().map(q=>'<tr><td>'+esc(q.q)+'</td><td class="r">'+n(q.lntt,0)+'</td><td class="r">'+n(q.loi,0)+'</td><td class="r">'+n(q.mot_lan,0)+'</td><td class="r">'+n(q.du_phong,0)+'</td><td class="r">'+n(q.lnst_me,0)+'</td><td class="r">'+n(q.cfo,0)+'</td></tr>').join('')+'</table></div><p class="mut">Dự phòng: số dương là trích thêm (làm giảm lãi), số âm là hoàn nhập (cộng vào lãi). Ở ngân hàng là trích lập dự phòng tín dụng.</p>';
  return h}

/* ---------------- Nhận định hằng ngày ---------------- */
function bangChinhXac(o){return '<tr>'+[5,20,60].map(k=>{const a=(o||{})[k]||{};return '<td class="r">'+(a.da_cham?a.dung+'/'+a.da_cham:'—')+'</td><td class="r">'+(a.dung_pct!=null?n(a.dung_pct)+'%':'<span class="mut">chưa đủ mẫu</span>')+'</td><td class="r mut">'+n(a.cho||0,0)+' chờ</td>'}).join('')+'</tr>'}
function nd(){const N=B.nhan_dinh||{},H=N.hom_nay||[];let h='<h2 style="margin-top:0">Nhận định hằng ngày</h2><p class="mut">Mỗi chiều code tự ghi cho từng mã: <b>tăng</b>, <b>đi ngang</b> hay <b>giảm</b> so với VN-Index trong 5, 20 và 60 phiên tới. Từ 22/10/2026 nhận định theo <b>hạng</b>: điểm thuộc 30% cao nhất trong ~170 mã thanh khoản → tăng, 30% thấp nhất → giảm, còn lại → đi ngang. Sau đủ phiên, code tự chấm: nói tăng mà mã hơn VN-Index là đúng; nói giảm mà mã kém VN-Index là đúng; nói đi ngang mà chênh lệch nằm trong ±'+n((N.bien||{})[5],0)+'% / ±'+n((N.bien||{})[20],0)+'% / ±'+n((N.bien||{})[60],0)+'% là đúng. Trọng số đang dùng: <b>'+esc((N.trong_so||{}).ten)+'</b>.</p>';
  h+=H.length?'<div class="scroll"><table><tr><th>Mã</th><th>Nhận định</th><th class="r">Điểm</th><th class="r">Hạng</th><th>Vì sao</th><th>Bot · Bản tin · Daily</th><th>Ngày</th></tr>'+H.map(r=>'<tr><td><b>'+esc(r.ma)+'</b></td><td>'+chipN(r.chieu)+'</td><td class="r">'+n(r.diem,2)+'</td><td class="r">'+(r.hang_pct!=null?'top '+n(100-r.hang_pct,0)+'%<div class="mut" style="font-size:11px">/'+n(r.so_ma_xep,0)+' mã</div>':'—')+'</td><td class="w">'+(r.ly_do||[]).map(esc).join('<br>')+'</td><td>'+(r.may?['bot','tin','daily'].map(k=>chip(r.may[k])).join(''):'—')+'</td><td>'+esc(r.ngay)+'</td></tr>').join('')+'</table></div>':'<p class="mut">Chưa có nhận định.</p>';
  const D=N.do_chinh_xac||{};h+='<h3>Đúng bao nhiêu</h3><div class="scroll"><table><tr><th>Nhóm</th>'+[5,20,60].map(k=>'<th class="r" colspan="3">'+k+' phiên</th>').join('')+'</tr>'
   +'<tr><td>Mã trong port</td>'+bangChinhXac(D.port).slice(4)+'<tr><td>Tất cả '+n(N.so_ma_theo_doi||0,0)+' mã theo dõi</td>'+bangChinhXac(D.tat_ca).slice(4)+'</table></div><p class="mut">Dưới 10 lần chấm thì chưa ra tỷ lệ. Code ghi nhận định cho cả nhóm mã thanh khoản cao để có nhiều mẫu học hơn, nhưng trang chỉ hiện mã của port.</p>';
  const L=(N.lich_su_port||[]).filter(r=>r.kq_5||r.kq_20||r.kq_60).slice(-60).reverse();
  if(L.length)h+='<details class="card"><summary>Các nhận định đã chấm ('+L.length+' gần nhất)</summary><div class="scroll"><table><tr><th>Ngày</th><th>Mã</th><th>Nói</th><th>5 phiên</th><th>20 phiên</th><th>60 phiên</th></tr>'+L.map(r=>'<tr><td>'+esc(r.ngay)+'</td><td><b>'+esc(r.ma)+'</b></td><td>'+chipN(r.chieu)+'</td>'+[5,20,60].map(k=>'<td>'+(r['kq_'+k]?'<b class="'+(r['kq_'+k]==='ĐÚNG'?'up':'dn')+'">'+esc(r['kq_'+k])+'</b> '+pct(r['vuot_'+k]):'<span class="mut">chờ</span>')+'</td>').join('')+'</tr>').join('')+'</table></div></details>';
  const Ho=N.hoc;h+='<h3>Vòng học: có nên đổi trọng số không?</h3>';
  if(!Ho)return h+'<p class="mut">Lượt này không chạy lùi được (thiếu bảng giá dài hạn hoặc BCTC chi tiết).</p>';
  h+='<div class="'+(/đề xuất anh Sơn duyệt/.test(Ho.ket_luan)?'ok':'card')+'">'+esc(Ho.ket_luan)+'</div><p class="mut">Code chạy lùi cùng cách tính trên lịch sử từ 2019 ('+n(Ho.so_mau,0)+' mẫu, chỉ dùng BCTC đã công bố tính tới từng ngày), luyện mô hình trên các năm trước rồi thử trên năm sau. Bảng dưới so trọng số đang dùng với mô hình trên những năm mô hình <b>chưa thấy</b>. Code không tự đổi: anh đồng ý thì nhắn Claude ghi trọng số mới.</p>';
  const T0=Ho.tong_dang_dung||{},T1=Ho.tong_mo_hinh||{};
  const o3=(a)=>'<td class="r">'+(a.ic!=null?(a.ic>0?'+':'')+n(a.ic,3):'—')+'</td><td class="r">'+pct(a.chenh)+'</td><td class="r">'+(a.top_thang_pct!=null?n(a.top_thang_pct)+'%':'—')+'</td><td class="r mut">'+(a.dung_pct!=null?n(a.dung_pct)+'%':'—')+'</td>';
  h+='<div class="scroll"><table><tr><th rowspan="2">Kỳ hạn</th><th colspan="4">Bộ đang dùng</th><th colspan="4">Mô hình luyện lại</th><th class="r" rowspan="2">Số mẫu</th></tr><tr><th class="r">Xếp hạng (IC)</th><th class="r">Nhóm cao − nhóm thấp</th><th class="r">Nhóm cao hơn VNI</th><th class="r">Đúng chiều</th><th class="r">Xếp hạng (IC)</th><th class="r">Nhóm cao − nhóm thấp</th><th class="r">Nhóm cao hơn VNI</th><th class="r">Đúng chiều</th></tr>'+[5,20,60].map(k=>'<tr><td>'+k+' phiên</td>'+o3(T0[k]||{})+o3(T1[k]||{})+'<td class="r">'+n((T0[k]||{}).mau,0)+'</td></tr>').join('')+'</table></div><p class="mut"><b>Xếp hạng (IC)</b>: điểm hôm nay xếp mã có đúng thứ tự hơn/kém VN-Index về sau không — 0 là đoán bừa, +0,05 trở lên là có ích thật với cổ phiếu. <b>Nhóm cao − nhóm thấp</b>: 20% mã điểm cao nhất hơn 20% mã điểm thấp nhất bao nhiêu % trong kỳ hạn đó. <b>Nhóm cao hơn VNI</b>: bao nhiêu % số lần nhóm điểm cao thật sự chạy hơn VN-Index. "Đúng chiều" chỉ để đối chiếu — gần 50% với mọi bộ, vì đa số mã đi theo cả thị trường.</p>';
  h+='<details><summary>Theo từng năm</summary><div class="scroll"><table><tr><th>Năm thử</th><th class="r">Mẫu luyện</th>'+[5,20,60].map(k=>'<th class="r">'+k+'p đang dùng</th><th class="r">'+k+'p mô hình</th>').join('')+'</tr>'+(Ho.theo_nam||[]).map(y=>'<tr><td>'+esc(y.nam)+'</td><td class="r">'+n(y.mau_luyen,0)+'</td>'+[5,20,60].map(k=>'<td class="r">'+n(((y.dang_dung||{})[k]||{}).ic,3)+'</td><td class="r">'+n(((y.mo_hinh||{})[k]||{}).ic,3)+'</td>').join('')+'</tr>').join('')+'</table></div><p class="mut">Số trong bảng là IC xếp hạng từng năm (dương = xếp đúng hướng).</p></details>';
  const w0=(N.trong_so||{}).w||{},w1=((Ho.de_xuat||{}).w)||{};
  h+='<details><summary>Trọng số đang dùng và đề xuất</summary><div class="scroll"><table><tr><th>Đặc trưng</th><th class="r">Đang dùng</th><th class="r">Đề xuất</th></tr>'+Object.keys(w0).map(k=>'<tr><td>'+esc(TEN_DT[k]||k)+'</td><td class="r">'+n(w0[k],3)+'</td><td class="r">'+n(w1[k],3)+'</td></tr>').join('')+'</table></div></details>';
  return h}
const TEN_DT={rs120:'Mạnh hơn VN-Index 120 phiên',cfo_ln:'Tiền từ kinh doanh ÷ lãi 4 quý',rs20:'Mạnh hơn VN-Index 20 phiên',rs60:'Mạnh hơn VN-Index 60 phiên',ma50:'Giá so với MA50',ma200:'Giá so với MA200',dinh250:'Cách đỉnh 250 phiên',bien_dong:'Biến động 20 phiên',ln_yoy:'Lợi nhuận quý so cùng kỳ',dt_yoy:'Doanh thu quý so cùng kỳ',dinh_gia:'Định giá so với trung vị 12 quý',thi_truong:'VN-Index so với MA50'};

/* ---------------- 3 máy nói gì ---------------- */
function tinCay(k){const T=B.tin_cay||{},pv=(T.port_vs_may||{})[k]||{};let s='';
  if(k==='tin'){const tt=(T.tin||{}).trong_tai;s=tt?'người phân xử đúng '+n(tt.ty_le_dung)+'% trong '+tt.n+' lần chấm':'chưa có số chấm'}
  if(k==='daily'){const d=T.daily||{};s=d.da_cham?'sổ dự báo đúng '+d.dung+'/'+d.da_cham:'sổ dự báo chưa chấm dòng nào'}
  if(k==='bot'){const p=((T.bot||{}).metrics)||{};s=p.total_return!=null?'chạy lùi: lợi nhuận +'+Math.round(p.total_return*100)+'% cả kỳ, sụt giảm lớn nhất '+n(p.maxdd*100)+'%, tổng lãi ÷ tổng lỗ '+n(p.pf,2):'xem trang web'}
  const c=(pv['20p']||{});return s+(c.da_cham?' · những lần nói ngược port: máy đúng '+c.may_dung+'/'+c.da_cham+' (sau 20 phiên)':'')}
function db(){const x=cur();if(!x)return rong();const t=x.luan,h0=x.ho_so,pb=t.phan_bien_may||{};let h=chonMa();
  h+='<h2 style="margin-top:0">'+esc(t.ma)+': port nghĩ '+chip(CHP[t.chieu]||0)+'</h2>';
  h+=h0.chua_tra_loi.length?'<div class="flag">Máy nói ngược mà port CHƯA trả lời: '+h0.chua_tra_loi.map(k=>esc(B.ten_may[k]||k)).join(', ')+'. Chưa đưa vào danh mục trước khi trả lời.</div>':(h0.nguoc.length?'<div class="ok">Đã trả lời mọi máy nói ngược.</div>':'<div class="ok">Không máy nào nói ngược port.</div>');
  h+='<div class="grid"><div class="card"><h3 class="up">Lý do lạc quan</h3>'+list(t.bull)+'</div><div class="card"><h3 class="dn">Lý do thận trọng</h3>'+list(t.bear)+'</div></div>';
  h+='<h3>Từng máy nói gì</h3><div class="grid">'+['bot','tin','daily'].map(k=>{const m=h0.may[k],r=pb[k],rt=r&&typeof r==='object'?r.noi_dung:r;
    let bcx='';if(k==='tin')bcx=(m.bang_chung||[]).map(z=>'<li>'+esc(z.ngay)+' · '+chip(z.chieu)+' '+esc(z.tieu_de)+' <span class="mut">('+esc(z.muc==='mã'?'nói thẳng về mã':'nói về ngành')+')</span>'+(z.noi_bo?' <span class="nb">ZALO · chỉ dùng nội bộ</span>':'')+'</li>').join('');
    else bcx=(m.bang_chung||[]).map(z=>'<li>'+esc(z)+'</li>').join('');
    return '<div class="may'+(m.nguoc_port?' nguoc':'')+'"><b>'+esc(B.ten_may[k]||k)+'</b> '+chip(m.chieu)+'<div class="mut">'+esc(m.khung||'')+'</div><div class="mut">Độ tin cậy: '+esc(tinCay(k))+'</div><ul>'+(m.ly_do||[]).map(z=>'<li>'+esc(z)+'</li>').join('')+'</ul>'
      +(bcx?'<details><summary>Dựa trên</summary><ul>'+bcx+'</ul></details>':'')
      +(m.nguoc_port?'<div style="margin-top:6px"><b>Port trả lời:</b> '+(rt?esc(rt):'<span class="dn">chưa có</span>')+'</div>':'')+'</div>'}).join('')+'</div>';
  h+='<h3>Các vòng tranh luận</h3>'+((t.debate||[]).length?(t.debate.map(r=>'<div class="card"><span class="pill">vòng '+esc(r.vong)+'</span><span class="pill">'+esc(BEN[r.ben]||r.ben)+'</span><span class="mut">'+esc(r.ngay)+'</span><div style="white-space:pre-wrap">'+esc(r.noi_dung)+'</div></div>').join('')):'<span class="mut">chưa có</span>');
  return h}

/* ---------------- Lọc cơ bản ---------------- */
const PRESET={ben:{ny_lien:3,roe:15,np4:15},re:{pe_rel:0.8,ny:0},cl:{roe:20},dao:{ny:30,ny_truoc_am:1}};
let F={gtgd:5,roe:'',ny_lien:'',np4:'',ny:'',pe_rel:'',nganh:'',q:'',bo_chan:1,ny_truoc_am:0};
function loc(){const sec=[...new Set((B.loc||[]).map(r=>r.nganh).filter(Boolean))].sort();
  let h='<h2 style="margin-top:0">Lọc cơ bản <span class="mut">('+(B.loc||[]).length+' mã, từ BCTC 12 quý và dữ liệu quét thị trường bot đã có)</span></h2>'
  +'<div class="f"><button class="btn g" data-p="ben">Lợi nhuận tăng đều</button><button class="btn g" data-p="re">Rẻ hơn chính nó</button><button class="btn g" data-p="cl">Hiệu quả cao (ROE)</button><button class="btn g" data-p="dao">Lợi nhuận vừa quay đầu tăng</button><button class="btn g" data-p="xoa">Xoá lọc</button></div>'
  +'<div class="f" style="margin-top:8px">'
  +'<label>Giá trị giao dịch ≥ <input type="number" id="f_gtgd" value="'+F.gtgd+'"> tỷ/phiên</label><label>ROE ≥ <input type="number" id="f_roe" value="'+F.roe+'">%</label>'
  +'<label>Lợi nhuận tăng liền ≥ <input type="number" id="f_ny_lien" value="'+F.ny_lien+'"> quý</label><label>Lợi nhuận 4 quý ≥ <input type="number" id="f_np4" value="'+F.np4+'">%</label>'
  +'<label>Lợi nhuận quý gần nhất ≥ <input type="number" id="f_ny" value="'+F.ny+'">%</label><label>P/E ÷ mức thường thấy 3 năm ≤ <input type="number" step="0.1" id="f_pe_rel" value="'+F.pe_rel+'"></label>'
  +'<label>Ngành <select id="f_nganh"><option value="">tất cả</option>'+sec.map(s=>'<option '+(s===F.nganh?'selected':'')+'>'+esc(s)+'</option>').join('')+'</select></label>'
  +'<label><input type="checkbox" id="f_bo_chan" '+(F.bo_chan?'checked':'')+'> bỏ mã bị chặn vì dòng tiền âm hoặc khó trả lãi vay</label><label>Tìm <input id="f_q" value="'+esc(F.q)+'" placeholder="mã/tên" style="width:110px"></label></div>';
  const ok=r=>{if(F.q){const q=F.q.toUpperCase();if(!(r.sym.includes(q)||String(r.ten||'').toUpperCase().includes(q)))return false}
    if(F.gtgd!==''&&!((r.gtgd||0)>=+F.gtgd))return false;if(F.roe!==''&&!((r.roe??-1e9)>=+F.roe))return false;
    if(F.ny_lien!==''&&!(r.ny_lien>=+F.ny_lien))return false;if(F.np4!==''&&!((r.np4_yoy??-1e9)>=+F.np4))return false;
    if(F.ny!==''&&!((r.ny??-1e9)>=+F.ny))return false;if(F.ny_truoc_am&&!((r.ny_truoc??1)<0))return false;
    if(F.pe_rel!==''&&!(r.pe>0&&r.pe_tv>0&&r.pe/r.pe_tv<=+F.pe_rel))return false;if(F.nganh&&r.nganh!==F.nganh)return false;
    if(F.bo_chan&&/^(CFO|ICR)/.test(r.chan||''))return false;return true};
  let rows=(B.loc||[]).filter(ok);rows.sort((a,b)=>{const x=a[sortK],y=b[sortK];return (x==null)-(y==null)||(x<y?-1:x>y?1:0)*sortD});
  const co=new Set((B.luan_diem||[]).map(x=>x.luan.ma));
  const C=[['sym','Mã'],['nganh','Ngành'],['gia','Giá'],['gtgd','GT giao dịch'],['quy','Quý'],['ny','LN quý'],['ny_lien','LN tăng liền'],['np4_yoy','LN 4 quý'],['rev4_yoy','DT 4 quý'],['roe','ROE'],['pe','P/E'],['pe_tv','P/E thường thấy'],['pb','P/B'],['pb_tv','P/B thường thấy'],['rs','Sức mạnh giá'],['trang_thai','Bot']];
  h+='<p class="mut">'+rows.length+' mã khớp'+(rows.length>300?' · hiện 300 dòng đầu':'')+'. "Thường thấy" = trung vị 12 quý. LN = lợi nhuận, DT = doanh thu, so cùng kỳ năm trước. Đây là bước sàng đầu vào, không phải kết luận: mã lọt sàng còn phải viết đủ luận điểm.</p>'
   +'<div class="scroll" style="max-height:70vh"><table><tr>'+C.map(c=>'<th data-k="'+c[0]+'">'+c[1]+(sortK===c[0]?(sortD>0?' ▲':' ▼'):'')+'</th>').join('')+'</tr>'
   +rows.slice(0,300).map(r=>'<tr><td><b>'+esc(r.sym)+'</b>'+(co.has(r.sym)?' <span class="pill">có luận điểm</span>':'')+(r.tim?' <span class="pill warn" title="'+esc(r.tim_vi)+'">lãi bất thường</span>':'')+'</td><td>'+esc(r.nganh)+'</td><td>'+n(r.gia,2)+'</td><td>'+n(r.gtgd)+'</td><td>'+esc(r.quy)+'</td><td>'+pct(r.ny)+'</td><td>'+n(r.ny_lien,0)+'</td><td>'+pct(r.np4_yoy)+'</td><td>'+pct(r.rev4_yoy)+'</td><td>'+n(r.roe)+'</td><td>'+n(r.pe)+'</td><td>'+n(r.pe_tv)+'</td><td>'+n(r.pb,2)+'</td><td>'+n(r.pb_tv,2)+'</td><td>'+n(r.rs,0)+'</td><td>'+esc(r.chan||r.trang_thai||'')+'</td></tr>').join('')+'</table></div>';
  return h}
function ganLoc(){document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{const p=b.dataset.p;F={gtgd:5,roe:'',ny_lien:'',np4:'',ny:'',pe_rel:'',nganh:F.nganh,q:'',bo_chan:1,ny_truoc_am:0};
    if(p!=='xoa'){const P=PRESET[p];if(P.ny_lien)F.ny_lien=P.ny_lien;if(P.roe)F.roe=P.roe;if(P.np4)F.np4=P.np4;if(P.pe_rel)F.pe_rel=P.pe_rel;if(P.ny!=null)F.ny=P.ny;if(P.ny_truoc_am)F.ny_truoc_am=1}else F.nganh='';ve()});
  ['gtgd','roe','ny_lien','np4','ny','pe_rel','nganh','q'].forEach(k=>{const e=$('#f_'+k);if(e)e.onchange=()=>{F[k]=e.value;ve()}});
  const c=$('#f_bo_chan');if(c)c.onchange=()=>{F.bo_chan=c.checked?1:0;ve()};
  document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(sortK===k)sortD=-sortD;else{sortK=k;sortD=-1};ve()})}

/* ---------------- Ai đoán đúng ---------------- */
function bangDC(o){return ['20p','60p','120p'].map(k=>{const a=(o||{})[k]||{};return '<td class="r">'+(a.da_cham?a.dung+'/'+a.da_cham:'—')+(a.cho?' <span class="mut">(chờ '+a.cho+')</span>':'')+'</td><td class="r">'+(a.ty_le!=null?n(a.ty_le)+'%':'—')+'</td><td class="r">'+pct(a.alpha_tb)+'</td><td class="w">'+esc(String(a.ket_luan||'').replace('ĐỦ MẠNH','chắc chắn hơn tung đồng xu').replace('CHƯA HƠN TUNG ĐỒNG XU','đúng nhiều hơn sai nhưng chưa chắc').replace('ĐANG SAI NHIỀU HƠN ĐÚNG','đang sai nhiều hơn đúng'))+'</td>'}).join('')}
function hoc(){const T=B.tin_cay||{},pv=T.port_vs_may||{},D=B.do_chinh_xac;let h='<h2 style="margin-top:0">Ai đoán đúng</h2>';
  if(D){const TN={port:'Port (luận điểm)',bot:'Bot',tin:'Bản tin sáng',daily:'Daily Market'},hd='<tr><th>Ai nói</th>'+['20','60','120'].map(k=>'<th class="r">'+k+' phiên: đúng/đã chấm</th><th class="r">Tỷ lệ</th><th class="r">Hơn VN-Index TB</th><th>Kết luận</th>').join('')+'</tr>';
    h+='<p class="mut">Mỗi luận điểm, mỗi bên ghi một lần khi bắt đầu nói và mỗi khi đổi ý. Sau 20/60/120 phiên chấm: mã hơn VN-Index thì bên nói "tăng" đúng. Chỉ kết luận "chắc chắn hơn tung đồng xu" khi đủ mẫu và tỷ lệ đúng vẫn trên 50% ngay cả ở cận dưới khoảng tin cậy 90%. Dưới 10 lần chấm thì chưa kết luận.</p>';
    h+='<div class="scroll"><table>'+hd+['port','bot','tin','daily'].map(k=>'<tr><td>'+TN[k]+'</td>'+bangDC(D[k])+'</tr>').join('')+'</table></div>';
    h+='<h3>Port đúng hơn khi các máy cùng ý?</h3><div class="scroll"><table>'+hd.replace('Ai nói','Số máy cùng ý')+['0','1','2','3'].map(k=>'<tr><td>'+k+'/3</td>'+bangDC((D.port_theo_dong_thuan||{})[k])+'</tr>').join('')+'</table></div>';
    const Tm=B.timing||{};h+='<p>Mục tiêu đã kết thúc: '+n(Tm.da_dong||0,0)+' · chạm '+n(Tm.dat||0,0)+' · bỏ luận điểm '+n(Tm.vo_hieu||0,0)+' · hết hạn '+n(Tm.het_han||0,0)+(Tm.lech_tb!=null?' · đến lệch trung bình '+n(Tm.lech_tb)+' phiên so với dự kiến (dương = chậm hơn)':'')+'</p>'}
  h+='<h3>Những lần máy nói ngược port</h3><p class="mut">Mỗi lần một máy nói ngược port, sổ ghi giá mã và VN-Index lúc đó; sau 20 và 60 phiên xem ai đúng.</p>';
  h+='<div class="scroll"><table><tr><th>Máy</th><th class="r">Số lần</th><th>20 phiên: port đúng / máy đúng</th><th>60 phiên: port đúng / máy đúng</th><th>Máy tự chấm</th></tr>'+['bot','tin','daily'].map(k=>{const o=pv[k]||{},a=o['20p']||{},b=o['60p']||{};
    return '<tr><td>'+esc(B.ten_may[k]||k)+'</td><td class="r">'+n(o.so_lan||0,0)+'</td><td>'+(a.da_cham?a.port_dung+' / '+a.may_dung:'—')+'</td><td>'+(b.da_cham?b.port_dung+' / '+b.may_dung:'—')+'</td><td class="w">'+esc(tinCay(k))+'</td></tr>'}).join('')+'</table></div>';
  const kc=T.kiem_chung_port||{};h+='<p>Mốc code tự chấm của port: đúng '+n(kc.dung||0,0)+' / '+n(kc.da_cham||0,0)+' mốc đã chấm.</p>';
  const so=(B.so_bat_dong||[]).slice().reverse();h+='<details class="card"><summary>Sổ các lần nói ngược ('+so.length+')</summary>'+(so.length?'<div class="scroll"><table><tr><th>Ngày</th><th>Mã</th><th>Máy</th><th>Port</th><th>Máy nói</th><th>Vì sao máy nói vậy</th><th class="r">Hơn VN-Index 20 phiên</th><th class="r">60 phiên</th></tr>'+so.map(r=>'<tr><td>'+esc(r.ngay)+'</td><td><b>'+esc(r.ma)+'</b></td><td>'+esc(B.ten_may[r.may]||r.may)+'</td><td>'+chip(r.chieu_port)+'</td><td>'+chip(r.chieu_may)+'</td><td class="w">'+esc(r.ly_do_may)+'</td><td class="r">'+pct(r.vuot_20p)+(r.port_dung_20p!=null?(r.port_dung_20p?' port đúng':' máy đúng'):'')+'</td><td class="r">'+pct(r.vuot_60p)+(r.port_dung_60p!=null?(r.port_dung_60p?' port đúng':' máy đúng'):'')+'</td></tr>').join('')+'</table></div>':'<span class="mut">chưa có lần nào</span>')+'</details>';
  return h}

function ve(){const L=B.luan_diem||[];if(L.length&&(!chon||!L.find(x=>x.luan.ma===chon)))chon=(L.find(x=>x.luan.trang_thai==='trong_port')||L[0]).luan.ma;veTabs();const f={dm,gl,so,bc,nd,db,loc,hoc}[tab]||dm;$('#app').innerHTML=f();if(tab==='loc')ganLoc();const s=$('#chon');if(s)s.onchange=()=>{chon=s.value;ve()}}
fetch('/port/data').then(r=>r.json().then(j=>{if(!r.ok)throw new Error(j.loi||r.status);return j})).then(j=>{B=j;
  const nh=j.nhac||{};$('#meta').textContent='Dữ liệu đến phiên '+(j.asof||'?')+' · đèn thị trường '+(j.den||'?')+' · bản tin sáng '+((j.nguon||{}).tin_so_ban||0)+' bản · Daily '+((j.nguon||{}).daily_ngay||'?')+(nh.ky_review?' · kỳ review gần nhất '+nh.ky_review:'')+' · dựng lúc '+String(j.cap_nhat||'').replace('T',' ').slice(0,16);ve()})
 .catch(e=>{$('#app').innerHTML='<b>Chưa đọc được gói port.</b> '+esc(e.message)});
</script></body></html>`
