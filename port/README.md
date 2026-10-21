# Lọc port: vòng học thứ tư của bộ máy NSI

Đây là phần lọc cổ phiếu cho khách hàng. Cách làm: đi từ vĩ mô xuống ngành rồi xuống doanh nghiệp, sau đó từ mô hình kinh doanh dẫn ngược lại vĩ mô. Mỗi mã phải có pitch, quan điểm đầu tư rõ ràng và qua debate.

Port không chạy riêng. Nó là vòng thứ tư nối vào ba bộ máy đã có. Luận điểm nào cũng phải đối chất với ba máy kia, và cả bốn bên đều bị chấm điểm bằng giá thật.

```
            ┌──────────── dữ liệu công khai, không cào thêm ────────────┐
  Bot (nsi-bot)          NSI Tin (nsi-tin)           NSI Daily (nsi-tin)
  9 điều kiện, tín hiệu, trọng tài + 3 phe theo mã,  mốc hỗ trợ/kháng cự,
  cổng rủi ro CFO/ICR,   tự chấm T+4 vượt VN-Index   sổ dự báo code chấm
  backtest + Monte Carlo
            └──────────────┬──────────────────────────────┘
                           ▼
        port/build.py → hồ sơ máy cho từng mã có luận điểm
                           │
   máy ngược chiều port ──►│──► bắt buộc có phan_bien_may.<máy>; thiếu thì treo cờ CHƯA TRẢ LỜI MÁY
                           │──► mở sổ bất đồng (giá mã + VNI) → chấm sau 20 và 60 phiên: port đúng hay máy đúng
   mốc kiểm chứng ────────►│──► code chấm (giá: giu/thung/vuot/duoi · cơ bản: chỉ tiêu quý ≥/≤ ngưỡng)
                           ▼
        bảng tin cậy + bài học → đầu vào cho lần debate sau (Claude đọc trước khi viết luận điểm)
```

## Ai làm gì

- **Claude, trong chat dự án NSI Daily Market.** Viết và cập nhật luận điểm theo khuôn `MAU_LUAN_DIEM.json`, rồi đẩy thẳng vào nhánh `port-data`. Trước khi viết, Claude đọc hồ sơ máy và bảng tin cậy. Khi có máy ngược chiều, Claude phải trả lời máy đó trước khi đưa mã vào danh mục.
- **Workflow "Lọc port".** Chạy sau mỗi lượt "Cập nhật Nguyễn Sơn Invest", mỗi lần có luận điểm mới đẩy vào `port-data`, và 18h17 các ngày trong tuần.
  - Workflow dùng mã ở `main` và dữ liệu ở `port-data`.
  - Kết quả chấm được ghi lại vào `port-data/port/state/`.
  - Gói tổng được đẩy lên KV `port/bundle`.
- **Trang quản trị `/port`** (`worker_port_page.js`). Trang chỉ đọc KV và có 5 tab: Danh mục & pitch · Sổ phân tích · Debate với máy · Lọc cơ bản · Vòng học.

## Riêng tư

- Luận điểm và danh mục chỉ nằm ở hai nơi: nsi-bot (private) và KV, đọc qua trang quản trị có đăng nhập.
- Không ghi gì của port sang nsi-tin (public), lên trang web hay kênh video.
- Bằng chứng lấy từ nhóm Zalo kín được gắn nhãn "chỉ nội bộ" và không được trích vào pitch cho khách hàng.

## Cài đặt (một lần)

1. Thêm 3 secret vào nsi-bot (Settings → Secrets and variables → Actions). Giá trị giống hệt bên nsi-tin: `CF_ACCOUNT_ID`, `CF_KV_NAMESPACE_ID`, `CF_API_TOKEN`.
2. Merge PR này. Claude sẽ tạo nhánh `port-data` từ `main`.
3. Trong Worker nsi-quantri, dán `worker_port_page.js`, rồi thêm dòng định tuyến cạnh dòng của `/daily`:
   `if (ADMIN && (url.pathname === '/port' || url.pathname.startsWith('/port/'))) return handlePort(req, env)`
   Worker dùng lại KV binding `SLIDES` đã có, nên không cần token mới.

## Giới hạn đang biết

- Số phiên được đếm theo các ngày workflow chụp được giá. Ngày nào workflow không chạy thì phiên đó không được đếm, nên kết quả chấm có thể đến muộn hơn chứ không bị sai.
- Quan điểm của từng máy là quy ước rút gọn, chỉ có ba mức +1 / 0 / −1:
  - Bot: −1 khi cổng CFO/ICR chặn mã; +1 khi có tín hiệu trong 14 ngày hoặc mã đang chờ điểm mua; còn lại 0.
  - NSI Tin: lấy chiều của trọng tài theo mã trong 10 ngày, có trọng số theo mức quan trọng.
  - NSI Daily: theo sổ dự báo đang mở; nếu không có dòng nào thì theo vị trí giá so với MA50 và MA200.
