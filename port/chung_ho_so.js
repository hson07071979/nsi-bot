/* ===== PHẦN DÙNG CHUNG: trang /port (thẻ mã) và /port/ho-so (Hồ sơ doanh nghiệp) — 28/10/2026 =====
   build.py chèn file này vào chỗ đánh dấu CHUNG_JS của hai trang trước khi đẩy KV.
   Cần sẵn: esc(s), n(v,d), pct(v). */
const VT={thuong_nguon:'Thượng nguồn',trung_nguon:'Trung nguồn',ha_nguon:'Hạ nguồn',tich_hop:'Tích hợp chuỗi',tai_chinh:'Trung gian tài chính',ha_tang:'Hạ tầng'};
const XH={tang:['tăng','▲'],giam:['giảm','▼'],ngang:['đi ngang','●'],'thiếu':['chưa có số','?']};
function ttCls(tt){return tt==='THUẬN'?'up':tt==='NGHỊCH'?'dn':'mut'}
function ttBadge(t,nho){if(!t)return '<span class="badge mut">chưa có hồ sơ</span>';return '<span class="badge '+ttCls(t.tong)+(nho?' nho':'')+'">'+(t.tong==='THUẬN'?'▲ ':t.tong==='NGHỊCH'?'▼ ':'● ')+esc(t.tong)+'</span>'}
function sec(so,ten,noi){return '<section class="sec"><h3><span class="so">'+so+'</span>'+ten+'</h3>'+noi+'</section>'}
function para(s){return s?'<p>'+esc(s)+'</p>':''}
/* 1. Làm ăn gì + chuỗi giá trị */
function veLamGi(h,ng){if(!h)return '<p class="mut">Chưa có hồ sơ doanh nghiệp cho mã này — Claude sẽ viết ở đợt hồ sơ kế tiếp.</p>';const c=h.chuoi_gia_tri||{};
  return para(h.lam_gi)+'<div class="mini"><b>Tiền đến từ đâu</b>'+para(h.tien_tu_dau)+'</div>'
   +'<div class="flow"><div><b>Đầu vào</b>'+esc(c.dau_vao||'—')+'</div><div class="mui">→</div><div class="dn-box"><b>'+esc(h.ma)+' · '+esc(VT[h.vi_tri]||h.vi_tri||'')+'</b>'+esc(c.vi_tri||'')+'</div><div class="mui">→</div><div><b>Đầu ra</b>'+esc(c.dau_ra||'—')+'</div></div>'
   +(c.khac_doi_thu?'<div class="mini"><b>Khác đối thủ</b>'+para(c.khac_doi_thu)+'</div>':'')
   +(ng&&ng.chuoi?'<details><summary>Chuỗi giá trị cả ngành '+esc(ng.ten||'')+'</summary>'+para(ng.chuoi)+'</details>':'')
   +'<div class="mut nho">'+esc(h.mo_hinh||'')+' · cập nhật '+esc(h.cap_nhat||'')+' (BCTC '+esc(h.quy||'')+') · nguồn: '+esc((h.nguon||[]).join('; '))+'</div>'}
/* 4. Vĩ mô ủng hộ / chống */
function tdoi(b){if(b.thay_doi==null)return '';return ' ('+(b.thay_doi>0?'+':'')+n(b.thay_doi,b.do==='diem'?2:1)+(b.do==='diem'?' điểm':'%')+' / '+(b.kieu==='thang'?b.cua_so+' tháng':b.cua_so+' phiên')+')'}
function nhay(d){if(!d||d.r==null)return '<span class="mut">chưa đo'+(d&&d.n!=null?' ('+d.n+' mẫu)':'')+'</span>';
  const k=d.khop===true?'<b class="up">khớp</b>':d.khop===false?'<b class="dn">ngược</b>':'<span class="mut">chưa rõ</span>';return 'r '+(d.r>0?'+':'')+n(d.r,2)+' · t '+n(d.t,1)+' · '+k}
