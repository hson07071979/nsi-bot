/* ============================================================================
   TRANG /port — Lọc port (vòng học thứ tư của bộ máy NSI) · chỉ trang quản trị nsi-quantri
   Gắn giống /daily: trong serveSite(), sau bước kiểm admin:
     if (ADMIN && (url.pathname === '/port' || url.pathname.startsWith('/port/'))) return handlePort(req, env)
   và thêm ở đầu file Worker:  import { handlePort } from './port_page.js'   (hoặc dán cả file này vào cuối)

   Dữ liệu: KV binding SLIDES (đã có, namespace nsi-slides), khóa port/bundle — do workflow "Lọc port" của nsi-bot ghi.
   Không cần token mới. Dữ liệu port là RIÊNG TƯ: chỉ đọc sau bước kiểm admin, không có đường công khai.
   Đường:
     GET /port        trang
     GET /port/data   JSON gói (luận điểm + hồ sơ máy + sổ bất đồng + bảng lọc + bảng tin cậy)
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
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1f23;--mut:#6b6f76;--line:#e4e2dc;--acc:#1f5f8b;--up:#167a3e;--dn:#b42318;--warn:#a15c07;--chip:#eef2f6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:16px}a{color:var(--acc)}h1{font-size:22px;margin:4px 0}h2{font-size:18px;margin:20px 0 8px}h3{font-size:15px;margin:12px 0 6px}
.mut{color:var(--mut);font-size:13px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.pill{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;font-weight:600;background:var(--chip);margin-right:4px}
.up{color:var(--up)}.dn{color:var(--dn)}.warn{color:var(--warn)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}.tabs button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer}
.tabs button.on{background:var(--acc);border-color:var(--acc);color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px}
.chain{display:grid;gap:6px}.chain div{border-left:3px solid var(--acc);padding:2px 0 2px 10px}.chain b{display:block;font-size:12.5px;color:var(--mut)}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;vertical-align:top;white-space:nowrap}
td.w{white-space:normal;min-width:220px}th{cursor:pointer;user-select:none;position:sticky;top:0;background:var(--card)}
.may{border:1px solid var(--line);border-radius:10px;padding:10px 12px}.may.nguoc{border-color:var(--dn);border-width:2px}
.flag{background:#fdecea;color:var(--dn);border-radius:8px;padding:6px 10px;margin:6px 0;font-weight:600}
.ok{background:#e9f6ee;color:var(--up);border-radius:8px;padding:6px 10px;margin:6px 0}
input,select{font:inherit;padding:4px 8px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
input[type=number]{width:84px}.f{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}.f label{font-size:13px}
.btn{border:0;background:var(--acc);color:#fff;border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer}.btn.g{background:var(--chip);color:var(--ink)}
ul{margin:4px 0;padding-left:20px}details summary{cursor:pointer;font-weight:600}.nb{font-size:11px;color:var(--warn);font-weight:600}
</style></head><body><div class="wrap">
<div><h1>Lọc port</h1><div class="mut">Vòng học thứ tư của bộ máy: luận điểm port debate với Bot · NSI Tin · NSI Daily, cả bốn cùng bị chấm bằng giá thật · chỉ trang quản trị ·
<a href="/daily">Daily</a> · <a href="/tin">Bản tin sáng</a></div><div id="meta" class="mut"></div></div>
<div class="tabs" id="tabs"></div><div id="app" class="card">Đang tải…</div></div>
<script>
const $=s=>document.querySelector(s), esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TABS=[['dm','Danh mục & pitch'],['so','Sổ phân tích'],['db','Debate với máy'],['loc','Lọc cơ bản'],['hoc','Vòng học']];
const CH={1:['tăng','up'],'-1':['giảm','dn'],0:['trung lập','mut']}, CHP={tang:1,giam:-1,trung_lap:0};
const TT={nghien_cuu:'Đang nghiên cứu',trong_port:'Trong port',loai:'Đã loại',dong:'Đã đóng'};
const KHAU=[['vi_mo','Vĩ mô'],['nganh','Ngành'],['doanh_nghiep','Doanh nghiệp'],['mo_hinh_kd','Mô hình kinh doanh'],['lanh_dao','Lãnh đạo'],['chuoi_gia_tri','Vị trí trong chuỗi giá trị'],['dan_nguoc_vi_mo','Dẫn ngược lên vĩ mô']];
let B=null, tab='dm', chon=null, sortK='np4_yoy', sortD=-1;
try{tab=localStorage.getItem('port-tab')||'dm'}catch(e){}
const chip=c=>{const x=CH[String(c)]||CH[0];return '<span class="pill '+x[1]+'">'+x[0]+'</span>'};
const n=(v,d=1)=>v==null||v===''?'—':(typeof v==='number'?v.toLocaleString('vi-VN',{maximumFractionDigits:d}):esc(v));
const pct=v=>v==null?'—':'<span class="'+(v>0?'up':v<0?'dn':'')+'">'+(v>0?'+':'')+n(v)+'%</span>';
function hq(){const q=B.hieu_qua;if(!q)return '<div class="card"><h3>Hiệu quả thực</h3><span class="mut">Chưa có lệnh nào. Ghi từng đợt giải ngân vào port/so_lenh.json (nhánh port-data): ngày, mã, % vốn, giá khớp — hoặc nhắn Claude.</span></div>';
  return '<div class="card"><h3>Hiệu quả thực (từ sổ lệnh)</h3><div class="f"><span>NAV <b>'+n(q.nav,2)+'</b></span><span>Lãi/lỗ '+pct(q.lai_pct)+'</span><span>VN-Index cùng kỳ '+pct(q.vni_pct)+'</span><span>Vượt VN-Index '+pct(q.vuot_vni)+'</span><span>Đã giải ngân '+n(q.da_giai_ngan)+'% · tiền mặt '+n(q.tien_mat)+'%</span></div><div class="mut">Từ '+esc(q.tu_ngay)+' đến '+esc(q.den_ngay)+' · '+esc(q.ghi_chu)+'</div>'
  +'<div class="scroll"><table><tr><th>Mã</th><th>Vốn (%)</th><th>Giá vốn TB</th><th>Giá</th><th>Lãi/lỗ</th><th>% NAV</th><th>Số lần mua</th></tr>'+(q.vi_the||[]).map(v=>'<tr><td><b>'+esc(v.ma)+'</b></td><td>'+n(v.von)+'</td><td>'+n(v.gia_tb,2)+'</td><td>'+n(v.gia,2)+'</td><td>'+pct(v.lai_pct)+'</td><td>'+n(v.ty_trong_nav)+'</td><td>'+n(v.so_lan_mua,0)+'</td></tr>').join('')+'</table></div>'
  +((q.loi||[]).length?'<div class="flag">'+q.loi.map(esc).join('<br>')+'</div>':'')+'</div>'}
const MUC={mua:'up',ban:'dn',ngung:'dn',ra_soat:'dn',hoan:'warn',cho:'mut',giu:'up',cho_luot:'warn'};
function gn(){const T=B.trang_thai_tt||{},N=B.nhiet||{},L=(B.luan_diem||[]).filter(x=>x.giai_ngan&&x.giai_ngan.ty_trong_muc_tieu);if(!L.length&&!T.ten)return '';
  let h='<div class="card"><h3>Giải ngân & quản trị rủi ro</h3><div class="f"><span>Thị trường: <b>'+esc(T.ten||'?')+'</b> (VN-Index '+n(T.vni,1)+', '+n(T.dd)+'% so với đỉnh 250 phiên '+n(T.dinh_250,1)+')</span><span>Kế hoạch: <b>'+(T.so_dot||'?')+' đợt</b> '+(T.ty_le||[]).map(x=>Math.round(x*100)+'%').join('/')+'</span><span>Nhiệt danh mục: <b class="'+(N.vuot?'dn':'')+'">'+n(N.hien_tai,2)+'% NAV</b> (trần '+n(N.tran)+'%; khi đủ tỷ trọng tối đa '+n(N.khi_du_ty_trong,1)+'%)</span>'+(B.luot?'<span>Đang nắm <b>'+n(B.luot.dang_nam,0)+'/8</b> mã · mở mới 20 phiên qua: <b>'+n(B.luot.mo_gan,0)+'/2</b> · còn <b>'+n(B.luot.slot,0)+'</b> lượt'+(B.luot.uu_tien&&B.luot.uu_tien.length?' · ưu tiên: '+B.luot.uu_tien.map(esc).join(' → '):'')+'</span>':'')+'</div>'
  +'<p class="mut">Lớp danh mục (R40): chỉ mở mã mới khi VN-Index ≤ −10% so với đỉnh 250 phiên; tối đa 2 mã mới mỗi 20 phiên, xếp lượt theo điểm 70/30; tối đa 8 mã × 12,5% NAV. Lớp từng mã (R38, anh Sơn chốt 15/10): hoảng loạn (VNI ≤ −20%) 2 đợt 60/40, còn lại 3 đợt; đợt sau chỉ khi đi ngang 20 phiên (biên ≤ 8%, không tạo đáy mới); chạy +10% trước đợt 2 → mua nửa phần còn lại ngay, nửa khi hồi MA20; giá < giá vốn −7% → ngừng mua thêm, rà luận điểm; giá < giá vốn −15% → bán hết; VN-Index dưới mốc dừng → hoãn đợt mới; mỗi mã ≤ 12,5% NAV.</p>'
  +(N.vi_pham_tran_ma&&N.vi_pham_tran_ma.length?'<div class="flag">Vượt trần 12,5% NAV/mã: '+N.vi_pham_tran_ma.map(esc).join(', ')+'</div>':'')
  +'<div class="scroll"><table><tr><th>Mã</th><th>Mục tiêu %NAV</th><th>Đã giải ngân</th><th>Giá vốn</th><th>Lãi/lỗ</th><th>Ngừng mua</th><th>Bán</th><th>Điểm 70/30</th><th>Việc tiếp theo</th></tr>'
  +L.map(x=>{const g=x.giai_ngan,d=x.diem_70_30||{};return '<tr><td><b>'+esc(x.luan.ma)+'</b></td><td>'+n(g.ty_trong_muc_tieu)+'</td><td>'+n(g.da_giai_ngan)+'</td><td>'+n(g.gia_von,2)+'</td><td>'+pct(g.lai_lo_pct)+'</td><td>'+n(g.gia_ngung_mua,2)+'</td><td>'+n(g.gia_ban,2)+'</td><td><b>'+n(d.tong,0)+'</b> <span class="mut">('+n(d.pitch,0)+'+'+n(d.ket_qua,0)+')</span></td><td class="w"><b class="'+(MUC[g.muc]||'')+'">'+esc(g.hanh_dong)+'</b></td></tr>'}).join('')+'</table></div></div>';
  return h}
function d7030(x){const d=x.diem_70_30;if(!d)return '';const c=d.chi_tiet||{};
  return '<div class="grid"><div class="card"><h3>Pitch '+n(d.pitch,0)+'/70</h3><ul><li>Định giá so với chính nó: '+n(c.dinh_gia,0)+'/20 <span class="mut">(P/E, P/B ÷ trung vị 3 năm = '+n(c.dinh_gia_rel,2)+')</span></li><li>Trạng thái thị trường: '+n(c.thi_truong,0)+'/20</li><li>Độ chặt lập luận (checklist): '+n(c.lap_luan,0)+'/15</li><li>Vì sao thị trường định giá sai: '+n(c.dinh_gia_sai,0)+'/15'+(c.dinh_gia_sai_ly_do?' <span class="mut">— '+esc(c.dinh_gia_sai_ly_do)+'</span>':'')+'</li></ul></div>'
   +'<div class="card"><h3>Kết quả kinh doanh '+n(d.ket_qua,0)+'/30</h3><ul><li>LN 4 quý: '+n(c.loi_nhuan,0)+'/10</li><li>ROE: '+n(c.roe,0)+'/10</li><li>Mốc K2: '+n(c.k2,0)+'/10</li></ul><p class="mut">R39: tăng trưởng LN/DT gần như không dự báo được lợi suất (ai cũng thấy); định giá so với chính nó + trạng thái thị trường mới là phần có lợi thế.</p></div></div>'}
const KQ={'ĐẠT':'up','VÔ HIỆU':'dn','HẾT HẠN':'warn'};
function mucTieu(x){const M=x.muc_tieu_cham||[];if(!M.length)return '<span class="warn">chưa có mục tiêu + timing</span>';const R=Object.fromEntries((x.rr||[]).map(r=>[r.id,r.rr]));
  return '<div class="scroll"><table><tr><th>ID</th><th>Giá</th><th>Nguồn</th><th>Cách giá lúc ghi</th><th>Dự kiến</th><th>Hạn</th><th>R:R</th><th>XS chạm 60p</th><th>XS chạm 120p</th><th>Trạng thái</th><th>Timing</th></tr>'+M.map(m=>'<tr><td>'+esc(m.id)+'</td><td>'+n(m.gia,2)+'</td><td class="w">'+esc(m.nguon)+'</td><td>'+pct(m.cach_pct)+'</td><td>'+n(m.du_kien_phien,0)+' phiên</td><td>'+n(m.han_phien,0)+' phiên</td><td>'+n(R[m.id],2)+'</td><td>'+(m.p60!=null?n(m.p60*100,0)+'%':'—')+'</td><td>'+(m.p120!=null?n(m.p120*100,0)+'%':'—')+'</td><td>'
   +(m.trang_thai==='dong'?'<b class="'+(KQ[m.ket_qua]||'')+'">'+esc(m.ket_qua)+'</b> '+esc(m.ngay_dong||''):'mở · '+n(m.phien,0)+' phiên · tiến độ '+n(m.tien_do_pct)+'% · còn '+pct(m.con_cach_pct))+'</td><td>'
   +(m.lech_timing!=null?(m.lech_timing>0?'chậm '+m.lech_timing:'sớm '+(-m.lech_timing))+' phiên':'—')+'</td></tr>').join('')+'</table></div><p class="mut">Giá vô hiệu: '+n(x.luan.vo_hieu_gia,2)+'. Timing là dự đoán và được phép lệch — sổ ghi độ lệch để hiệu chỉnh dần. XS chạm = xác suất chạm trong 60/120 phiên theo độ biến động 60 phiên (R39: dự báo 50% → thực tế 51%).</p>'}
function sanSang(x){const s=x.san_sang;if(!s)return '';return '<div class="'+(s.ket_luan==='ĐỦ ĐỂ XUỐNG TIỀN'?'ok':'flag')+'">Sẵn sàng xuống tiền: '+esc(s.ket_luan)+' ('+s.dat+'/'+s.tong+' mục)</div><ul>'+s.muc.map(m=>'<li><b class="'+(m.dat?'up':'dn')+'">'+(m.dat?'✓':'✗')+'</b> '+esc(m.ten)+(m.ghi_chu?' <span class="mut">— '+esc(m.ghi_chu)+'</span>':'')+'</li>').join('')+'</ul>'+((s.dieu_kien_vao||[]).length?'<b>Điều kiện vào riêng của luận điểm</b><ul>'+s.dieu_kien_vao.map(m=>'<li><b class="'+(m.dat?'up':'dn')+'">'+(m.dat?'✓':'✗')+'</b> '+esc(m.ten)+' <span class="mut">— '+esc(m.ghi_chu)+'</span></li>').join('')+'</ul>':'<p class="mut">Không có điều kiện vào riêng.</p>')+'<p class="mut">Checklist do code kiểm cấu trúc lập luận, không phải AI tự chấm. Đủ checklist ≠ chắc thắng; tỷ lệ đúng thật nằm ở tab Vòng học.</p>'}
function list(a){a=(a||[]).filter(Boolean);return a.length?'<ul>'+a.map(x=>'<li>'+esc(typeof x==='string'?x:(x.noi_dung||JSON.stringify(x)))+(x&&x.nhan?' <span class="pill">'+esc(x.nhan)+'</span>':'')+'</li>').join('')+'</ul>':'<span class="mut">—</span>'}
function veTabs(){$('#tabs').innerHTML=TABS.map(t=>'<button class="'+(t[0]===tab?'on':'')+'" data-t="'+t[0]+'">'+t[1]+'</button>').join('');
  document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{tab=b.dataset.t;try{localStorage.setItem('port-tab',tab)}catch(e){};ve()})}
function chonMa(){const L=B.luan_diem||[];if(!L.length)return'';
  return '<div class="f" style="margin-bottom:8px"><label>Mã <select id="chon">'+L.map(x=>{const h=x.ho_so;return '<option '+(x.luan.ma===chon?'selected':'')+'>'+esc(x.luan.ma)+'</option>'}).join('')+'</select></label>'
  +L.map(x=>x.ho_so.chua_tra_loi.length?'<span class="pill dn">'+esc(x.luan.ma)+': chưa trả lời '+x.ho_so.chua_tra_loi.length+' máy</span>':'').join('')+'</div>'}
function cur(){return (B.luan_diem||[]).find(x=>x.luan.ma===chon)}
function rong(){return '<p><b>Chưa có luận điểm nào.</b> Anh nhắn Claude trong chat dự án (ví dụ "phân tích FPT cho port"). Claude viết luận điểm theo khuôn port/MAU_LUAN_DIEM.json, đẩy vào nhánh port-data, workflow tự dựng hồ sơ máy và chấm điểm.</p>'}

function dm(){const d=B.danh_muc||{};let h='<h2 style="margin-top:0">Danh mục & pitch</h2>';
  if(d.quan_diem)h+='<div class="card"><h3>Quan điểm đầu tư</h3><div>'+esc(d.quan_diem)+'</div></div>';
  if((d.vi_tri||[]).length)h+='<div class="scroll"><table><tr><th>Mã</th><th>Tỷ trọng</th><th>Vai trò</th><th>Lý do</th><th>Giá</th><th>T1</th><th>T2</th><th>Vô hiệu</th><th>Máy ngược chiều</th></tr>'+d.vi_tri.map(v=>{const x=(B.luan_diem||[]).find(z=>z.luan.ma===v.ma);
    return '<tr><td><b>'+esc(v.ma)+'</b></td><td>'+n(v.ty_trong)+'</td><td>'+esc(v.vai_tro)+'</td><td class="w">'+esc(v.ly_do)+'</td><td>'+(x?n(x.gia,2):'')+'</td>'+[0,1].map(i=>{const m=x&&(x.muc_tieu_cham||[])[i];return '<td>'+(m?n(m.gia,2)+' '+pct(m.cach_pct):'—')+'</td>'}).join('')+'<td>'+(x?n(x.luan.vo_hieu_gia,2):'')+'</td><td>'+(x?(x.ho_so.nguoc.map(m=>'<span class="pill dn">'+esc(m)+'</span>').join('')||'<span class="up">không</span>'):'<span class="warn">chưa có luận điểm</span>')+'</td></tr>'}).join('')+'</table></div>';
  if(d.pitch)h+='<div class="card"><h3>Pitch cho khách hàng</h3><div style="white-space:pre-wrap">'+esc(d.pitch)+'</div><p class="mut">Không trích tin nhóm Zalo kín. Kiểm tra quy định nội dung của công ty trước khi gửi.</p></div>';
  h+=gn();
  h+=hq();
  if((d.rui_ro||[]).length)h+='<div class="card"><h3>Rủi ro danh mục</h3>'+list(d.rui_ro)+'</div>';
  const L=B.luan_diem||[];h+='<h3>Toàn bộ luận điểm</h3>'+(L.length?'<div class="scroll"><table><tr><th>Mã</th><th>Trạng thái</th><th>Chiều</th><th>Giá</th><th>Bot</th><th>Tin</th><th>Daily</th><th>Thiếu khâu</th><th>Mục tiêu T1</th><th>Mục tiêu T2</th><th>Vô hiệu</th><th>Sẵn sàng</th><th>R:R T1</th><th>Vượt VNI 20p</th></tr>'+L.map(x=>{const m=x.ho_so.may;
    return '<tr><td><b>'+esc(x.luan.ma)+'</b></td><td>'+esc(TT[x.luan.trang_thai]||x.luan.trang_thai)+'</td><td>'+chip(CHP[x.luan.chieu]||0)+'</td><td>'+n(x.gia,2)+'</td>'+['bot','tin','daily'].map(k=>'<td>'+chip(m[k].chieu)+(m[k].nguoc_port?(x.ho_so.chua_tra_loi.includes(k)?' <b class="dn">!</b>':' <span class="mut">đã trả lời</span>'):'')+'</td>').join('')
    +'<td>'+(x.thieu.length?'<span class="warn">'+x.thieu.length+'</span>':'<span class="up">đủ</span>')+'</td>'+[0,1].map(i=>{const m=(x.muc_tieu_cham||[])[i];return '<td>'+(m?'<b>'+n(m.gia,2)+'</b> '+pct(m.cach_pct)+'<div class="mut">'+(m.trang_thai==='dong'?esc(m.ket_qua):'~'+n(m.du_kien_phien,0)+' phiên')+'</div>':'—')+'</td>'}).join('')+'<td>'+n(x.luan.vo_hieu_gia,2)+'</td><td>'+(x.san_sang?'<span class="'+(x.san_sang.ket_luan==='ĐỦ ĐỂ XUỐNG TIỀN'?'up':'warn')+'">'+x.san_sang.dat+'/'+x.san_sang.tong+'</span>':'—')+'</td><td>'+n(x.san_sang&&x.san_sang.r1,2)+'</td><td>'+pct(x.ket_qua&&x.ket_qua['20p'])+'</td></tr>'}).join('')+'</table></div>':rong());
  return h}

function so(){const x=cur();if(!x)return rong();const t=x.luan,h0=x.ho_so;let h=chonMa();
  h+='<h2 style="margin-top:0">'+esc(t.ma)+' <span class="mut">'+esc(h0.nganh||'')+'</span></h2><div>'+'<span class="pill">'+esc(TT[t.trang_thai]||t.trang_thai)+'</span>'+chip(CHP[t.chieu]||0)+'<span class="pill">kỳ hạn '+esc(t.ky_han||'—')+'</span><span class="pill">giá '+n(x.gia,2)+'</span><span class="mut">mở '+esc(t.ngay_mo||'')+' · cập nhật '+esc(t.cap_nhat||'')+'</span></div>';
  if(x.thieu.length)h+='<div class="flag">Chuỗi tư duy còn thiếu: '+x.thieu.map(esc).join(' · ')+'</div>';
  h+='<h3>Chuỗi vĩ mô → ngành → doanh nghiệp → dẫn ngược vĩ mô</h3><div class="chain">'+KHAU.map(k=>'<div><b>'+k[1]+'</b>'+(esc((t.chuoi||{})[k[0]])||'<span class="warn">chưa viết</span>')+'</div>').join('')+'</div>';
  h+='<h3>Luận điểm</h3>'+list(t.luan_diem);
  h+='<div class="grid"><div><h3>Định giá</h3>'+esc(t.dinh_gia||'—')+'</div><div><h3>Điều kiện vô hiệu</h3>'+esc(t.vo_hieu||'—')+'</div></div>';
  h+='<h3>Mục tiêu và timing (code chấm)</h3>'+mucTieu(x);
  h+='<h3>Luận điểm đủ để xuống tiền chưa?</h3>'+sanSang(x);
  h+='<h3>Điểm 70% pitching / 30% kết quả</h3>'+d7030(x);
  if(x.giai_ngan)h+='<h3>Giải ngân</h3><p><b class="'+(MUC[x.giai_ngan.muc]||'')+'">'+esc(x.giai_ngan.hanh_dong)+'</b></p>';
  h+='<h3>Mốc kiểm chứng (code chấm, không để AI tự chấm)</h3>'+((x.kiem_chung||[]).length?'<div class="scroll"><table><tr><th>ID</th><th>Nội dung</th><th>Loại</th><th>Trạng thái</th><th>Kết quả</th></tr>'+x.kiem_chung.map(k=>'<tr><td>'+esc(k.id)+'</td><td class="w">'+esc(k.noi_dung)+'</td><td>'+esc(k.loai)+(k.moc?' '+n(k.moc,2):'')+(k.quy?' '+esc(k.quy):'')+'</td><td>'+(k.trang_thai==='mo'?'mở'+(k.phien!=null?' · '+k.phien+'/'+(k.han_phien||'')+' phiên':'')+(k.ghi_chu?' · '+esc(k.ghi_chu):''):'đóng '+esc(k.ngay_dong||''))+'</td><td>'+(k.ket_qua?'<b class="'+(k.ket_qua==='ĐÚNG'?'up':'dn')+'">'+esc(k.ket_qua)+'</b>'+(k.gia_tri!=null?' ('+n(k.gia_tri)+')':''):'')+'</td></tr>').join('')+'</table></div>':'<span class="warn">chưa có mốc</span>');
  if(x.ket_qua)h+='<p>Từ ngày vào port '+esc(x.ket_qua.ngay_vao)+': vượt VN-Index sau 20 phiên '+pct(x.ket_qua['20p'])+' · sau 60 phiên '+pct(x.ket_qua['60p'])+'</p>';
  if(t.pitch)h+='<h3>Pitch</h3><div style="white-space:pre-wrap">'+esc(t.pitch)+'</div>';
  if(t.bai_hoc)h+='<h3>Bài học</h3><div>'+esc(t.bai_hoc)+'</div>';
  return h}

function tinCay(k){const T=B.tin_cay||{},pv=(T.port_vs_may||{})[k]||{};let s='';
  if(k==='tin'){const tt=(T.tin||{}).trong_tai;s=tt?'trọng tài đúng '+n(tt.ty_le_dung)+'% / '+tt.n+' lần chấm':'chưa có số chấm'}
  if(k==='daily'){const d=T.daily||{};s=d.da_cham?'sổ dự báo đúng '+d.dung+'/'+d.da_cham:'sổ dự báo chưa chấm dòng nào'}
  if(k==='bot'){const p=((T.bot||{}).metrics)||{};s=p.total_return!=null?'backtest PROD: lợi nhuận +'+Math.round(p.total_return*100)+'% (cả kỳ), DD '+n(p.maxdd*100)+'%, PF '+n(p.pf,2):'backtest PROD (xem trang web)'}
  const c=(pv['20p']||{});return s+(c.da_cham?' · khi bất đồng với port: máy đúng '+c.may_dung+'/'+c.da_cham+' (20 phiên)':'')}
function db(){const x=cur();if(!x)return rong();const t=x.luan,h0=x.ho_so,pb=t.phan_bien_may||{};let h=chonMa();
  h+='<h2 style="margin-top:0">'+esc(t.ma)+': port nói '+chip(CHP[t.chieu]||0)+'</h2>';
  h+=h0.chua_tra_loi.length?'<div class="flag">Máy ngược chiều mà port CHƯA trả lời: '+h0.chua_tra_loi.map(k=>esc(B.ten_may[k]||k)).join(', ')+'. Không đưa vào danh mục trước khi trả lời.</div>':(h0.nguoc.length?'<div class="ok">Đã trả lời mọi máy ngược chiều.</div>':'<div class="ok">Không máy nào ngược chiều port.</div>');
  h+='<div class="grid"><div class="card"><h3 class="up">Bull</h3>'+list(t.bull)+'</div><div class="card"><h3 class="dn">Bear</h3>'+list(t.bear)+'</div></div>';
  h+='<h3>Máy nói gì</h3><div class="grid">'+['bot','tin','daily'].map(k=>{const m=h0.may[k],r=pb[k],rt=r&&typeof r==='object'?r.noi_dung:r;
    let bc='';if(k==='tin')bc=(m.bang_chung||[]).map(z=>'<li>'+esc(z.ngay)+' · '+chip(z.chieu)+' '+esc(z.tieu_de)+' <span class="mut">('+esc(z.muc)+(z.xac_minh?', '+esc(z.xac_minh):'')+')</span>'+(z.noi_bo?' <span class="nb">ZALO · chỉ nội bộ</span>':'')+'</li>').join('');
    else bc=(m.bang_chung||[]).map(z=>'<li>'+esc(z)+'</li>').join('');
    return '<div class="may'+(m.nguoc_port?' nguoc':'')+'"><b>'+esc(B.ten_may[k]||k)+'</b> '+chip(m.chieu)+'<div class="mut">'+esc(m.khung||'')+'</div><div class="mut">Độ tin cậy: '+esc(tinCay(k))+'</div><ul>'+(m.ly_do||[]).map(z=>'<li>'+esc(z)+'</li>').join('')+'</ul>'
      +(bc?'<details><summary>Bằng chứng</summary><ul>'+bc+'</ul></details>':'')
      +(m.nguoc_port?'<div style="margin-top:6px"><b>Port phản biện:</b> '+(rt?esc(rt):'<span class="dn">chưa có</span>')+'</div>':'')+'</div>'}).join('')+'</div>';
  h+='<h3>Các vòng debate</h3>'+((t.debate||[]).length?(t.debate.map(r=>'<div class="card"><span class="pill">vòng '+esc(r.vong)+'</span><span class="pill">'+esc(r.ben)+'</span><span class="mut">'+esc(r.ngay)+'</span><div style="white-space:pre-wrap">'+esc(r.noi_dung)+'</div></div>').join('')):'<span class="mut">chưa có</span>');
  return h}

const PRESET={ben:{ny_lien:3,roe:15,np4:15},re:{pe_rel:0.8,ny:0},cl:{roe:20},dao:{ny:30,ny_truoc_am:1}};
let F={gtgd:5,roe:'',ny_lien:'',np4:'',ny:'',pe_rel:'',nganh:'',q:'',bo_chan:1,ny_truoc_am:0};
function loc(){const sec=[...new Set((B.loc||[]).map(r=>r.nganh).filter(Boolean))].sort();
  let h='<h2 style="margin-top:0">Lọc cơ bản <span class="mut">('+(B.loc||[]).length+' mã, dữ liệu bot đã có: BCTC 12 quý + quét thị trường)</span></h2>'
  +'<div class="f"><button class="btn g" data-p="ben">Tăng trưởng bền</button><button class="btn g" data-p="re">Rẻ so với lịch sử</button><button class="btn g" data-p="cl">Chất lượng cao</button><button class="btn g" data-p="dao">Lợi nhuận đảo chiều</button><button class="btn g" data-p="xoa">Xoá lọc</button></div>'
  +'<div class="f" style="margin-top:8px">'
  +'<label>GTGD ≥ <input type="number" id="f_gtgd" value="'+F.gtgd+'"> tỷ</label><label>ROE ≥ <input type="number" id="f_roe" value="'+F.roe+'">%</label>'
  +'<label>LN tăng liền ≥ <input type="number" id="f_ny_lien" value="'+F.ny_lien+'"> quý</label><label>LN 4 quý ≥ <input type="number" id="f_np4" value="'+F.np4+'">%</label>'
  +'<label>LN quý gần ≥ <input type="number" id="f_ny" value="'+F.ny+'">%</label><label>P/E ÷ trung vị 3 năm ≤ <input type="number" step="0.1" id="f_pe_rel" value="'+F.pe_rel+'"></label>'
  +'<label>Ngành <select id="f_nganh"><option value="">tất cả</option>'+sec.map(s=>'<option '+(s===F.nganh?'selected':'')+'>'+esc(s)+'</option>').join('')+'</select></label>'
  +'<label><input type="checkbox" id="f_bo_chan" '+(F.bo_chan?'checked':'')+'> bỏ mã bị chặn CFO/ICR</label><label>Tìm <input id="f_q" value="'+esc(F.q)+'" placeholder="mã/tên" style="width:110px"></label></div>';
  const ok=r=>{if(F.q){const q=F.q.toUpperCase();if(!(r.sym.includes(q)||String(r.ten||'').toUpperCase().includes(q)))return false}
    if(F.gtgd!==''&&!((r.gtgd||0)>=+F.gtgd))return false;if(F.roe!==''&&!((r.roe??-1e9)>=+F.roe))return false;
    if(F.ny_lien!==''&&!(r.ny_lien>=+F.ny_lien))return false;if(F.np4!==''&&!((r.np4_yoy??-1e9)>=+F.np4))return false;
    if(F.ny!==''&&!((r.ny??-1e9)>=+F.ny))return false;if(F.ny_truoc_am&&!((r.ny_truoc??1)<0))return false;
    if(F.pe_rel!==''&&!(r.pe>0&&r.pe_tv>0&&r.pe/r.pe_tv<=+F.pe_rel))return false;if(F.nganh&&r.nganh!==F.nganh)return false;
    if(F.bo_chan&&/^(CFO|ICR)/.test(r.chan||''))return false;return true};
  let rows=(B.loc||[]).filter(ok);rows.sort((a,b)=>{const x=a[sortK],y=b[sortK];return (x==null)-(y==null)||(x<y?-1:x>y?1:0)*sortD});
  const co=new Set((B.luan_diem||[]).map(x=>x.luan.ma));
  const C=[['sym','Mã'],['nganh','Ngành'],['gia','Giá'],['gtgd','GTGD'],['quy','Quý'],['ny','LN quý'],['ny_lien','LN tăng liền'],['np4_yoy','LN 4Q'],['rev4_yoy','DT 4Q'],['roe','ROE'],['pe','P/E'],['pe_tv','P/E tv'],['pb','P/B'],['pb_tv','P/B tv'],['rs','RS'],['trang_thai','Bot']];
  h+='<p class="mut">'+rows.length+' mã khớp'+(rows.length>300?' · hiện 300 dòng đầu':'')+'. "tv" = trung vị 12 quý. Đây là màn lọc đầu vào, không phải kết luận: mã lọt lưới cần đi đủ chuỗi tư duy ở Sổ phân tích.</p>'
   +'<div class="scroll" style="max-height:70vh"><table><tr>'+C.map(c=>'<th data-k="'+c[0]+'">'+c[1]+(sortK===c[0]?(sortD>0?' ▲':' ▼'):'')+'</th>').join('')+'</tr>'
   +rows.slice(0,300).map(r=>'<tr><td><b>'+esc(r.sym)+'</b>'+(co.has(r.sym)?' <span class="pill">có luận điểm</span>':'')+(r.tim?' <span class="pill warn" title="'+esc(r.tim_vi)+'">LN bất thường</span>':'')+'</td><td>'+esc(r.nganh)+'</td><td>'+n(r.gia,2)+'</td><td>'+n(r.gtgd)+'</td><td>'+esc(r.quy)+'</td><td>'+pct(r.ny)+'</td><td>'+n(r.ny_lien,0)+'</td><td>'+pct(r.np4_yoy)+'</td><td>'+pct(r.rev4_yoy)+'</td><td>'+n(r.roe)+'</td><td>'+n(r.pe)+'</td><td>'+n(r.pe_tv)+'</td><td>'+n(r.pb,2)+'</td><td>'+n(r.pb_tv,2)+'</td><td>'+n(r.rs,0)+'</td><td>'+esc(r.chan||r.trang_thai||'')+'</td></tr>').join('')+'</table></div>';
  return h}
function ganLoc(){document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{const p=b.dataset.p;F={gtgd:5,roe:'',ny_lien:'',np4:'',ny:'',pe_rel:'',nganh:F.nganh,q:'',bo_chan:1,ny_truoc_am:0};
    if(p!=='xoa'){const P=PRESET[p];if(P.ny_lien)F.ny_lien=P.ny_lien;if(P.roe)F.roe=P.roe;if(P.np4)F.np4=P.np4;if(P.pe_rel)F.pe_rel=P.pe_rel;if(P.ny!=null)F.ny=P.ny;if(P.ny_truoc_am)F.ny_truoc_am=1}else F.nganh='';ve()});
  ['gtgd','roe','ny_lien','np4','ny','pe_rel','nganh','q'].forEach(k=>{const e=$('#f_'+k);if(e)e.onchange=()=>{F[k]=e.value;ve()}});
  const c=$('#f_bo_chan');if(c)c.onchange=()=>{F.bo_chan=c.checked?1:0;ve()};
  document.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(sortK===k)sortD=-sortD;else{sortK=k;sortD=-1};ve()})}

function bangDC(o){return ['20p','60p','120p'].map(k=>{const a=(o||{})[k]||{};return '<td>'+(a.da_cham?a.dung+'/'+a.da_cham:'—')+(a.cho?' <span class="mut">(chờ '+a.cho+')</span>':'')+'</td><td>'+(a.ty_le!=null?n(a.ty_le)+'%':'—')+'</td><td>'+(a.wilson_thap!=null?n(a.wilson_thap)+'%':'—')+'</td><td>'+pct(a.alpha_tb)+'</td><td class="w">'+esc(a.ket_luan||'')+'</td>'}).join('')}
function dcHtml(){const D=B.do_chinh_xac;if(!D)return '';const TN={port:'Port (luận điểm)',bot:'Bot',tin:'NSI Tin',daily:'NSI Daily'},hd='<tr><th>Nguồn</th>'+['20','60','120'].map(k=>'<th>'+k+'p đúng/chấm</th><th>Tỷ lệ</th><th>Cận dưới 90%</th><th>Vượt VNI TB</th><th>Kết luận</th>').join('')+'</tr>';
  let h='<h3>AI đoán có đúng không — sổ dự đoán</h3><p class="mut">Mỗi luận điểm, mỗi nguồn ghi một dự đoán khi bắt đầu nói và khi đổi chiều; sau 20/60/120 phiên chấm: mã vượt VN-Index thì bên nói "tăng" đúng. "Đủ mạnh" khi cận dưới khoảng tin cậy 90% của tỷ lệ đúng vượt 50% — tức là chắc chắn hơn tung đồng xu. Mẫu dưới 10 chưa kết luận.</p>';
  h+='<div class="scroll"><table>'+hd+['port','bot','tin','daily'].map(k=>'<tr><td>'+TN[k]+'</td>'+bangDC(D[k])+'</tr>').join('')+'</table></div>';
  h+='<h3>Port đúng hơn khi máy đồng thuận?</h3><div class="scroll"><table>'+hd.replace('Nguồn','Số máy cùng chiều')+['0','1','2','3'].map(k=>'<tr><td>'+k+'/3</td>'+bangDC((D.port_theo_dong_thuan||{})[k])+'</tr>').join('')+'</table></div>';
  const S=D.so_mau||{},Tm=B.timing||{};h+='<p class="mut">Bộ dữ liệu cho mô hình học máy: '+n(S.tong||0,0)+' dự đoán ('+n(S.port||0,0)+' của port), '+n(S.da_cham_60p||0,0)+' đã đủ 60 phiên. Cần khoảng '+n(S.can_cho_mo_hinh||50,0)+' mẫu đã chấm trước khi dựng mô hình — trước đó mô hình sẽ học thuộc nhiễu.</p>';
  h+='<p>Mục tiêu đã đóng: '+n(Tm.da_dong||0,0)+' · đạt '+n(Tm.dat||0,0)+' · vô hiệu '+n(Tm.vo_hieu||0,0)+' · hết hạn '+n(Tm.het_han||0,0)+(Tm.lech_tb!=null?' · timing lệch TB '+n(Tm.lech_tb)+' phiên (dương = chậm hơn dự kiến)':'')+'</p>';
  return h}
function hoc(){const T=B.tin_cay||{},pv=T.port_vs_may||{};let h='<h2 style="margin-top:0">Vòng học — ai đáng tin ở đâu</h2>'+dcHtml()+'<h3>Port bất đồng với máy</h3><p class="mut">Mỗi lần máy ngược chiều port, sổ ghi giá mã và VN-Index lúc đó; sau 20 và 60 phiên chấm: mã vượt VN-Index thì bên nói "tăng" đúng. Mẫu dưới 10 lần thì chưa ra tỷ lệ — chưa kết luận được gì.</p>';
  h+='<div class="scroll"><table><tr><th>Máy</th><th>Số lần bất đồng</th><th>20 phiên: port đúng / máy đúng</th><th>60 phiên: port đúng / máy đúng</th><th>Máy tự chấm</th></tr>'+['bot','tin','daily'].map(k=>{const o=pv[k]||{},a=o['20p']||{},b=o['60p']||{};
    return '<tr><td>'+esc(B.ten_may[k]||k)+'</td><td>'+n(o.so_lan||0,0)+'</td><td>'+(a.da_cham?a.port_dung+' / '+a.may_dung+(a.ty_le_port_dung!=null?' ('+n(a.ty_le_port_dung)+'% port)':''):'—')+'</td><td>'+(b.da_cham?b.port_dung+' / '+b.may_dung+(b.ty_le_port_dung!=null?' ('+n(b.ty_le_port_dung)+'% port)':''):'—')+'</td><td class="w">'+esc(tinCay(k))+'</td></tr>'}).join('')+'</table></div>';
  const kc=T.kiem_chung_port||{};h+='<p>Mốc kiểm chứng của port: đúng '+n(kc.dung||0,0)+' / '+n(kc.da_cham||0,0)+' mốc đã chấm.</p>';
  const tt=T.tin||{};const ks=Object.keys(tt);if(ks.length)h+='<h3>NSI Tin tự chấm (T+4 vượt VN-Index)</h3><div class="scroll"><table><tr><th>Nhóm</th><th>Số lần</th><th>Tỷ lệ đúng</th></tr>'+ks.map(k=>'<tr><td>'+esc(k)+'</td><td>'+n(tt[k].n,0)+'</td><td>'+(tt[k].ty_le_dung==null?'—':n(tt[k].ty_le_dung)+'%')+'</td></tr>').join('')+'</table></div>';
  const so=(B.so_bat_dong||[]).slice().reverse();h+='<h3>Sổ bất đồng</h3>'+(so.length?'<div class="scroll"><table><tr><th>Ngày</th><th>Mã</th><th>Máy</th><th>Port</th><th>Máy nói</th><th>Lý do máy</th><th>Vượt VNI 20p</th><th>60p</th></tr>'+so.map(r=>'<tr><td>'+esc(r.ngay)+'</td><td><b>'+esc(r.ma)+'</b></td><td>'+esc(r.may)+'</td><td>'+chip(r.chieu_port)+'</td><td>'+chip(r.chieu_may)+'</td><td class="w">'+esc(r.ly_do_may)+'</td><td>'+pct(r.vuot_20p)+(r.port_dung_20p!=null?(r.port_dung_20p?' port':' máy'):'')+'</td><td>'+pct(r.vuot_60p)+(r.port_dung_60p!=null?(r.port_dung_60p?' port':' máy'):'')+'</td></tr>').join('')+'</table></div>':'<span class="mut">chưa có lần bất đồng nào</span>');
  return h}

function ve(){const L=B.luan_diem||[];if(L.length&&(!chon||!L.find(x=>x.luan.ma===chon)))chon=L[0].luan.ma;veTabs();const f={dm,so,db,loc,hoc}[tab]||dm;$('#app').innerHTML=f();if(tab==='loc')ganLoc();const s=$('#chon');if(s)s.onchange=()=>{chon=s.value;ve()}}
fetch('/port/data').then(r=>r.json().then(j=>{if(!r.ok)throw new Error(j.loi||r.status);return j})).then(j=>{B=j;
  $('#meta').textContent='Dữ liệu bot đến phiên '+(j.asof||'?')+' · đèn '+(j.den||'?')+' · NSI Tin '+((j.nguon||{}).tin_so_ban||0)+' bản · Daily '+((j.nguon||{}).daily_ngay||'?')+' · dựng lúc '+String(j.cap_nhat||'').replace('T',' ').slice(0,16);ve()})
 .catch(e=>{$('#app').innerHTML='<b>Chưa đọc được gói port.</b> '+esc(e.message)});
</script></body></html>`