- Mỗi máy nhìn một khung thời gian khác (Bot và Daily là ngắn hạn), nên khi phản biện phải nói rõ khung thời gian. Port thắng ở 60 phiên không có nghĩa là máy sai ở khung 5 phiên.
- Mẫu dưới 10 lần thì chưa ra tỷ lệ, nghĩa là chưa kết luận được bên nào đáng tin hơn.

## Giải ngân, rủi ro, mục tiêu, điểm 70/30 (R38/R39, anh Sơn chốt 15/10/2026)

Code: `port/giai_ngan.py`. Bằng chứng: `research/r38_giai_ngan.py`, `research/r39_dinh_gia.py`, `evidence/r38_*.json`, `evidence/r39_*.json`
(giá FireAnt 2017→nay ~700 mã HOSE/HNX, BCTC theo ngày công bố, 281 sự kiện "tài sản tốt, giá thấp" 2020–2025).

- **Trạng thái thị trường** (VN-Index so với đỉnh 250 phiên): hoảng loạn ≤ −20% → 2 đợt 60/40; còn lại → 3 đợt 1/3.
- **Đợt sau** chỉ khi đi ngang 20 phiên sau đợt trước (biên đóng cửa ≤ 8%, đầu–cuối ≤ 4%, nửa sau không tạo đáy mới); quá 120 phiên không có nền → mua nốt nếu luận điểm còn đúng.
- **Chạy luôn** (+10% so với đợt 1 trước đợt 2): mua nửa phần còn lại ngay, nửa khi hồi về MA20 trong 60 phiên. Không bỏ lỡ (R38: bỏ lỡ mất ~8 điểm %/năm).
- **Rủi ro**: < giá vốn −7% → ngừng mua thêm, rà luận điểm; < giá vốn −15% → bán hết; VN-Index dưới `danh_muc.dung_vni` → hoãn đợt mới; mỗi mã ≤ 20% NAV; nhiệt danh mục ≤ 10% NAV.
  R38 với quy tắc này: lợi suất TB 12 tháng +14,0%, mã xấu nhất −26,5%, Monte Carlo 8 mã p5 −5,7%, xác suất danh mục lỗ > 10% sau 12 tháng 0,6%.
- **Mục tiêu**: T1/T2 vẫn từ mốc kỹ thuật/định giá, kèm **xác suất chạm trong 60/120 phiên** (bước ngẫu nhiên không trôi, σ 60 phiên — R39 hiệu chỉnh tốt). Không dùng "P/E tại đỉnh LN cũ" để xếp hạng (R39: tương quan với lợi suất thực tế −0,12).
- **Điểm 70/30**: pitch 70 (định giá so với chính nó 20, trạng thái thị trường 20, độ chặt lập luận 15, `pitch_diem.dinh_gia_sai` 15) + kết quả 30 (LN 4 quý 10, ROE 10, K2 10). Điểm được ghi vào sổ dự đoán để sau này kiểm có dự báo được không.
- **Sổ lệnh** `port/so_lenh.json` (nhánh port-data) là nguồn duy nhất cho vị thế thật: `{"lenh":[{"ngay","ma","loai":"mua|ban","ty_le":% NAV,"gia","dot"}]}`.

### Lớp danh mục (R40, anh Sơn chốt 15/10/2026)
Mô phỏng danh mục theo lịch 14/02/2020→15/10/2026 (`research/r40_rui_ro.py`, `evidence/r40_rui_ro.json`): cắt lỗ từng mã KHÔNG chặn được sụt giảm danh mục (quy tắc −15% vẫn sụt −54% năm 2022, chỉ +7,2%/năm). Thêm hai lớp:
- **Chỉ mở mã mới khi VN-Index ≤ −10% so với đỉnh 250 phiên.**
- **Tối đa 2 mã mới mỗi 20 phiên**, xếp lượt theo điểm 70/30; tối đa 8 mã × 12,5% NAV.
Kết quả: +171,7% (16,2%/năm), sụt giảm danh mục lớn nhất −18,7% (VN-Index +81,2%, −40,3%); riêng 2023–2026 +14,8%/năm, −14,3%; Monte Carlo trung vị 15,9%/năm, p5 11,8%, sụt p95 21,5%. Đã thử ~20 phương án trên cùng dữ liệu nên có rủi ro quá khớp — vùng tham số lân cận (ngưỡng −8…−15%, 6–10 mã, nhịp 1–2) đều cho 10–20%/năm, sụt 9–24%.
