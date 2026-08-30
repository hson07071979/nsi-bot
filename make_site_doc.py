# -*- coding: utf-8 -*-
"""Gom cac file template cua trang web thanh MOT tai lieu de luu vao project.
Ly do: phien chay tu dong 19/08 khong dung lai duoc web vi tai lieu ma nguon
thieu site/*.js — no phai tu viet mot trang khac han."""
FILES = ['site/part1.html', 'site/part2.js', 'site/p3.js', 'site/p4.js',
         'site/p5.js', 'site/part6.js', 'site/p8.js', 'site/p9.js', 'site/p10.js', 'site/p11.js', 'site/p12.js', 'site/p7.js']

out = ["""# Template trang web — Nguyễn Sơn Invest

Tài liệu này chứa các file template mà `build_site2.py` cần đọc. Không có chúng thì
không dựng lại được đúng trang web (phiên chạy tự động 19/08/2026 đã vấp đúng lỗi này).

**Cách dùng:** tạo thư mục `site/`, ghi từng khối bên dưới ra đúng tên file trong tiêu đề,
rồi chạy `python3 build_site2.py`. Thứ tự nạp JS trong `build_site2.py` là:
`part2.js, p3.js, p4.js, p5.js, part6.js, p8.js, p9.js, p10.js, p11.js, p12.js, p7.js`
(chú ý: **p7.js phải nạp SAU CÙNG** vì nó chạy router ngay khi nạp xong;
p9.js phải nạp TRƯỚC p7.js vì nó khai báo `let` mà router cần).

Chỉ tác vụ 19h30 (dựng lại web) mới cần tài liệu này. Tác vụ 11h20 và 14h05 chỉ chạy
chuông báo nên không cần đọc.

"""]
for f in FILES:
    lang = 'html' if f.endswith('.html') else 'javascript'
    out.append(f"\n## `{f}`\n\n```{lang}\n" + open(f).read().rstrip() + "\n```\n")
txt = ''.join(out)
open('site_doc.md', 'w').write(txt)
print('chars', len(txt))
