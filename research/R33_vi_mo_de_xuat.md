# R33 — Đề xuất: dạy bot hiểu vĩ mô (lãi suất, liên ngân hàng, tỷ giá)

*Bản đề xuất 29/09/2026 — CHƯA code, CHƯA đụng PROD. Anh Sơn duyệt hướng rồi mới làm.*

## 0. Nguyên tắc (theo quy tắc II.B)

- Vĩ mô **không phải lớp chặn tuyệt đối**. Chặn cứng làm miss nhiều deal tốt: thị trường VN hay tăng
  mạnh đúng lúc tin vĩ mô còn xấu.
- Mỗi tín hiệu vĩ mô chỉ là **một phiếu** trong nhiều lớp. Phải kiểm chéo với đèn thị trường (G1/G2/G3),
  dòng tiền (ĐK9) và khối ngoại trước khi được đổi cỡ lệnh.
- Mọi luật phải qua cùng bộ kiểm như R11/R13: walk-forward 2019–22 vs 2023–26, Monte Carlo bỏ 10% deal,
  vùng phẳng (không phải đỉnh nhọn), đếm số deal bị miss, và chạy **chỉ hiển thị** vài tuần trước khi vào PROD.

## 1. Cào từ nguồn nào

| Chỉ số | Nguồn chính | Nguồn đối chiếu | Tần suất | Lịch sử từ 2017? |
|---|---|---|---|---|
| Lãi suất **liên ngân hàng** qua đêm / 1 tuần / 1 tháng | SBV (sbv.gov.vn — "Lãi suất thị trường liên ngân hàng") | Vietstock / CafeF tin hằng ngày, báo cáo tuần của SSI/VNDirect | ngày | SBV có bảng theo ngày; cần cào lùi một lần |
| Bơm/hút **OMO** + phát hành **tín phiếu** NHNN | SBV (kết quả nghiệp vụ thị trường mở) | Vietstock tin OMO | ngày | có, cào lùi |
| **Lãi suất điều hành** (tái cấp vốn, tái chiết khấu) | SBV | tin báo chí | khi đổi | tự gõ tay ~10 lần đổi, đủ |
| **Tỷ giá** trung tâm USD/VND + giá bán Vietcombank | SBV (tỷ giá trung tâm), vietcombank.com.vn | FRED/Yahoo USD/VND | ngày | có |
| Lợi suất **TPCP 10 năm** VN | HNX (thị trường trái phiếu) | investing.com | ngày | có |
| Lãi suất **huy động 12 tháng** Big4 | website 4 ngân hàng | CafeF tổng hợp | tháng | tự dựng tay các mốc |
| CPI, tăng trưởng tín dụng | GSO (gso.gov.vn), SBV | báo chí | tháng | có |
| Mỹ: Fed funds, US10Y, DXY, dầu Brent | **FRED** (API miễn phí: DFF, DGS10, DTWEXBGS, DCOILBRENTEU) | Yahoo | ngày | có, dễ nhất |
| Khối ngoại mua/bán ròng | **đã có** (FireAnt) | — | ngày | có |

Ghi chú kỹ thuật: cào trên máy chạy GitHub (như fireant.py). Hỏng nguồn thì bước này `continue-on-error`,
không bao giờ làm đổ bản dựng tối. Lưu `data/macro.json`, có `asof` và nguồn cho từng chuỗi.

## 2. Biến thành tín hiệu gì

Không dùng **mức tuyệt đối** ("lãi suất > X% thì đứng ngoài") làm luật chính — mức "bình thường"
của VN trôi theo năm. Dùng **độ lệch so với chính nó**:

1. **Căng thanh khoản**: liên ngân hàng qua đêm vượt trung bình 1 năm + 2 độ lệch chuẩn, hoặc
   tăng > 2 điểm % trong 10 phiên.
2. **NHNN hút tiền**: OMO + tín phiếu hút ròng 10 phiên liên tiếp.
3. **Áp lực tỷ giá**: USD/VND tăng > 1,5% trong 20 phiên, hoặc sát trần biên độ.
4. **Lãi suất dài hạn tăng**: TPCP 10 năm tăng > 50 điểm cơ bản trong 60 phiên.
5. **Gió ngược toàn cầu**: DXY tăng mạnh + US10Y tăng cùng lúc.

→ **Điểm căng vĩ mô 0–5** = số tín hiệu đang bật.

Các giai đoạn phải kiểm được bằng mắt trên dữ liệu: Q4/2022 (liên ngân hàng qua đêm vọt 6–7%,
VND mất giá, khủng hoảng trái phiếu — thị trường sập), Q2/2024 (NHNN phát hành tín phiếu, tỷ giá
cao), 2020 (hạ lãi suất — sóng lên), 2018 (Fed tăng lãi suất, DXY mạnh).

## 3. Dùng điểm căng thế nào (giả thuyết để backtest, chưa phải luật)

Chỉ những cách **mềm**, so với PROD hiện tại:

- **A. Giảm cỡ lệnh**: điểm ≥ 2 → cỡ lệnh mới × 0,8; điểm ≥ 3 → × 0,6. Không chặn mua.
- **B. Siết thoát**: điểm ≥ 3 → khoá lãi bật sớm hơn một nấc, van thời gian T+3.
- **C. Kiểm chéo với đèn**: chỉ giảm cỡ khi điểm căng cao **và** đèn không phải Xanh; đèn Xanh thì bỏ qua
  vĩ mô (giá đã nói trước tin).
- **D. Đối chứng**: ngưỡng mức tuyệt đối kiểu "qua đêm > 5%" để xem có thua cách độ lệch không.

Đo cho từng cách: tổng LN, DD, PF, Sharpe, **số deal bị bỏ/thu nhỏ và lãi của chính các deal đó**,
kết quả chia hai nửa 2019–22 / 2023–26. Chỉ giữ cách nào giảm DD mà không mất quá ~5% tổng LN
và thắng ở cả hai nửa.

## 4. Lộ trình

| Bước | Việc | Ảnh hưởng tới lệnh |
|---|---|---|
| P0 | `macro_fetch.py`: cào + lưu lịch sử từ 2017, kiểm độ phủ | không |
| P1 | Ô "Vĩ mô hôm nay" trên web + dòng trong Telegram (điểm căng, từng tín hiệu) | không — chỉ để xem |
| P2 | R33 backtest A/B/C/D + đủ bộ kiểm (walk-forward, MC, vùng phẳng, deal bị miss) | không |
| P3 | Chạy song song chỉ hiển thị ≥ 4 tuần | không |
| P4 | Anh Sơn duyệt → vào PROD một nút, có preset tắt để so mỗi tối | có |

## 5. Rủi ro phải nói trước

- Dữ liệu SBV cào lùi có thể thiếu ngày / đổi định dạng → phải đối chiếu hai nguồn.
- Chỉ có ~7,7 năm, số đợt căng vĩ mô thật chỉ 3–4 lần → dễ **khớp quá** vào 2022. Vì thế bắt buộc
  thắng ở cả hai nửa và vùng phẳng.
- Đèn thị trường đã phản ứng theo giá; vĩ mô có thể chỉ **đếm hai lần** cùng một tin xấu (như bài học
  "mua dưới đèn Cam rồi hạ 1/3"). Cách C để đo đúng điều này.

## 6. Anh Sơn cần quyết

1. Đồng ý bộ nguồn ở mục 1 chưa? (FRED + SBV + HNX là lõi; phần còn lại thêm sau.)
2. Làm P0 + P1 trước (chỉ hiển thị), R33 backtest sau?
