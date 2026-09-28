# -*- coding: utf-8 -*-
"""Lop real-time trinh duyet phai giu co cua may chu (28/09/2026): mua_do -> MUA_DO (Du diem mua,
khong liet DK9 la 'con thieu'), dang_cam -> DANG_CAM (khong bao gio SAP_DU / MUA).
Run: python3 tests/test_live_flags.py"""
import os, re, sys, json, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
src = open('site/p11.js', encoding='utf-8').read()
a = src.index('const ODK9'); b = src.index('const BAC_TH')
helper = src[a:src.index('\n', b)]
JS = helper + r'''
var LIVE = {server: {hits: []}};
const K = 'Cỡ lệnh mua ≥ 1.40× cỡ lệnh bán';
const out = {};
const mk = (lvl, miss) => ({level: lvl, miss: miss, realtime_mapped: true});
out.muaDo   = apCoMayChu(mk('SAP_DU', [K]), {mua_do: true}, {});
out.muaDoPx = apCoMayChu(mk('SAP_DU', ['Biên độ tăng giá', K]), {mua_do: true}, {});
out.cam     = apCoMayChu(mk('SAP_DU', [K]), {dang_cam: true, mua_do: false}, {});
out.camLk   = apCoMayChu(mk('THEO_DOI', [K]), null, {dang_cam: true});
out.camMua  = apCoMayChu(mk('MUA', []), {dang_cam: true}, {});
out.plain   = apCoMayChu(mk('SAP_DU', ['Biên độ tăng giá', K]), null, {});
out.srvOnly = apCoMayChu({level: 'SAP_DU', miss: [K], mua_do: true}, {mua_do: true}, {});
console.log(JSON.stringify(out));
'''
r = json.loads(subprocess.check_output(['node', '-e', JS]).decode())
ok = 0; T = [
  ('mua do -> MUA_DO, DK9 khong con la thieu', r['muaDo']['level'] == 'MUA_DO' and r['muaDo']['miss'] == []),
  ('gia tut khoi nguong sau lan quet -> khong mua do', r['muaDoPx']['level'] == 'SAP_DU' and not r['muaDoPx']['mua_do']),
  ('dang cam (may chu) -> DANG_CAM', r['cam']['level'] == 'DANG_CAM' and r['cam']['dang_cam']),
  ('dang cam (o tra cuu) -> DANG_CAM', r['camLk']['level'] == 'DANG_CAM'),
  ('MUA ma dang cam -> DANG_CAM', r['camMua']['level'] == 'DANG_CAM'),
  ('ma thuong khong doi', r['plain']['level'] == 'SAP_DU' and len(r['plain']['miss']) == 2),
  ('ban ghi live.json khong real-time van mua do', r['srvOnly']['level'] == 'MUA_DO'),
]
for n, c in T:
    print('PASS' if c else 'FAIL', n); ok += bool(c)
for f in ('site/p11.js', 'site/p13.js'):
    s = open(f, encoding='utf-8').read()
    c = 'apCoMayChu(' in s and "h.level === 'MUA_DO'" in s
    print('PASS' if c else 'FAIL', f, 'goi apCoMayChu + chuong MUA_DO'); ok += bool(c)
print(f'{ok}/{len(T) + 2} passed'); sys.exit(0 if ok == len(T) + 2 else 1)
