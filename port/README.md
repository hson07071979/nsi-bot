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
