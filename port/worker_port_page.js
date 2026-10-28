/* ============================================================================
   TRANG /port — Lọc port · chỉ trang quản trị nsi-quantri

   BẢN 28/10/2026 — TRANG NẰM Ở KV, KHÔNG NẰM TRONG WORKER NỮA
     Workflow "Lọc port" (nsi-bot) đẩy 2 khoá lên KV binding SLIDES:
       port/bundle  gói dữ liệu (như cũ)
       port/html    chính trang /port (file port/trang_port.html trong repo)
     Từ nay sửa trang chỉ cần sửa port/trang_port.html — lượt "Lọc port" kế tiếp tự đẩy
     bản mới lên KV. Không phải dán lại Worker sau mỗi lần sửa trang. Đây là lần dán cuối.

   Cách dán (một lần):
     Trong Worker nsi-quantri, XOÁ toàn bộ khối port cũ (từ dòng
       export async function handlePort(req, env) {
     tới hết chuỗi PORT_HTML — dòng cuối là  </script></body></html>`  )
     rồi dán TOÀN BỘ file này vào đúng chỗ đó. Dòng định tuyến cũ giữ nguyên:
       if (ADMIN && (url.pathname === '/port' || url.pathname.startsWith('/port/'))) return handlePort(req, env)
     Nếu Worker dán trên dashboard một file và báo lỗi chữ `export`: bỏ chữ `export` ở đầu hàm handlePort.

   Riêng tư: chỉ đọc sau bước kiểm admin, không có đường công khai.
   Đường:
     GET /port        trang (KV port/html)
     GET /port/data   JSON gói (KV port/bundle)
   ========================================================================== */

export async function handlePort(req, env) {
  const url = new URL(req.url)
  const p = url.pathname.replace(/\/+$/, '') || '/port'
  if (req.method !== 'GET') return pErr(405, 'chỉ đọc')
  if (!env.SLIDES) return pErr(500, 'Worker chưa gắn KV binding SLIDES')
  if (p === '/port') {
    const html = await env.SLIDES.get('port/html', { type: 'text' })
    return new Response(html || PORT_CHO, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } })
  }
  if (p === '/port/data') {
    const v = await env.SLIDES.get('port/bundle', { type: 'text' })
    if (v === null) return pErr(404, 'chưa có gói port — chạy workflow "Lọc port" trong nsi-bot')
    return new Response(v, { headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } })
  }
  return pErr(404, 'không có đường này')
}

function pErr(code, msg) {
  return new Response(JSON.stringify({ loi: msg }), { status: code, headers: { 'content-type': 'application/json; charset=utf-8' } })
}

const PORT_CHO = '<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lọc port</title></head>'
  + '<body style="font:16px/1.6 system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px">'
  + '<h1>Lọc port</h1><p>Trang chưa có trên KV. Vào tab <b>Actions</b> của repo <b>nsi-bot</b>, chọn workflow <b>"Lọc port"</b>, '
  + 'bấm <b>Run workflow</b>. Chạy xong (khoảng 5–10 phút) tải lại trang này.</p></body></html>'
