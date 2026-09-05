/* ============================================================================
   CHỐNG CHÈN MÃ ĐỘC (XSS) — bắt buộc cho MỌI chữ do người nhập.

   Đường tấn công có thật, không phải giả định. Chuỗi ba bước:
     1. `manual.json` nằm trong repo PUBLIC. Ai có quyền ghi repo — hoặc lỡ để lộ
        mã truy cập GitHub — đều nhét được nội dung vào ô ghi chú.
     2. Ô ghi chú trước đây được dán thẳng vào trang bằng `${w.note}`. Nhét vào đó
        một thẻ <img onerror=...> là mã lạ chạy ngay trong trang.
     3. Trang lưu MÃ TRUY CẬP GITHUB của anh Sơn trong localStorage. Mã lạ chạy
        cùng nguồn thì đọc được nó, và đọc được là ghi được vào repo.

   Tức là một dòng ghi chú có thể đổi thành quyền ghi cả repo. Bịt ở bước 2:
   mọi chữ do người nhập phải đi qua hàm này trước khi vào HTML.

   Nguyên tắc: dữ liệu KHÔNG BAO GIỜ được tự biến thành mã. Kể cả dữ liệu của
   chính mình — vì hôm nay là của mình, ngày mai là của file bị sửa.
   ========================================================================== */