function veViMo(t){if(!t)return '<p class="mut">Chưa có hồ sơ → chưa chấm được vĩ mô.</p>';
  return '<div class="f">'+ttBadge(t)+'<span class="mut">tổng '+(t.diem>0?'+':'')+t.diem+' từ '+t.bien.length+' biến nhạy nhất'+(t.thieu?' · '+t.thieu+' biến chưa có số':'')+'</span></div>'
   +'<div class="scroll"><table><tr><th>Biến</th><th>Hôm nay</th><th>Với mã này</th><th>Vì sao</th><th>Máy đo từ 2019</th></tr>'
   +t.bien.map(b=>{const x=XH[b.xu_huong]||XH['thiếu'];return '<tr><td><b>'+esc(b.ten)+'</b><div class="mut nho">'+(b.tu_dong?'tự cào · '+esc(b.ngay_so||''):'cập nhật tay · '+esc(b.ngay_so||''))+'</div></td><td>'+x[1]+' '+x[0]+'<span class="mut nho">'+tdoi(b)+'</span></td><td><b class="'+ttCls(b.tt)+'">'+esc(b.tt)+'</b><div class="mut nho">biến tăng là '+(b.chieu>0?'tốt':'xấu')+'</div></td><td class="w">'+esc(b.kenh||'')+(b.tre?' <span class="mut nho">(trễ '+esc(b.tre)+')</span>':'')+(b.ly_do?'<div class="mut nho">'+esc(b.ly_do)+'</div>':'')+'</td><td class="nho">'+nhay(b.do_nhay)+'</td></tr>'}).join('')+'</table></div>'
   +'<p class="mut nho">Tăng/giảm = thay đổi trong cửa sổ so với dao động bình thường của chính biến đó (z ≥ 0,5). "Máy đo" = tương quan giữa thay đổi của biến và lợi suất hơn VN-Index của mã, cửa sổ 20 phiên từ 2019; "ngược" nghĩa là giá thật đi ngược điều hồ sơ viết.</p>'}
/* 5. Vĩ mô → vi mô → vĩ mô */
function veChuoi(h,t){const c=(t&&t.chuoi)||{};if(!h&&!c.vi_mo)return '<p class="mut">Chưa có.</p>';
  return '<div class="chain"><div><b>Vĩ mô → ngành → doanh nghiệp</b>'+esc((h&&h.vi_mo_xuong)||'')+(c.nganh?'<div class="mut">'+esc(c.nganh)+'</div>':'')+'</div>'
   +'<div><b>Doanh nghiệp → dẫn ngược lên vĩ mô</b>'+esc((h&&h.vi_mo_nguoc)||c.dan_nguoc_vi_mo||'')+'</div></div>'
   +(c.vi_mo?'<details><summary>Bản đồ vĩ mô đầy đủ trong luận điểm</summary>'+para(c.vi_mo)+'</details>':'')}
/* 2. Giá 1 năm + vùng nền + ngày mua */
function veGia(g,mua){if(!g||!g.gia||g.gia.length<2)return '<p class="mut">Chưa có chuỗi giá.</p>';
  const W=760,H=220,P=36,a=g.gia,v=a.filter(x=>x!=null),lo=Math.min(...v,g.nen_duoi)*0.98,hi=Math.max(...v)*1.02;
  const X=i=>P+i*(W-2*P)/(a.length-1),Y=y=>H-P-(y-lo)/(hi-lo)*(H-2*P);
  const path=a.map((y,i)=>y==null?'':(i&&a[i-1]!=null?'L':'M')+X(i).toFixed(1)+','+Y(y).toFixed(1)).join('');
  const i0=Math.max(0,g.ngay.indexOf(g.nen_tu));const band='<rect x="'+X(i0)+'" y="'+Y(g.nen_tren)+'" width="'+(X(a.length-1)-X(i0))+'" height="'+Math.max(2,Y(g.nen_duoi)-Y(g.nen_tren))+'" fill="var(--acc)" opacity=".18"/>';
  const id=g.ngay.indexOf(g.ngay_dinh);const dinh=id>=0?'<circle cx="'+X(id)+'" cy="'+Y(g.dinh)+'" r="4" fill="var(--dn)"/><text x="'+(X(id)+6)+'" y="'+(Y(g.dinh)+4)+'">đỉnh '+n(g.dinh,2)+'</text>':'';
  const m=(mua||[]).map(l=>{const i=g.ngay.indexOf(l.ngay);return i<0?'':'<line x1="'+X(i)+'" x2="'+X(i)+'" y1="'+P+'" y2="'+(H-P)+'" stroke="var(--up)" stroke-dasharray="3 3"/><text x="'+(X(i)+3)+'" y="'+(P+10)+'">mua '+esc(l.dot||'')+'</text>'}).join('');
  const gl=[lo,(lo+hi)/2,hi].map(y=>'<line x1="'+P+'" x2="'+(W-P)+'" y1="'+Y(y)+'" y2="'+Y(y)+'" stroke="var(--line)"/><text x="2" y="'+(Y(y)+4)+'">'+n(y,1)+'</text>').join('');
  return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" aria-label="Giá 1 năm và vùng nền">'+gl+band+'<path d="'+path+'" fill="none" stroke="var(--ink)" stroke-width="1.8"/>'+dinh+m
   +'<text x="'+P+'" y="'+(H-8)+'">'+esc(g.ngay[0])+'</text><text x="'+(W-P-64)+'" y="'+(H-8)+'">'+esc(g.ngay[g.ngay.length-1])+'</text></svg>'
   +'<div class="mut nho">Giá điều chỉnh 250 phiên · dải xanh = nền 30 phiên ('+n(g.nen_duoi,2)+'–'+n(g.nen_tren,2)+', rộng '+n((g.nen_tren/g.nen_duoi-1)*100,1)+'%) · cách đỉnh '+pct((a[a.length-1]/g.dinh-1)*100)+'</div>'}
