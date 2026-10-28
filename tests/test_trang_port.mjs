// Trang /port nằm ở KV (28/10/2026): cú pháp script của port/trang_port.html, và Worker trả đúng trang / dữ liệu.
import { readFileSync } from 'node:fs'
import { handlePort } from '../port/worker_port_page.js'
const html = readFileSync(new URL('../port/trang_port.html', import.meta.url), 'utf8')
const js = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n')
new Function(js)   // ném lỗi nếu sai cú pháp
if (!/function ds\(/.test(js) || !/function daGN\(/.test(js) || /VN-Index cùng kỳ/.test(js)) throw new Error('trang /port: thiếu % NAV đã giải ngân hoặc còn ô VN-Index cùng kỳ')
const kv = { 'port/html': html, 'port/bundle': '{"asof":"x"}' }
const env = { SLIDES: { get: async k => (k in kv ? kv[k] : null) } }
let r = await handlePort(new Request('https://a/port'), env)
if ((await r.text()) !== html) throw new Error('/port không trả trang từ KV')
r = await handlePort(new Request('https://a/port/data'), env)
if ((await r.text()) !== '{"asof":"x"}') throw new Error('/port/data sai')
r = await handlePort(new Request('https://a/port'), { SLIDES: { get: async () => null } })
if (!(await r.text()).includes('Run workflow')) throw new Error('KV trống phải hiện hướng dẫn')
kv['port/page/ho-so'] = '<p>ho so</p>'; kv['port/page/ho-so/data'] = '{"n":1}'
r = await handlePort(new Request('https://a/port/ho-so'), env)
if ((await r.text()) !== '<p>ho so</p>') throw new Error('/port/ho-so không trả trang KV')
r = await handlePort(new Request('https://a/port/ho-so/data'), env)
if ((await r.text()) !== '{"n":1}') throw new Error('/port/ho-so/data sai')
r = await handlePort(new Request('https://a/port/khong-co/data'), env)
if (r.status !== 404) throw new Error('trang chưa có dữ liệu phải 404')
r = await handlePort(new Request('https://a/port/../x'), env)
if (r.status !== 404) throw new Error('đường lạ phải 404')
r = await handlePort(new Request('https://a/port', { method: 'POST' }), env)
if (r.status !== 405) throw new Error('POST phải bị chặn')
console.log('trang /port: đạt')
