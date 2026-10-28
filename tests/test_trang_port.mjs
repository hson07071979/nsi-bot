// Trang /port nằm ở KV (28/10/2026): cú pháp script của port/trang_port.html, và Worker trả đúng trang / dữ liệu.
import { readFileSync } from 'node:fs'
import { handlePort } from '../port/worker_port_page.js'
const html = readFileSync(new URL('../port/trang_port.html', import.meta.url), 'utf8')
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n')
new Function(js)   // ném lỗi nếu sai cú pháp
if (!/function daGN\(/.test(js) || /VN-Index cùng kỳ/.test(js)) throw new Error('trang /port: thiếu % NAV đã giải ngân hoặc còn ô VN-Index cùng kỳ')
const kv = { 'port/html': html, 'port/bundle': '{"asof":"x"}' }
const env = { SLIDES: { get: async k => (k in kv ? kv[k] : null) } }
let r = await handlePort(new Request('https://a/port'), env)
if ((await r.text()) !== html) throw new Error('/port không trả trang từ KV')
r = await handlePort(new Request('https://a/port/data'), env)
if ((await r.text()) !== '{"asof":"x"}') throw new Error('/port/data sai')
r = await handlePort(new Request('https://a/port'), { SLIDES: { get: async () => null } })
if (!(await r.text()).includes('Run workflow')) throw new Error('KV trống phải hiện hướng dẫn')
r = await handlePort(new Request('https://a/port', { method: 'POST' }), env)
if (r.status !== 405) throw new Error('POST phải bị chặn')
console.log('trang /port: đạt')