/* ===== LUẬN ĐIỂM ĐẦY ĐỦ (29/10/2026) — cùng khuôn mọi mã TOP110, dùng ở thẻ port và trang hồ sơ ===== */
const LD_TT={nghien_cuu:'Đang nghiên cứu',trong_port:'Đang trong danh mục',theo_doi:'Theo dõi (TOP110)',loai:'Đã loại',dong:'Đã đóng'};
const LD_KHAU=[['vi_mo','Vĩ mô'],['nganh','Ngành'],['doanh_nghiep','Doanh nghiệp'],['mo_hinh_kd','Kiếm tiền bằng gì'],['lanh_dao','Ban lãnh đạo'],['chuoi_gia_tri','Vị trí trong chuỗi giá trị'],['dan_nguoc_vi_mo','Tác động ngược lại nền kinh tế']];
const LD_KH={quoc_te:['Quốc tế',10],vi_mo_vn:['Vĩ mô Việt Nam',15],nganh:['Ngành',15],doanh_nghiep:['Doanh nghiệp',15],gia_sai:['Vì sao giá sai',15]},LD_SO={dinh_gia:['Định giá',10],kqkd:['Kết quả kinh doanh',10],suc_khoe_tc:['Sức khỏe tài chính',10]};
const LD_GS=[['tin_xau','Tin xấu là gì'],['co_that_su_xau','Có thật sự xấu không'],['trang_thai','Tin xấu đang ở đâu'],['ky_vong_ngam','Giá đang ngầm giả định gì'],['nguoi_ban_can_bien','Ai đang bán'],['counter','Phản biện cùng trục'],['phep_thu','Phép thử tiếp theo']];
const LD_TC=[['catalyst','Catalyst'],['chi_truoc','Phải chi trước những gì'],['hoa_von','Điểm hòa vốn'],['dieu_kien_can','Điều kiện cần'],['dieu_kien_du','Điều kiện đủ'],['khi_nao_tien_ve','Khi nào tiền về'],['phan_bien','Phản biện']];
const LD_BEN={bull:'Phe lạc quan',bear:'Phe thận trọng',trong_tai:'Người phân xử',anh_son:'Anh Sơn',claude:'Claude'};
const LD_DK={a:'a. Lợi nhuận tăng là thật',b:'b. Tăng trưởng không chậm lại (PEG)',c:'c. Giảm vì thị trường/ngành',d:'d. Đã cân bằng'};
const LD_NHOM={giai_ngan:['Giải ngân','up'],can_them:['Cần thêm bằng chứng','warn'],giu_khong_mua:['Giữ, ngừng mua','mut'],loai:['Chưa vào danh sách','dn']};
const ldBo=s=>String(s==null?'':s).replace(/^(FACT|OBSERVATION|INTERPRETATION|HYPOTHESIS|CONFIRMATION)\s*:\s*/i,'');
function ldList(a){a=(a||[]).filter(Boolean);return a.length?'<ul>'+a.map(x=>'<li>'+esc(ldBo(typeof x==='string'?x:(x.noi_dung||'')))+(x&&x.bang_chung&&x.bang_chung.length?'<div class="mut nho">Dựa trên: '+x.bang_chung.map(b=>esc(ldBo(b))).join(' · ')+'</div>':'')+'</li>').join('')+'</ul>':'<span class="mut">—</span>'}
/* tìm mã trong danh sách giải ngân → {nhom, vi_sao, bon_dk, duoc_mua, thieu, qua_loc, loai_loc} */
function ldTrongDS(ds,ma){for(const k of ['giai_ngan','can_them','giu_khong_mua','loai']){const x=((ds||{})[k]||[]).find(z=>z.ma===ma);if(x)return Object.assign({nhom:k},x)}return null}
/* hộp kết luận: điểm, danh sách nào, vì sao chưa được chọn / còn thiếu gì, 4 điều kiện */
function ldKetLuan(t,d){const p=(t&&t.pitch_diem)||{};let h='<div class="ld-kl"><div class="f"><b class="ld-diem">'+(p.tong!=null?n(p.tong,0)+'/100':'chưa chấm')+'</b><span>'+esc(p.ket_luan||'chưa có kết luận')+'</span>'
   +'<span class="badge nho">'+esc(LD_TT[t.trang_thai]||t.trang_thai||'')+'</span>';
  if(d){const g=LD_NHOM[d.nhom]||['?','mut'];h+='<span class="badge nho '+g[1]+'">'+g[0]+'</span>'+(d.duoc_mua===true?'<span class="badge nho up">được mua</span>':d.duoc_mua===false?'<span class="badge nho dn">chưa mua</span>':'')}
  h+='</div>';
  const ly=[];if(t.trang_thai==='loai')ly.push('Claude đã loại sau debate'+(t.bai_hoc?': '+t.bai_hoc:''));
  if(d&&d.vi_sao)ly.push(d.vi_sao);if(d&&(d.thieu||[]).length&&!(d.vi_sao||'').includes('thiếu'))ly.push('luận điểm còn thiếu: '+d.thieu.join(', '));
  if(!d&&t.trang_thai!=='loai')ly.push('chưa có trong bảng lọc lượt này');
  if(ly.length)h+='<div class="ld-vs"><b>'+(d&&d.nhom==='giai_ngan'&&d.duoc_mua?'Vì sao được chọn':'Vì sao chưa được chọn / còn thiếu gì')+'</b><ul>'+ly.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>';
  const k=d&&d.bon_dk;if(k)h+='<div class="dk4">'+'abcd'.split('').map(c=>{const v=k[c]||{};return '<div><b class="'+(v.dat===true?'up':v.dat===false?'dn':'mut')+'">'+(v.dat===true?'✓ ':v.dat===false?'✗ ':'? ')+esc(LD_DK[c])+'</b><span class="mut">'+esc(v.cau||'chưa đo')+'</span></div>'}).join('')+'</div>';
  else if(t.trang_thai!=='loai')h+='<p class="mut nho">4 điều kiện chỉ đo cho mã có trong bảng lọc TOP110 / watchlist.</p>';
  return h+'</div>'}