function esc(x) {
  if (x == null) return '';
  return String(x)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
/* dùng cho chữ nằm trong thuộc tính HTML (value=", title=") — nghiêm hơn một bậc */
function escA(x) { return esc(x).replace(/`/g, '&#96;'); }

const D = JSON.parse(document.getElementById('DATA').textContent);
document.getElementById('asof').textContent = D.asof;

/* ---------- THANH LIEN HE — sua dung o day, khong sua cho nao khac ---------- */
const LIENHE = {
  ten:      'Nguyễn Hoàng Sơn',
  sdt:      '0559 562 157',
  zalo:     '0559562157',
  chuc:     '',              // de TRONG thi ca chu lan dau gach doc tu an
  nhom:     '',              // link nhom — de TRONG thi nut tu an
  nhom_ten: 'Vào nhóm',
};
(function veLienHe(){
  const q = id => document.getElementById(id);
  const url = 'https://zalo.me/' + LIENHE.zalo;
  q('cbNm').textContent = LIENHE.ten;
  // Bo chuc danh thi phai an CA dau gach doc dung truoc no, khong thi con mot
  // vach dung tro tro giua so dien thoai va nut Zalo.
  const role = q('cbRole');
  role.textContent = LIENHE.chuc;
  role.style.display = LIENHE.chuc ? '' : 'none';
  const sep = role.previousElementSibling;
  if (sep && sep.classList.contains('cbsep')) sep.style.display = LIENHE.chuc ? '' : 'none';
  const ph = q('cbPh'); ph.textContent = LIENHE.sdt; ph.href = url;
  q('cbCta').href = url;
  if (LIENHE.nhom) {
    const a = document.createElement('a');
    a.className = 'cbcta ghost'; a.href = LIENHE.nhom;
    a.target = '_blank'; a.rel = 'noopener noreferrer';
    a.textContent = LIENHE.nhom_ten + ' \u2192';
    q('cbActs').insertAdjacentElement('afterbegin', a);
  }
})();

/* ---------- helpers ---------- */
const pct = (x,d=1)=> (x*100).toFixed(d)+'%';
const sg  = (x,d=1)=> (x>=0?'+':'')+(x*100).toFixed(d)+'%';
const num = (x,d=0)=> x.toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d});
const vnd = x => (Math.abs(x)>=1e9? (x/1e9).toFixed(2)+' tỷ' : (x/1e6).toFixed(0)+' tr');
const cls = x => x>=0?'pos':'neg';
const el  = (t,c,h)=>{const e=document.createElement(t); if(c)e.className=c; if(h!=null)e.innerHTML=h; return e;};
const CV = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const LIGHTVAR = {XANH:'--good', VANG:'--warn', CAM:'--serious', DO:'--critical'};
const LIGHTNAME = {XANH:'Xanh', VANG:'Vàng', CAM:'Cam', DO:'Đỏ'};

/* ---------- line chart with crosshair ---------- */
function lineChart(host, opt){
  const W=1000, H=opt.h||300, P={t:14,r:16,b:26,l:56};
  const box=el('div','chartbox'); host.appendChild(box);
  const tip=el('div','tip'); box.appendChild(tip);
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`); svg.setAttribute('preserveAspectRatio','none');
  svg.style.height=H+'px'; box.appendChild(svg);
  const S=opt.series, n=S[0].v.length;
  let lo=Infinity, hi=-Infinity;
  S.forEach(s=>s.v.forEach(y=>{if(y==null)return; if(y<lo)lo=y; if(y>hi)hi=y;}));
  if(opt.min!=null) lo=Math.min(lo,opt.min);
  const pad=(hi-lo)*0.08||0.1; lo-=pad; hi+=pad;
  const X=i=> P.l + i*(W-P.l-P.r)/(n-1);
  const Y=y=> P.t + (hi-y)*(H-P.t-P.b)/(hi-lo);
  const NS='http://www.w3.org/2000/svg';
  const mk=(t,a)=>{const e=document.createElementNS(NS,t); for(const k in a)e.setAttribute(k,a[k]); return e;};
  // gridlines
  const ticks=5;
  for(let k=0;k<=ticks;k++){
    const y=lo+(hi-lo)*k/ticks;
    svg.appendChild(mk('line',{x1:P.l,x2:W-P.r,y1:Y(y),y2:Y(y),stroke:CV('--line'),'stroke-width':1,'vector-effect':'non-scaling-stroke'}));
    const t=mk('text',{x:P.l-8,y:Y(y)+4,'text-anchor':'end',fill:CV('--text-muted'),'font-size':11});
    t.textContent=opt.fmtY?opt.fmtY(y):y.toFixed(2); svg.appendChild(t);
  }
  // x labels
  (opt.xticks||[]).forEach(([i,lab])=>{
    const t=mk('text',{x:X(i),y:H-6,'text-anchor':'middle',fill:CV('--text-muted'),'font-size':11});
    t.textContent=lab; svg.appendChild(t);
  });
  S.forEach(s=>{
    let d='',started=false;
    s.v.forEach((y,i)=>{ if(y==null){started=false;return;} d+=(started?'L':'M')+X(i).toFixed(1)+' '+Y(y).toFixed(1)+' '; started=true; });
    if(s.fill){
      const a=mk('path',{d:d+`L${X(n-1)} ${Y(lo)} L${X(0)} ${Y(lo)} Z`,fill:CV(s.color),opacity:.14,stroke:'none'});
      svg.appendChild(a);
    }
    svg.appendChild(mk('path',{d,fill:'none',stroke:CV(s.color),'stroke-width':2,'vector-effect':'non-scaling-stroke','stroke-linejoin':'round','stroke-linecap':'round'}));
  });
  const cross=mk('line',{y1:P.t,y2:H-P.b,stroke:CV('--text-muted'),'stroke-width':1,'vector-effect':'non-scaling-stroke',opacity:0});
  svg.appendChild(cross);
  const dots=S.map(s=>{const c=mk('circle',{r:4.5,fill:CV(s.color),stroke:CV('--surface-1'),'stroke-width':2,opacity:0}); svg.appendChild(c); return c;});
  box.addEventListener('pointermove',ev=>{
    const r=box.getBoundingClientRect();
    const px=(ev.clientX-r.left)/r.width*W;
    let i=Math.round((px-P.l)/((W-P.l-P.r)/(n-1)));
    i=Math.max(0,Math.min(n-1,i));
    cross.setAttribute('x1',X(i)); cross.setAttribute('x2',X(i)); cross.setAttribute('opacity',.5);
    let html='<b>'+(opt.labels?opt.labels[i]:i)+'</b>';
    S.forEach((s,k)=>{
      const y=s.v[i];
      dots[k].setAttribute('opacity', y==null?0:1);
      if(y!=null){ dots[k].setAttribute('cx',X(i)); dots[k].setAttribute('cy',Y(y)); }
      html+=`<div style="display:flex;gap:8px;align-items:center;margin-top:3px"><span style="width:9px;height:9px;border-radius:3px;background:${CV(s.color)};display:inline-block"></span>${s.name}: <b>${y==null?'—':(opt.fmtV?opt.fmtV(y):y.toFixed(2))}</b></div>`;
    });
    tip.innerHTML=html; tip.style.opacity=1;
    const tw=tip.offsetWidth, left=Math.min(Math.max(0,ev.clientX-r.left-tw/2), r.width-tw);
    tip.style.left=left+'px'; tip.style.top='6px';
  });
  box.addEventListener('pointerleave',()=>{tip.style.opacity=0;cross.setAttribute('opacity',0);dots.forEach(d=>d.setAttribute('opacity',0));});
  return box;
}

/* ---------- bar chart ---------- */
function barChart(host, items, opt={}){
  const W=1000, H=opt.h||240, P={t:16,r:12,b:40,l:56};
  const box=el('div','chartbox'); host.appendChild(box);
  const tip=el('div','tip'); box.appendChild(tip);
  const NS='http://www.w3.org/2000/svg';
  const mk=(t,a)=>{const e=document.createElementNS(NS,t); for(const k in a)e.setAttribute(k,a[k]); return e;};
  const svg=mk('svg',{viewBox:`0 0 ${W} ${H}`,preserveAspectRatio:'none'}); svg.style.height=H+'px'; box.appendChild(svg);
  const vals=items.map(d=>d.v);
  let lo=Math.min(0,...vals), hi=Math.max(0,...vals); const pad=(hi-lo)*.12||1; hi+=pad; if(lo<0) lo-=pad;
  const Y=v=>P.t+(hi-v)*(H-P.t-P.b)/(hi-lo);
  const bw=(W-P.l-P.r)/items.length;
  for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4;
    svg.appendChild(mk('line',{x1:P.l,x2:W-P.r,y1:Y(v),y2:Y(v),stroke:CV('--line'),'stroke-width':1,'vector-effect':'non-scaling-stroke'}));
    const t=mk('text',{x:P.l-8,y:Y(v)+4,'text-anchor':'end',fill:CV('--text-muted'),'font-size':11}); t.textContent=opt.fmtY?opt.fmtY(v):v.toFixed(0); svg.appendChild(t);}
  items.forEach((d,i)=>{
    const x=P.l+i*bw+bw*0.18, w=bw*0.64;
    const y0=Y(0), y1=Y(d.v); const top=Math.min(y0,y1), h=Math.max(2,Math.abs(y1-y0));
    const col=d.color?CV(d.color):(d.v>=0?CV('--good'):CV('--critical'));
    const r=mk('rect',{x,y:top,width:w,height:h,fill:col,rx:4});
    r.style.cursor='pointer'; svg.appendChild(r);
    const t=mk('text',{x:x+w/2,y:H-22,'text-anchor':'middle',fill:CV('--text-muted'),'font-size':11}); t.textContent=d.k; svg.appendChild(t);
    if(opt.showVal!==false){const vt=mk('text',{x:x+w/2,y:(d.v>=0?top-6:top+h+13),'text-anchor':'middle',fill:CV('--text-secondary'),'font-size':11,'font-weight':600});
      vt.textContent=opt.fmtV?opt.fmtV(d.v):d.v.toFixed(1); svg.appendChild(vt);}
    r.addEventListener('pointerenter',ev=>{
      tip.innerHTML=`<b>${d.k}</b><div>${opt.label||'Giá trị'}: <b>${opt.fmtV?opt.fmtV(d.v):d.v}</b></div>${d.note?'<div class="muted">'+d.note+'</div>':''}`;
      tip.style.opacity=1; const br=box.getBoundingClientRect();
      tip.style.left=Math.min(Math.max(0,ev.clientX-br.left-70),br.width-160)+'px'; tip.style.top='0px';});
    r.addEventListener('pointerleave',()=>tip.style.opacity=0);
  });
  svg.appendChild(mk('line',{x1:P.l,x2:W-P.r,y1:Y(0),y2:Y(0),stroke:CV('--text-muted'),'stroke-width':1.5,'vector-effect':'non-scaling-stroke'}));
  return box;
}
