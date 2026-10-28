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
`;document.head.insertAdjacentHTML('beforeend','<style>'+css+'</style>')})();