function ldChuoi(t){const c=(t&&t.chuoi)||{};return '<div class="chain">'+LD_KHAU.map(k=>'<div><b>'+k[1]+'</b>'+(c[k[0]]?esc(ldBo(c[k[0]])):'<span class="warn">chưa viết</span>')+'</div>').join('')+'</div>'}
function ldY(t){return ldList(t.luan_diem)+'<div class="grid2"><div class="mini"><b>Định giá</b>'+para(t.dinh_gia)+'</div><div class="mini"><b>Khi nào bỏ luận điểm</b>'+para(t.vo_hieu)+'</div></div>'
   +'<div class="grid2"><div class="mini"><b class="up">Lý lẽ lạc quan</b>'+ldList(t.bull)+'</div><div class="mini"><b class="dn">Lý lẽ thận trọng</b>'+ldList(t.bear)+'</div></div>'}
function ldCatalyst(t){const c=t.the_catalyst;if(!c)return '';return '<div class="mini"><b>Thẻ catalyst</b></div><div class="chain">'+LD_TC.map(k=>c[k[0]]?'<div><b>'+k[1]+'</b>'+esc(c[k[0]])+'</div>':'').join('')+'</div>'
   +((c.moc_quy||[]).length?'<ul>'+c.moc_quy.map(m=>'<li><b>'+esc(m.quy)+'</b> — '+esc(m.moc)+'</li>').join('')+'</ul>':'')}
