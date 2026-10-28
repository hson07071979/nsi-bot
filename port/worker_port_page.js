
/* ============================================================================
   TRANG /port — Lọc port · chỉ trang quản trị nsi-quantri

   BẢN 28/10/2026 (tối) — MỌI TRANG CỦA PORT NẰM Ở KV, KHÔNG NẰM TRONG WORKER
     Workflow "Lọc port" (nsi-bot) đẩy lên KV binding SLIDES:
       port/html            trang /port            (port/trang_port.html)
       port/bundle          dữ liệu /port/data
       port/page/<tên>      trang /port/<tên>      (vd port/page/ho-so = Hồ sơ doanh nghiệp)
       port/page/<tên>/data dữ liệu /port/<tên>/data
     Thêm trang mới hay sửa trang cũ chỉ cần sửa repo — không phải dán lại Worker.

   Riêng tư: chỉ chạy sau bước kiểm admin của Worker, không có đường công khai.
   ========================================================================== */

async function handlePort(req, env) {
  const url = new URL(req.url)
  const p = url.pathname.replace(/\/+$/, '') || '/port'
  if (req.method !== 'GET') return pErr(405, 'chỉ đọc')
  if (!env.SLIDES) return pErr(500, 'Worker chưa gắn KV binding SLIDES')
  if (p === '/port') return pTrang(await env.SLIDES.get('port/html', { type: 'text' }))
  if (p === '/port/data') return pJson(await env.SLIDES.get('port/bundle', { type: 'text' }))
  const m = p.match(/^\/port\/([a-z0-9-]{1,40})(\/data)?$/)
  if (!m) return pErr(404, 'không có đường này')
  const k = 'port/page/' + m[1] + (m[2] ? '/data' : '')
  const v = await env.SLIDES.get(k, { type: 'text' })
  return m[2] ? pJson(v) : pTrang(v)
}

function pTrang(html) {
  return new Response(html || PORT_CHO, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } })
}

function pJson(v) {
  if (v === null) return pErr(404, 'chưa có dữ liệu — chạy workflow "Lọc port" trong nsi-bot')
  return new Response(v, { headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } })
}

function pErr(code, msg) {
  return new Response(JSON.stringify({ loi: msg }), { status: code, headers: { 'content-type': 'application/json; charset=utf-8' } })
}

const PORT_CHO = '<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lọc port</title></head>'
  + '<body style="font:16px/1.6 system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px">'
  + '<h1>Trang chưa có</h1><p>Trang này chưa được đẩy lên KV. Vào tab <b>Actions</b> của repo <b>nsi-bot</b>, chọn workflow <b>"Lọc port"</b>, '
  + 'bấm <b>Run workflow</b>. Chạy xong (khoảng 5–10 phút) tải lại trang này.</p></body></html>'

export { handlePort }
