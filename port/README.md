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

## Bốn phần thêm ngày 22/10/2026

- **Sổ giả lập mua bán + NAV** (`sim.py`): vốn 1 tỷ, phí 0,15%/0,25%, khớp giá đóng cửa phiên sau ngày quyết định. Mua theo quy tắc giải ngân trong `danh_muc.json` (3 đợt 1/3; hoảng loạn 60/40; đợt sau khi đi ngang 20 phiên; giá chạy +10% thì mua đuổi). (T1/T2 đã bỏ 24/10/2026) dưới giá vốn −15% bán hết; −10% hoặc thủng hỗ trợ Daily chỉ treo cờ. Sổ chỉ ghi tiếp (`state/so_gia_lap.json`).
- **Mục tiêu giá**: code gom mốc có nguồn (kháng cự/đỉnh cũ của Daily, MA200, định giá về giữa/trung vị 12 quý) và đề xuất T1 ≥ +12%, T2 ≥ T1 +12%. Claude duyệt rồi ghi vào `muc_tieu` của luận điểm; sổ giả lập chỉ dùng số đã duyệt.
- **Đọc BCTC sâu** (`bctc.py`): tách lãi trước thuế thành kinh doanh chính / tài chính / một lần / dự phòng từ `data/funda_raw2.json` (cache `bctc-` của dây chuyền hằng ngày), tìm khoản kéo lên/xuống so cùng kỳ, viết câu theo khuôn.
- **Nhận định hằng ngày + vòng học** (`nhan_dinh.py`): mỗi chiều chấm điểm từng mã (tăng/đi ngang/giảm so với VN-Index trong 5/20/60 phiên), chấm đúng/sai khi đủ phiên. Mỗi lượt chạy lùi từ 2019 trên `data/port_gia.npz` (dây chuyền hằng ngày cắt từ fa.npz, cache `port-gia-`) để so trọng số đang dùng (`trong_so.json` ở port-data, chưa có thì bộ v1) với mô hình đề xuất. Không tự đổi trọng số.
- **Nhắc review** (`nhac.py`): chuông ntfy/Telegram khi nguyensonfinance có BCTC quý mới của mã trong port/hàng chờ, khi đủ số cả port (đến kỳ review quý), và khi sổ giả lập treo cờ.

## Lọc quý TOP110 (22/10/2026, `loc_quy.py`)

- **Tự lọc theo quý, nối vào BCTC của nguyensonfinance:** mỗi lượt "Lọc port", mã nào trong TOP110 (vũ trụ của bot) vừa có quý mới trong BCTC trang đã cào (`data/funda_raw2.json`, cache `bctc-`; thiếu thì 12 quý trên trang) được chấm lại **phần số của khung 70/30**: định giá so với chính nó 20 + LN 4 quý 10 + ROE 10 = tối đa 40. Mã bị cổng rủi ro của bot chặn không vào top.
- **Top 10 = lọt lọc quý**, chuông ntfy khi có mã mới lọt/rời top. Lọt lọc không tự vào port: phần 70% định tính Claude viết lúc anh Sơn review quý.
- **Sổ pitch bóng** (`state/so_loc_quy.json`): mỗi mã TOP110 mỗi quý một dòng, chấm hơn VN-Index sau 20/60/120/250 phiên — mẫu cho vòng học (~440 dòng/năm).
- **Chạy lùi từ 2019** (`state/loc_quy_lui.json`): IC theo đợt quý của điểm và từng thành phần, top 10 so với cả rổ. Kết quả lần đầu (22/10/2026, 4.005 mẫu, 168 mã): top 10 **thua** cả rổ −6,2 điểm % sau 60 phiên (t −5,1), −2,2 sau 250 phiên; phần "rẻ so với chính nó" kéo ngược (IC 60 phiên −0,20). Thang điểm chưa đổi — chỉ đổi khi anh Sơn duyệt.
- Trang `/port` → tab **Lọc quý TOP110**.

## Pool tuần + tỷ trọng theo kết luận pitch (anh Sơn chốt 24/10/2026, `pool.py`, `sim.py`)

Bộ máy port giữ nguyên (luận điểm 5 khâu, khung 70/30, khâu 5, debate với máy, review quý). Chỉ đổi **cách lọc** và **pool**.

- **Pool = watchlist NSI + 20–30 mã riêng (TOP110)**, chốt lại mỗi tuần. Pool là đầu vào để pitch, không phải danh mục.
  Mã watchlist NSI cũng phải qua bộ lọc mới.
- **Loại cứng — nền giá cao:** giá cách đỉnh 250 phiên chưa tới −15%, hoặc biên độ đóng cửa 30 phiên > 20%.
- **Điểm 0–100 (kịch bản bật lại):** vùng giá thấp 25 · nền hẹp 15 · siết vol (KL TB20 ÷ TB120) 15 · biên độ co 5 ·
  ngành ở đáy chu kỳ 10 · rẻ so với chính nó 15 · lợi nhuận sắp hồi 10 · ROE 5. Rơi sâu và P/E thấp **được** dùng làm lý do mua.
  Không xét dòng tiền mua bán (mã ít người để ý, volume co lại còn được ưu tiên).
- **Trừ điểm, không còn chặn cứng:** CFO 12 tháng âm −10 (không áp cho ngân hàng/CK/bảo hiểm) · trả lãi vay < 1,5 lần −8 ·
  nợ xấu > 3% −8 · nợ vay/vốn chủ > 4 −5 · lãi bất thường −3.
- **Sổ pool bóng** (`state/so_pool.json`): mỗi tuần mọi mã TOP110 một dòng, chấm hơn VN-Index sau 20/60/120/250 phiên.
  Thang điểm là giả thuyết — lưu ý chạy lùi lọc quý 22/10 cho "rẻ so với chính nó" IC 60 phiên −0,20; sổ này đo lại cho bộ lọc mới.
- Chuông ntfy khi pool tuần có mã vào/ra. Lọc quý TOP110 vẫn chạy để đo, không gửi chuông nữa.
- **Sổ giả lập:** bỏ mục tiêu T1/T2. Tỷ trọng theo kết luận pitch: ĐỦ ĐỂ XUỐNG TIỀN ≥ 70 điểm → 12% NAV, 60–69 → 8%;
  CHỜ PHÉP THỬ → chỉ đợt 1, tối đa 4% (mã ở hàng chờ); còn lại 0. Đợt: 40/30/30 (hoảng loạn 60/40).
  Trần: mã 15% NAV, ngành 30%, tổng giải ngân 90%. Cắt −15% dưới giá vốn giữ nguyên. Đổi luật nên sổ chạy lại từ 15/10.
- Trang `/port` → tab **Pool tuần** (dán lại `worker_port_page.js` vào Worker nsi-quantri).

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