function ldDiem(t){const p=t.pitch_diem||{};if(p.tong==null)return '<p class="mut">Chưa chấm điểm.</p>';const k=p.khau||{},q=p.so||{},g=p.gia_sai||{};
  let h='<div class="grid2"><div class="mini"><b>Lập luận '+n(p.luan_diem_70,0)+'/70</b><ul>'+Object.keys(LD_KH).map(c=>'<li>'+LD_KH[c][0]+': '+n(k[c],0)+'/'+LD_KH[c][1]+'</li>').join('')+'</ul></div><div class="mini"><b>Số liệu '+n(p.so_30,0)+'/30</b><ul>'+Object.keys(LD_SO).map(c=>'<li>'+LD_SO[c][0]+': '+n(q[c],0)+'/'+LD_SO[c][1]+'</li>').join('')+'</ul>'+(p.ghi_chu?'<p class="mut nho">'+esc(p.ghi_chu)+'</p>':'')+'</div></div>';
  if(g.ket_luan||g.tin_xau)h+='<div class="mini"><b>Giá đã phản ánh hết tin xấu chưa? '+esc(g.ket_luan||'')+'</b></div><div class="chain">'+LD_GS.map(c=>g[c[0]]?'<div><b>'+c[1]+'</b>'+esc(g[c[0]])+'</div>':'').join('')+'</div>';
  return h}
function ldMoc(kc){kc=kc||[];if(!kc.length)return '<span class="warn">chưa có mốc</span>';return '<div class="scroll"><table><tr><th>Mốc</th><th>Nội dung</th><th>Trạng thái</th></tr>'+kc.map(k=>'<tr><td>'+esc(k.id)+'</td><td class="w">'+esc(k.noi_dung)+'</td><td>'+(k.ket_qua?'<b class="'+(k.ket_qua==='ĐÚNG'?'up':'dn')+'">'+esc(k.ket_qua)+'</b>'+(k.gia_tri!=null?' ('+n(k.gia_tri)+')':''):(k.trang_thai==='dong'?'đã chấm':'đang chờ'+(k.ghi_chu?' · '+esc(k.ghi_chu):'')))+'</td></tr>').join('')+'</table></div>'}
function ldDebate(t){const d=t.debate||[];if(!d.length)return '';return '<details><summary>Debate ('+d.length+' lượt)</summary><div class="chain">'+d.map(x=>'<div><b>'+esc(LD_BEN[x.ben]||x.ben)+' · '+esc(x.ngay||'')+'</b>'+esc(x.noi_dung)+'</div>').join('')+'</div></details>'}
/* cả luận điểm trong một thẻ, đánh số tiếp từ `so` */
function veLuanDu(t,d,kc,so){if(!t)return sec(so,'Luận điểm đầu tư','<p class="mut">Chưa có luận điểm.</p>');
  return sec(so,'Từ vĩ mô xuống doanh nghiệp',ldChuoi(t))
   +sec(so+1,'Luận điểm: các ý chính, định giá, lạc quan – thận trọng',ldY(t)+ldCatalyst(t)+ldDebate(t))
   +sec(so+2,'Điểm 70/30 · giá đã phản ánh hết tin xấu chưa',ldDiem(t))
   +sec(so+3,'Mốc để code tự chấm',ldMoc(kc||t.kiem_chung)+(t.bai_hoc?'<div class="mini"><b>Bài học</b>'+para(t.bai_hoc)+'</div>':''))}
