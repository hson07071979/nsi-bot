# -*- coding: utf-8 -*-
"""Sinh lai tai lieu ma nguon TU CHINH CAC FILE .py, de tai lieu khong bao gio lech code.
Phan van xuoi (LOI DA SUA + CROSS-CHECK) doc tu notes_code_doc.md."""
import os

HEADER = """# Mã nguồn bot Nguyễn Sơn Invest (v5 — sau cross-check toàn ngành)

Tài liệu này là **bản sao đúng nguyên văn** của các file `.py` trong thư mục làm việc,
được sinh tự động bởi `make_code_doc.py`. Đừng sửa tay trong tài liệu này — sửa file
`.py` rồi chạy lại script.

**Cách dựng lại bot từ số 0:**

```bash
mkdir kafi && cd kafi && mkdir -p data site
# ghi từng khối code bên dưới ra đúng tên file trong tiêu đề
python3 fireant.py      # cào ~694 mã HOSE+HNX, ~2400 phiên  (~2 phút)
python3 fetch_funda.py  # cào báo cáo tài chính Vietcap
python3 fa_prep.py      # nén thành data/fa.npz
python3 produce2.py     # chạy backtest, xuất data/site_data2.json
python3 watchlist.py    # quét lại watchlist
python3 alerts2.py      # chuông báo
python3 build_site2.py  # dựng NguyenSonInvest.html  (cần thêm tài liệu template trang web)
```

"""

FILES = ['bootstrap.py', 'fireant.py', 'fetch_funda.py', 'fa_prep.py', 'fa_ind.py', 'regime2.py',
         'prep.py', 'engine.py', 'engine2.py', 'vn300.py', 'extras.py', 'lookup.py', 'dealstats.py', 'screener.py',
         'watchlist.py', 'alerts2.py', 'produce2.py', 'build_site2.py', 'verify_build.py', 'publish.py',
         'manual.py', 'live_scan.py', 'pubrepo/portfolio.py',
         'audit_sector.py', 'icr_audit.py', 'ab_sector.py', 'icr_robust.py',
         'why_missed.py', 'last6m.py', 'make_site_doc.py', 'make_code_doc.py']

out = [HEADER]
if os.path.exists('notes_code_doc.md'):
    out.append(open('notes_code_doc.md', encoding='utf-8').read())
    out.append('\n---\n\n# Mã nguồn\n')

for f in FILES:
    if not os.path.exists(f):
        continue
    out.append(f'\n## `{f}`\n\n```python\n' + open(f, encoding='utf-8').read().rstrip() + '\n```\n')

doc = '\n'.join(out)
open('code_doc.md', 'w', encoding='utf-8').write(doc)
print('code_doc.md', len(doc), 'ky tu,', len(FILES), 'file')