/* giao diện chung theo màu của web NSI (tối mặc định, sáng khi máy để chế độ sáng) */
(function(){const css=`
:root{--bg:#111110;--card:#1a1a19;--card2:#232322;--ink:#ffffff;--ink2:#c3c2b7;--mut:#8b8a80;--line:#33322f;--acc:#3987e5;--up:#199e70;--dn:#e66767;--warn:#c98500;--chip:#232322}
@media (prefers-color-scheme:light){:root{--bg:#f7f7f5;--card:#ffffff;--card2:#f2f1ee;--ink:#0b0b0b;--ink2:#52514e;--mut:#7a7973;--line:#e2e1dc;--acc:#2a78d6;--up:#1baf7a;--dn:#e34948;--warn:#eda100;--chip:#f2f1ee}}
body{font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif!important;background:var(--bg)!important;color:var(--ink)!important}
.card{border-radius:14px!important}
.badge{display:inline-block;padding:3px 12px;border-radius:99px;font-weight:700;font-size:13px;background:var(--card2);border:1px solid var(--line)}
.badge.up{color:var(--up);border-color:var(--up)}.badge.dn{color:var(--dn);border-color:var(--dn)}.badge.nho{padding:0 7px;font-size:11px}
.sec{border-top:1px solid var(--line);padding:12px 0 4px}.sec h3{margin:0 0 8px;font-size:15px}.sec .so{display:inline-block;width:22px;height:22px;border-radius:99px;background:var(--acc);color:#fff;text-align:center;font-size:12px;line-height:22px;margin-right:8px}
.sec p{margin:4px 0 8px;color:var(--ink2)}.nho{font-size:12px}.mini{margin:6px 0}.mini b{display:block;font-size:12.5px;color:var(--mut)}
.flow{display:grid;grid-template-columns:1fr 18px 1fr 18px 1fr;gap:6px;align-items:stretch;margin:10px 0}.flow>div{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:13px;color:var(--ink2)}
.flow>div b{display:block;color:var(--ink);font-size:12.5px;margin-bottom:2px}.flow .mui{background:none;border:0;padding:0;align-self:center;text-align:center;color:var(--mut)}.flow .dn-box{border-color:var(--acc)}
@media (max-width:700px){.flow{grid-template-columns:1fr}.flow .mui{transform:rotate(90deg)}}
.hai{display:grid;grid-template-columns:260px minmax(0,1fr);gap:14px;align-items:start}.hai>div{min-width:0}.sec svg{max-width:100%}td.w{white-space:normal}@media (max-width:820px){.hai{grid-template-columns:1fr}}
.trai{position:sticky;top:8px;max-height:calc(100vh - 16px);overflow:auto}.trai input,.trai select{width:100%;margin-bottom:6px}
.nhom{font-size:11.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;margin:10px 0 4px}
.dong-ma{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:7px 9px;border-radius:9px;cursor:pointer;border:1px solid transparent}
.dong-ma:hover{background:var(--card2)}.dong-ma.on{background:var(--card2);border-color:var(--acc)}.dong-ma b{font-size:14px}.dong-ma .mut{font-size:12px}
.dau{font-size:20px;font-weight:800;margin:0}.tieu{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:4px 0 6px}
.gn{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin:8px 0}.gn div{background:var(--card2);border-radius:10px;padding:8px 10px}.gn b{display:block;font-size:18px}
.dk4{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px}.dk4 div{border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:13px}.dk4 div b{display:block}
.pitch{background:var(--card2);border-left:3px solid var(--acc);border-radius:8px;padding:10px 12px;color:var(--ink)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:4px 18px}.grid2 ul{margin:4px 0;padding-left:18px}.grid2 li,.sec li{margin:3px 0;color:var(--ink2)}
.chain{display:grid;gap:8px;margin:6px 0}.chain>div{border-left:3px solid var(--acc);padding:2px 0 2px 10px;color:var(--ink2);font-size:14px}.chain>div>b{display:block;font-size:12.5px;color:var(--mut)}
.ld-kl{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin:8px 0}.ld-diem{font-size:20px}.ld-vs{margin:8px 0}.ld-vs b{font-size:12.5px;color:var(--mut)}.ld-vs ul{margin:4px 0;padding-left:18px}
.warn{color:var(--warn)}.badge.warn{color:var(--warn);border-color:var(--warn)}
`;document.head.insertAdjacentHTML('beforeend','<style>'+css+'</style>')})();
