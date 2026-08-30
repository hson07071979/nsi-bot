# Bot Nguyễn Sơn Invest — repo riêng

Repo này chứa **mã nguồn bot** và **cỗ máy tự cập nhật**. Để ở chế độ **Private**
để không ai đọc được nguyên tắc giao dịch.

Mỗi tối thứ Hai đến thứ Sáu lúc **19h30 giờ Việt Nam**, GitHub tự chạy toàn bộ dây
chuyền trên máy chủ của họ, dựng lại trang web, và đẩy sang repo public để khách hàng
xem. Bạn không phải làm gì cả.

---

## Cài đặt lần đầu — 5 bước

### Bước 1 — Tạo repo này (Private)

github.com → dấu **+** → **New repository**

- Repository name: `nsi-bot`
- Chọn **Private**
- **Đừng** tick "Add a README file"
- Bấm **Create repository**

### Bước 2 — Tải mã nguồn lên

Giải nén `nsi-bot.zip`, rồi trong repo vừa tạo bấm
**uploading an existing file** (link màu xanh giữa trang) → kéo thả **toàn bộ** nội
dung đã giải nén vào → **Commit changes**.

> ⚠️ Phải có thư mục `.github/` — nó chứa lịch chạy. Nếu máy tính ẩn thư mục bắt đầu
> bằng dấu chấm: Windows bấm `Ctrl+H`, Mac bấm `Cmd+Shift+.` để hiện ra.
>
> Kiểm tra: sau khi tải lên, vào tab **Actions** phải thấy dòng
> "Cập nhật Nguyễn Sơn Invest". Không thấy tức là thiếu thư mục `.github/`.

### Bước 3 — Tạo chìa khoá cho bot đăng bài

Bot cần quyền ghi vào repo **public** (repo chứa trang web).

1. Vào https://github.com/settings/personal-access-tokens/new
2. Token name: `bot-dang-web`
3. Expiration: chọn **No expiration** (chọn 90 ngày thì cứ 3 tháng phải làm lại bước này)
4. Repository access: **Only select repositories** → chọn repo **public** (`nguyensoninvest`)
5. Permissions → Repository permissions → tìm dòng **Contents** → đổi sang **Read and write**
6. **Generate token** → copy chuỗi bắt đầu bằng `github_pat_...`

> Chìa khoá này chỉ mở được đúng repo public đó, không đụng được thứ gì khác trong
> tài khoản. Muốn thu hồi lúc nào cũng được ở https://github.com/settings/tokens

### Bước 4 — Cất chìa khoá vào repo riêng

Trong repo `nsi-bot` → **Settings** → menu trái **Secrets and variables** → **Actions**

**Tab Secrets** → **New repository secret**

| Name | Secret |
|---|---|
| `PAGES_TOKEN` | dán chuỗi `github_pat_...` vừa copy |

**Tab Variables** → **New repository variable**, tạo hai biến:

| Name | Value |
|---|---|
| `PAGES_OWNER` | tên đăng nhập GitHub của bạn |
| `PAGES_REPO` | tên repo public chứa trang web, ví dụ `nguyensoninvest` |

> Secret thì GitHub giấu đi, kể cả bạn cũng không xem lại được — chỉ ghi đè.
> Variable thì xem lại bình thường vì không phải bí mật.

### Bước 5 — Chạy thử ngay, đừng đợi tối

Tab **Actions** → bấm **Cập nhật Nguyễn Sơn Invest** ở cột trái → nút
**Run workflow** bên phải → **Run workflow**.

Đợi khoảng 15–20 phút. Xong mà tất cả dấu tick xanh là chạy được. Mở link web,
bấm `Ctrl+F5`, kiểm số liệu có đổi không.

---

## Đọc kết quả mỗi tối

Vào tab **Actions**:

- ✅ **Tick xanh** — đã cập nhật xong, trang web đã có số mới
- ❌ **Dấu X đỏ** — có bước hỏng. Bấm vào lần chạy đó, bước nào đỏ thì mở ra xem
  dòng chữ đỏ. Trang web **giữ nguyên bản cũ**, không bị đăng bản lỗi
- 🟡 **Chấm vàng** — đang chạy

Bật báo lỗi qua email: https://github.com/settings/notifications → mục *Actions* →
tick **Failed workflows only**. Hỏng mới báo, chạy êm thì im lặng.

---

## Dây chuyền chạy gì

| Bước | Việc | Lâu |
|---|---|---|
| `bootstrap.py` | lấy danh sách mã, ngành, VN-Index | ~1 phút |
| `fireant.py` | cào giá + dòng tiền 694 mã | ~2 phút |
| `fa_prep.py` | nén dữ liệu giá | ~1 phút |
| `fetch_funda.py` | cào báo cáo tài chính Vietcap | ~7 phút |
| `screener.py` | chấm điểm toàn thị trường | ~2 phút |
| `watchlist.py` | cập nhật watchlist | ~2 phút |
| `alerts2.py` | chuông báo cuối phiên | ~1 phút |
| `produce2.py` | backtest + xuất dữ liệu | ~3 phút |
| `build_site2.py` | dựng `index.html` | vài giây |
| `verify_build.py` | **kiểm tra trước khi đăng** | vài giây |
| `publish.py` | đóng gói `out/` để đẩy sang repo public | vài giây |

`verify_build.py` là chốt chặn: nếu dữ liệu cũ, thiếu khối, hay số liệu backtest
bất thường thì nó dừng workflow. **Thà không cập nhật còn hơn đăng bản hỏng cho khách.**

Mỗi lần chạy còn lưu một bản `index.html` ở mục **Artifacts** trong 14 ngày, tải về
được nếu cần.

---

## Quyền thủ công của anh — hai file văn bản

Đây là hai chỗ duy nhất anh sửa tay được, và sửa ngay trên GitHub trong ba cú bấm:
bấm vào file → bấm biểu tượng cây bút → gõ → **Commit changes**.

| File | Nghĩa là gì |
|---|---|
| `ghim.txt` | mã **luôn** có mặt trong watchlist, kể cả khi điểm tụt dưới ngưỡng |
| `loai.txt` | mã **không bao giờ** vào watchlist và **không bao giờ** kêu chuông |

Mỗi dòng một mã. Dòng bắt đầu bằng `#` là ghi chú, không tính.

Ba điều cần nhớ:

1. **Ghim không phải lệnh mua.** Bot vẫn chỉ vào lệnh khi mã qua đủ chín lớp.
   Ghim chỉ nghĩa là "đừng cho nó rơi khỏi tầm mắt tôi".
2. **Loại không làm bot bán.** Nếu mã đang nằm trong danh mục, bộ thoát chín lớp
   vẫn là thứ quyết định lúc nào bán. Loại chỉ nghĩa là "đừng mua thêm, đừng báo nữa".
3. **Backtest không đổi một con số nào.** Hai file này chỉ chi phối từ hôm nay trở đi.
   Nếu bỏ một mã ra khỏi quá khứ chỉ vì hôm nay không thích nó, con số hiệu suất
   thành vô nghĩa — nên hệ thống cố tình không cho phép điều đó.

Sửa xong thì bản quét 19h30 tối nay áp dụng. Muốn áp dụng ngay: tab **Actions** →
**Cập nhật Nguyễn Sơn Invest** → **Run workflow**.

Kiểm tra nhanh xem hệ đọc đúng chưa: xem dòng `thu cong: ghim ... | loai ...` trong
log của bước `screener.py` và bước `verify_build.py`.

---

## Cấu hình bot — đừng sửa lung tung

Trong `produce2.py`, khối `PROD`:

```python
use_top_liquid=True, top_n=110   # chỉ giao dịch TOP 110 mã thanh khoản nhất
big_win=0.19                     # ngưỡng lãi lớn bật trailing MA10
base_range=0.18                  # nền giá tối đa 18%
t_valve=6                        # van thời gian T+6
trail_ma=30                      # trailing MA30
score_floor=45                   # sàn điểm CANSLIM
ordimb_min=1.20                  # cỡ lệnh mua / cỡ lệnh bán
base_size=0.42                   # mỗi lệnh 42% NAV
```

Đổi `top_n` thì phải đổi **cả ba chỗ**, nếu không sẽ lệch nhau:

1. `produce2.py` — khối `PROD`
2. `screener.py` — `WL['top_n']`
3. `alerts2.py` — `build_topn(I, N)`

và sửa `TOP_N` trong `verify_build.py` cho khớp, không thì chốt chặn sẽ báo trượt.

**Hai cờ này phải luôn để `False`** — cả hai đã được kiểm chứng bằng backtest toàn kỳ
và đều làm hệ thống kém đi:

```python
re_cfo_warn=False       # nới CFO cho bất động sản
icr_cfo_rescue=False    # cứu ICR bằng dòng tiền
```

Số liệu tham chiếu hiện tại (phiên 19/08/2026):
**+533,2% · CAGR 27,4% · DD 10,5% · PF 4,55 · Sharpe 1,81 · 172 lệnh · 119 deal**

---

## Khi có trục trặc

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| Tab Actions trống trơn | Thiếu thư mục `.github/` khi tải lên |
| Bước "Đăng lên trang web" đỏ | Sai/hết hạn `PAGES_TOKEN`, hoặc token không có quyền **Contents: Read and write**, hoặc sai `PAGES_OWNER`/`PAGES_REPO` |
| Bước "Kiểm tra trước khi đăng" đỏ | Dữ liệu cào về có vấn đề — đọc dòng đỏ để biết chỗ nào. Trang web vẫn an toàn |
| Bước "Cào giá" đỏ | FireAnt chặn hoặc đổi API. Thử bấm Run workflow lại sau vài tiếng |
| Chạy xanh mà web vẫn số cũ | Trình duyệt nhớ tạm — bấm `Ctrl+F5`, hoặc thêm `?v=2` vào cuối link |
| Không chạy đúng 19h30 | GitHub thường trễ 5–20 phút khi máy chủ đông. Bình thường |

GitHub tự tắt lịch chạy nếu repo **không có hoạt động nào trong 60 ngày**. Nó sẽ gửi
email báo trước — chỉ cần vào bấm **Run workflow** một lần là lịch chạy lại.

---

# Bản cập nhật 29/08/2026 — ba việc

## 1. Lớp kiểm định (`robustness.py`) — tab **Kiểm định** trên web

Sinh ra từ bản audit hệ thống. Nó **không** cố làm backtest đẹp hơn; nó cố **phá**
hệ thống để xem edge có thật hay không. Tám bài:

| # | Bài | Trả lời câu hỏi |
|---|---|---|
| 1 | Walk-forward | tham số chọn bằng quá khứ có sống sang năm chưa từng thấy không |
| 2 | Trượt giá 0,15 → 1,5% + **bất đối xứng** mua/bán | chiều bán tháo trượt nặng thì còn lãi không |
| 3 | Nhiễu tham số ±10–20% trên 8 ngưỡng | vùng phẳng hay một đỉnh sắc (dấu hiệu overfit) |
| 4 | Bỏ 1/3/5/10% deal lãi nhất | edge phân bổ rộng hay chỉ vài lần may |
| 5 | Monte Carlo 5.000 lần | cùng edge, thứ tự khác đi thì gồng nổi không |
| 6 | Nhìn trước — 6 phép khẳng định **chạy thật** | có ăn gian thời gian ở đâu không |
| 7 | Ngắt mạch bảo vệ vốn — A/B thật | chuỗi thua dài có nên hạ cỡ vị thế không |
| 8 | Kẹt thanh khoản T+2.5 | 10% deal sàn 2 phiên trước khi hàng về thì sao |

Rồi chấm **5 tầng**: Chức năng → Lịch sử → Bền tham số → Chịu sốc → Ngoài mẫu.
Chỉ khi cả 5 đạt mới coi là chạy thật được.

```bash
python3 robustness.py                 # chạy tất cả (~35 giây sau khi có dữ liệu)
python3 robustness.py monte_carlo     # chỉ chạy lại một bài, các bài khác lấy từ cache
```

Cache ở `data/robust_cache.json` — xoá file đó là chạy lại toàn bộ.

### Ba lỗi bản kiểm định này đã bắt được và đã sửa

1. **`prep.py` — nhìn trước ở lớp dữ liệu.** Nguồn Vietcap đôi khi trả ngày công bố
   vô lý (CAP 2023Q1 ghi công bố 31/01/2023 trong khi quý đó đến 31/03 mới kết thúc).
   Tin theo con số đó là cho bộ máy đọc báo cáo *trước khi nó tồn tại* — loại nhìn
   trước âm thầm nhất vì nó không báo lỗi, nó chỉ làm backtest đẹp lên.
   Đã chốt chặn: `avail` không bao giờ sớm hơn ngày kết thúc quý + 20 ngày.
2. **Đường vốn dựng lại từ deal bị sắp xếp sai thứ tự** → mức sụt ra 71,6% vô nghĩa.
   Đã ép sắp theo ngày thoát lệnh. `verify_build.py` giờ tự bắt lỗi này.
3. **Cỡ vị thế nhân thẳng 42% cho từng deal nối tiếp** → +4.362% thay vì +524%.
   Bot chạy tới 12 vị thế song song nên vốn được chia sẻ. Đã hiệu chuẩn:
   cỡ vị thế hiệu dụng ~18,7%, khớp đúng backtest đầy đủ.

### `engine2.py` có thêm ba khoá cấu hình (mặc định TẮT, PROD không đổi hành vi)

- `slip_buy` / `slip_sell` — trượt giá hai chiều khác nhau
- `end` — cắt lịch sử để chạy walk-forward
- `cb_enable`, `cb_dd`, `cb_losses`, `cb_cut`, `cb_days` — ngắt mạch bảo vệ vốn

## 2. Real-time không cần máy chủ (`site/p13.js`)

Bảng giá VPS gửi nhãn CORS `*` và nhận 110 mã trong một lần gọi, nên trình duyệt
tự hỏi giá được — 15 giây một nhịp, không cầu nối, không phí, không token.
Chi tiết và đánh đổi: xem README của repo trang web.

## 3. Biểu đồ TradingView (`site/p9.js`)

Trang **Chi tiết mã** có hai tab: **TradingView** (nến thật, zoom/kéo/vẽ được, mã
nào cũng có) và **Nến + dấu lệnh bot** (chỉ nó chồng được dấu bot vào/thoát lệnh).

## Thứ tự chạy (đã cập nhật)

```
bootstrap.py → fireant.py → fa_prep.py → fetch_funda.py
→ screener.py → watchlist.py → alerts2.py
→ produce2.py → robustness.py → funda_series.py
→ build_site2.py → verify_build.py → publish.py
```

⚠️ `screener.py` và `watchlist.py` phải chạy **TRƯỚC** `produce2.py` —
nếu không thì `site_data2.json` thiếu hai khối đó và `verify_build.py` sẽ chặn.

---

# Bản vá 29/08/2026 (chiều) — ba lỗi anh Sơn bắt được

## 1. Biểu đồ trống với mã nhỏ · chữ tiếng Việt hỏng

**Lỗi:** nhúng widget iframe của TradingView. `HOSE:ORS` báo *"Mã giao dịch này chỉ
có trên TradingView"* — ô biểu đồ trắng trơn. Widget đó cũng dựng chữ tiếng Việt
hỏng ("Oợ Hợ Lợ Cợ ợ").

**Chữa:** bỏ iframe. Dùng **Lightweight Charts** — thư viện mã nguồn mở của chính
TradingView (Apache 2.0, `vendor/lwc.js`, nhúng thẳng vào trang chứ không tải CDN
để mở offline vẫn xem được). Dữ liệu do TA cấp nên **mã nào cũng vẽ được**.

Nến lấy theo thứ tự: `histdatafeed.vps.com.vn` → `dchart-api.vndirect.com.vn`
→ `D.candles` nhúng sẵn. Cả hai nguồn đầu đều có nhãn CORS nên trình duyệt gọi
thẳng, ~2.000 phiên mỗi mã, **không cần cầu nối nào**.

Biểu đồ chạy thật: lăn chuột phóng to, kéo ngang trượt lịch sử, chạm hai ngón trên
điện thoại, rê tới đâu dòng OHLC đọc số tới đó, năm khung thời gian, bật/tắt
MA20/50/200 · khối lượng · dấu bot vào/thoát lệnh.

## 2. Chữ méo ở khối "Tài chính — 12 quý gần nhất"

**Lỗi:** `cotKep` và `duongQuy` dùng `viewBox="0 0 1000 260"` kèm
`preserveAspectRatio="none"`, rồi nhét vào ô rộng ~370px cao 210px. Trình duyệt
được lệnh KHÔNG giữ tỷ lệ nên nén ngang 0,37 lần mà chỉ nén dọc 0,81 lần — mọi
chữ bị **bóp ngang kéo dọc hơn hai lần**. Không phải font sai, mà là chữ biến dạng.
Cỡ chữ 23–28 trong mã nguồn chính là dấu vết của việc bù méo đó.

**Chữa:** bỏ `preserveAspectRatio`, viewBox 560×260 đúng tỷ lệ khung thật, cỡ chữ
về 10,5–12. Nhãn quý xoay −38° cho 12 nhãn không dính nhau.
Đo lại: tỷ lệ ngang 0,93 — dọc 0,93, **lệch 0,0%**.

**Lỗi kèm theo:** nhãn giá trị cuối chuỗi đè lên nhau ("5.8" chồng "6.6") và đè
nhãn "TB". Chữa: gom mọi nhãn nổi vào một danh sách, đẩy tránh nhau tối thiểu 13
đơn vị, thêm viền nền `paint-order="stroke"` để chữ nằm trên đường kẻ vẫn đọc được.

`verify_build.py` giờ **chặn** cả hai lỗi này: bản dựng nào còn
`preserveAspectRatio="none"` trong mã vẽ, hoặc còn iframe TradingView, là trượt.

## 3. Số liệu nền cũ mà không ai biết

Anh Sơn hỏi đúng chỗ đau: *"mỗi ngày giá thay đổi thì sao?"*

Trang trộn **hai loại số**:

| Loại | Nguồn | Cũ được không |
|---|---|---|
| Giá, KL, GTGD trong phiên | VPS, 15 giây/nhịp | không, luôn mới |
| Nến biểu đồ | VPS, lấy khi bấm vào mã | không, tới hôm qua |
| VN-Index | VPS | không |
| **Ngưỡng giá/KL phiên tới** | dây chuyền 19h30 | **có** |
| **Điểm CANSLIM, watchlist** | dây chuyền 19h30 | **có** |
| **Backtest, tab Kiểm định** | dây chuyền 19h30 | **có** |

Nếu workflow 19h30 chết, trang vẫn mở bình thường và giá vẫn nhấp nháy real-time —
**nhìn y như đang chạy tốt**, nhưng ngưỡng là của tuần trước. Đó là kiểu hỏng nguy
hiểm nhất: hỏng mà không ai biết.

**Chữa:** `bangSoLieuCu()` trong `p11.js` đếm số phiên làm việc từ `D.asof` tới nay.
Quá 3 phiên thì hiện băng cảnh báo ở đầu trang **Hiệu suất** và **Chuông báo**,
ghi rõ đang trễ bao nhiêu phiên, số nào vẫn tin được, số nào không, và chỉ chỗ
kiểm tra (repo `nsi-bot` → tab Actions). Quá 7 phiên thì chuyển màu cảnh báo nặng.

---

# Bản vá 29/08/2026 (tối) — hai lỗi trên trang Danh mục

## 1. Giá hiện tại lệch 1.000 lần

**Triệu chứng:** trang Danh mục hiện *giá hiện tại 13850.00 · giá trị 1.522 tỷ ·
lãi +94.566% · tỷ trọng 24.371% tài khoản · tiền mặt 0,000 tỷ*, trong khi bảng
"Danh mục hệ thống đang cầm" ngay dưới lại hiện đúng *13,85 · 1,52 tỷ · −5,33%*.
Hai bảng cùng một trang nói hai con số khác nhau.

**Nguyên nhân:** `giaMoiNhat()` trong `p12.js` có bốn nhánh dự phòng. Ba nhánh sau
(`D.candles`, `D.lookup`, `D.screener`) đều trả **nghìn đồng**. Nhánh đầu —
`NSI.rt[sym].price` — trả **đồng**, vì lớp real-time VPS giữ nguyên khuôn của cầu
nối FireAnt cũ. Nên khi có giá real-time thì hàm trả số lớn gấp 1.000 lần, còn khi
không có real-time thì trả đúng. Đó là lý do bảng này sai mà bảng kia đúng.

**Chữa:** chia 1.000 ngay trong `giaMoiNhat()` — một chỗ duy nhất. Đã rà cả năm
nơi gọi hàm này (`p10.js:lastPx`, `p12.js` bốn chỗ), tất cả đều đang chờ nghìn đồng.

## 2. Xoá deal ở Sổ tay nhưng trang khách hàng vẫn hiện

**Không phải lỗi xoá — là lỗi thiếu chức năng.** Danh mục khách hàng gộp **ba nguồn**:

1. `D.open_positions` — sổ chạy của bộ máy chín lớp (backtest)
2. `portfolio.json` — sổ ghi tiến trên GitHub
3. `manual.json` — sổ tay anh Sơn

Mục "Lệnh của tôi" trong Sổ tay **chỉ quản nguồn 3**. ORS mang nhãn *"Hệ thống"*
nghĩa là nó đến từ nguồn 1 — xoá ở Sổ tay không đụng tới nó được, và trước bản này
thì **không có cách nào gỡ** ngoài sửa tay file.

**Chữa:** thêm mục **"Ẩn mã khỏi Danh mục hệ thống"** ở trang Sổ tay. Danh sách `an`
được lưu cùng `manual.json` nên đăng lên là khách hàng cũng không thấy nữa. Có nút
**Hiện lại**. Ô chọn chỉ liệt kê mã đang thực sự nằm trong danh mục, kèm nhãn nguồn
và ngày mua.

⚠️ Ẩn **chỉ giấu khỏi màn hình** — không sửa sổ backtest, không đổi con số hiệu suất,
không đổi tab Kiểm định. Dùng khi bộ máy ghi đang cầm một mã mà ngoài đời anh Sơn
không cầm.

---

# Bản 17 (30/08/2026) — sửa theo hai bản audit ngoài

## Lỗi NẶNG NHẤT đã sửa: survivorship bias

`fireant.py` lọc `exchange in ['HSX','HNX']`, mà cột `exchange` của vnstock là
**trạng thái HÔM NAY**. Mọi mã huỷ niêm yết hoặc bị đẩy xuống UPCOM trong 2019–2026
đều bị vứt khỏi vũ trụ backtest — **1.637 mã DELISTED + 818 mã UPCOM**.

Vì sao nó giết chết độ tin cậy: hệ này mua **chính xác** kiểu phiên mà nhóm FLC tạo
ra năm 2021 — trần, khối lượng gấp đôi, sau một nền tích luỹ. Bỏ chúng khỏi quá khứ
rồi hỏi "hệ bắt trần có lãi không" là đã trả lời trước câu hỏi.

Đã lấy lại: **FLC, ROS, HAI, AMD, KLF, GAB, TGG, ITA, HNG, POM, VNE, PSH, SJF**.
Sàn niêm yết lịch sử suy ra từ biên độ giá quan sát được (HOSE ±7% · HNX ±10% ·
UPCOM ±15%) vì vnstock chỉ biết sàn hôm nay.

| | Trước (694 mã sống sót) | Sau (1.213 mã, có cả mã chết) |
|---|---|---|
| Số lệnh | 147 | **137** |
| Tổng lợi nhuận | +524,5% | **+513,3%** |
| CAGR | 27,08% | **26,78%** |
| Sụt tối đa | 11,97% | **12,43%** |
| Profit Factor | 4,15 | **4,04** |

Edge sống sót. Chênh lệch nhỏ vì bộ lọc TOP-110 + vốn hoá + CANSLIM + cổng rủi ro
vốn đã loại phần lớn nhóm đó. Nhưng bây giờ **con số mới là con số trung thực**.

## Cổng B — "backtest có trade được ngoài đời không" (`cong_b.py`)

### B1 · Thiên lệch khớp giá đóng cửa — chạy lại dưới CẤU HÌNH ĐANG DÙNG

| Giả định khớp lệnh | Lợi nhuận | Sụt | PF |
|---|---|---|---|
| Đóng cửa phiên tín hiệu (đang giả định) | +513,3% | 12,4% | 4,04 |
| Mở cửa phiên sau | +313,5% | 14,5% | 2,90 |
| VWAP phiên sau | +318,2% | 13,9% | 3,09 |
| Đóng cửa + trượt 0,2% | +460,9% | 13,9% | 3,64 |
| Mở cửa phiên sau + trượt 0,2% | +272,2% | 15,9% | 2,61 |

**Mất 39% tổng lợi nhuận** khi bỏ giả định khớp giá đóng cửa. Đây là con số dưới
đúng cấu hình hiện tại, không phải thí nghiệm cấu hình cũ (215 lệnh).

### B2 · Rủi ro KHÔNG khớp được lệnh

**104/137 lệnh (76%) vào đúng phiên chạm trần**; 64 lệnh trong đó có khối lượng
dưới 3× TB20 — dấu hiệu bên bán đã rút.

| Kịch bản | Lợi nhuận trung vị |
|---|---|
| Khớp được hết (giả định hiện tại) | +513,3% |
| Hỏng 10% số lệnh chạm trần | +446,3% |
| Hỏng 25% | +330,5% |
| Hỏng 50% | +194,6% |
| Hỏng 100% | +38,2% |

Đây là **mất luôn cơ hội**, không phải mua đắt hơn — trượt giá không mô phỏng được.

### B3 · Sức chứa vốn

GTGD phiên vào lệnh trung vị **297 tỷ**.

| Vốn | Mỗi lệnh | % GTGD | Lệnh vượt 10% GTGD | Đánh giá |
|---|---|---|---|---|
| 1–10 tỷ | 0,4–4,2 tỷ | 0,1–1,4% | 0–1% | Chạy được |
| 50 tỷ | 21 tỷ | 7,1% | 34% | Bắt đầu chật |
| 100 tỷ | 42 tỷ | 14,2% | 64% | Không chạy được |
| 500 tỷ | 210 tỷ | 70,8% | 99% | Không chạy được |

**Trần thực tế khoảng 20–30 tỷ NAV.**

## Các sửa khác

- `prep.py` — chốt chặn nhìn trước nới từ quý+20 lên **quý+45 ngày**. Kiểm tra cho
  thấy 100% bản ghi có `publicDate` thật, độ trễ trung vị 30 ngày, nhưng có bản ghi
  ghi ngày công bố **trước** ngày hết quý tới 149 ngày — dữ liệu nhà cung cấp lỗi.
- `part6.js` — sửa mâu thuẫn cỡ vị thế: trang 9 lớp ghi 10%/20%/60% trong khi
  production chạy **42%/50%/100%**. Đã ghi rõ 42% là **hơn hai lần Kelly**.
- `p14.js` — hạ nhãn "ĐẠT CẢ NĂM TẦNG" thành **"NGHIÊN CỨU — CHƯA CHẠY TIỀN THẬT"**.
- `p13.js` — sửa bug `h.pct >= h.tran * 0.8` (so % với một cờ true/false).
- `part2.js` — thêm `esc()`, bọc **53 chỗ** nhận chữ do người nhập (chuỗi XSS → token).
- `p3.js` — xoá hàm `pageLive` chết (trùng tên với bản ở `p8.js`).
- `p11.js` — chuẩn hoá `live.json` trước khi vẽ, file hỏng không làm trắng trang.
- `p7.js` — dán nhãn bảng khớp lệnh cũ là **thí nghiệm cấu hình khác**.

## Kiến trúc thông tin hướng khách hàng (`p15.js`)

Menu từ 8 mục xuống **5**: Hôm nay · Cơ hội · Danh mục · Tra cứu mã · Hiệu quả &
Phương pháp. Thứ tự: **hành động → lý do → dữ liệu → phương pháp → bằng chứng**.

**Không xoá trang nào.** 12 trang nghiên cứu vẫn vào được bằng `#tên-trang` và có
lối vào gọn ở cuối trang Hiệu quả.

Thêm cột **"Việc cần làm"** ở Danh mục — dịch bảy luật thoát thành GIỮ / THEO DÕI /
GẦN CẮT LỖ / THOÁT, kèm lý do khi rê chuột.

## Thứ tự chạy (cập nhật)

```
bootstrap.py → fireant.py → fa_prep.py → fetch_funda.py
→ screener.py → watchlist.py → alerts2.py → produce2.py
→ robustness.py → cong_b.py → funda_series.py
→ build_site2.py → verify_build.py → publish.py
```

---

# Bản 19 (30/08/2026) — đổi sang van T+4 và dọn giao diện

## Van thời gian T+6 → T+4

Quét lại trên vũ trụ đúng 1.213 mã. T+4 thắng T+6 ở **cả bốn chỉ số cùng lúc**:

| Van | Lợi nhuận | Sụt | PF | Sharpe | Lệnh |
|---|---|---|---|---|---|
| **T+4 (mới)** | **+523,1%** | **11,34%** | **4,43** | **1,78** | 140 |
| T+5 | +519,7% | 12,14% | 4,17 | 1,78 | 137 |
| T+6 (cũ) | +513,3% | 12,43% | 4,04 | 1,71 | 137 |
| T+7 | +490,6% | 13,19% | 3,80 | 1,67 | 138 |

T+4 và T+5 gần như trùng nhau → **vùng phẳng thật**, không phải đỉnh nhọn.
Walk-forward đóng băng cặp 18%/T+4: thắng **5/8 năm**.

Lãi/lỗ nhảy từ 6,25 lên **8,53** vì lỗ trung bình co từ −3,49% xuống −2,80% —
van cắt sớm hơn hai phiên thì lệnh sai chết nhỏ hơn. Đổi lại tỷ lệ thắng giảm
40,9% → 37,1%: cắt sớm nên vài lệnh lẽ ra hồi được thì bị cắt mất.

**Không đổi gì khác.** Nền vẫn 18%, sàn điểm 45, cỡ vị thế 42%, ngưỡng lãi lớn 19%.

### Vì sao KHÔNG đổi nền xuống 16% hay 14%

Quét trên vũ trụ mới cho đường cong **hình chữ U**:
14% +568% · 16% +530% · **18% +513%** · 20% +497% · **22% +557%**

Thứ tự này **đảo hoàn toàn** so với vũ trụ cũ 694 mã (ở đó nó xuống đều, 14% tốt
nhất, 20% tệ nhất). Chỉ thêm mã vào vũ trụ mà thứ hạng lộn tùng phèo → tham số này
đang bắt **nhiễu**, không phải quy luật. Và walk-forward cặp 16%/T+4 chỉ thắng
**4/8 năm**, lợi thế dồn vào đúng hai năm 2024–2025.

### Ghi chú về cỡ vị thế 42%

Sharpe đạt đỉnh ở **30% NAV** (1,77) chứ không phải 42% (1,71). 42% mua thêm lợi
nhuận bằng cách trả PF 4,70 → 4,04. Kelly tính ra 19,6%, nên 42% là **hơn hai lần
Kelly**. Giữ nguyên vì đây là lựa chọn khẩu vị của anh Sơn, không phải lỗi — nhưng
phải biết mình đang chọn gì.

## Giao diện

- **Ẩn tab Kiểm định** khỏi menu. Vẫn vào được bằng `#kiemdinh`.
  Menu còn 7 mục: Hiệu suất · Chuông báo · Danh mục hệ thống · Watchlist · Bộ lọc ·
  Lịch sử lệnh · Chi tiết mã.
- **Xoá 48 đoạn chú thích nhỏ** (`p.lead` và `p.muted`) trên tám file trang.
  Giữ lại 8 đoạn là **thông báo trạng thái rỗng** ("Chưa có dữ liệu…") — chúng là
  thông tin duy nhất trên màn hình lúc đó, xoá đi thì trang trắng không giải thích.
- **Giữ nguyên mọi khối `.note` và `.note.warn`** — cảnh báo rủi ro, cảnh báo dữ
  liệu cũ, và dòng miễn trừ trách nhiệm không phải chữ trang trí.

## Lưu ý: danh mục giờ rỗng

Không phải lỗi. Dưới van T+4, ORS bị cắt ngày **27/08 ở −4,85%** (van thời gian)
thay vì còn cầm tới 28/08. Đây cũng là ví dụ trực tiếp về tác dụng của T+4: lệnh
sai bị đẩy ra sớm hơn một phiên.

## Bản 20 — dọn sạch chữ chú thích trên trang khách hàng

Xoá **16 khối `.note`** trên bảy trang khách hàng thấy (Hiệu suất · Chuông báo ·
Danh mục · Watchlist · Bộ lọc · Lịch sử lệnh · Chi tiết mã), gồm:

- "Cách đọc cho đúng — đây là kết quả mô phỏng…"
- "Cách trang này cập nhật…"
- "Sổ này khác backtest ở đâu…" và "Cập nhật lúc nào…"
- "Ngưỡng vào danh sách mua…"
- Hướng dẫn dùng biểu đồ ("lăn chuột để phóng to…") — chỉ còn dòng
  `N phiên · nguồn VPS · N dấu bot`
- Thông báo rỗng dài dòng ở Chuông báo → còn đúng một dòng "Chưa có mã nào."

**Không đụng tới:** trang Kiểm định (đã ẩn), Sổ tay, Bằng chứng — và **dòng miễn
trừ ở chân trang** vẫn nguyên: *"Đây là công cụ nghiên cứu, không phải khuyến nghị
đầu tư. Kết quả quá khứ không đảm bảo kết quả tương lai."* Dòng đó hiện trên mọi
trang nên bỏ các khối trong thân trang không làm mất phần cảnh báo pháp lý.

Chữ trên trang Hiệu suất giảm 3.289 → 2.024 ký tự, Danh mục 1.602 → 315.

## Bản 21 — sửa ba lỗi tài liệu/logic từ audit ngoài

### 1. Thang điểm: 100, KHÔNG phải 105 — audit sai, trang hiển thị sai

Cộng thật từ `canslim_score`: C1 15 + C2 15 + C3 5 + A1 10 + A2 10 + N 10 + S 5 +
L 15 + I 10 = **95 cố định**. Cộng `Mom = round(5 × mom3, 1)`, mà
`mom3 = pct_rank(r3)` luôn nằm trong **[0, 1]** → Mom tối đa **5**.

**Tổng tối đa = 100.** Cơ bản 55 · kỹ thuật **45** (không phải 50).
Kiểm bằng dữ liệu: điểm cao nhất trong 1.213 mã là **HCC 89,2**, không mã nào >100.

Nên trang "Hệ thống 9 lớp" ghi "Thang 100 điểm" là ĐÚNG; chỗ sai là `/105` ở
`p9.js` (ô chỉ số cạnh biểu đồ) và `p15.js`. Đã sửa cả hai về `/100` và ghi thêm
tách 55/45.

### 2. Ranh giới LNST YoY 25% — luật đúng, NHÃN sai

Mã nguồn thực ra nhất quán:
- Chấm điểm `npat_g >= 0.25` → đúng 25,00% **được** +15
- Cửa 5 `0 <= npg < 0.25` → đúng 25,00% **không** bị chặn

Không mã nào vừa được cộng điểm vừa bị loại. Lỗi nằm ở **nhãn làm tròn 0 chữ số**:
BAX có YoY thật 24,5% nhưng in ra "tăng 25% (0–25%)" — đọc như hệ tự mâu thuẫn.

Đã sửa `lookup.py` và `alerts2.py`: in **một chữ số thập phân** và ghi khoảng bằng
bất đẳng thức rõ — `vùng yếu: 0% ≤ x < 25%`. BAX giờ hiện **24,5%**.

> Còn một điểm thiết kế đáng bóc, chưa sửa: **LNST âm tự động lọt qua Cửa 5** vì
> nó không nằm trong `[0, 25%)`. Doanh nghiệp lỗ nặng qua cửa này dễ hơn doanh
> nghiệp tăng 20%, rồi phải trông vào cổng rủi ro cứu. Ghi lại để xem xét.

### 3. Sót "đã hạ về 10% NAV" — audit đúng

`part6.js` phần Kelly vẫn còn câu cũ. Đã sửa: ghi rõ đang chạy **42% NAV — hơn hai
lần full-Kelly**, kèm số liệu Sharpe đỉnh ở 30% (1,77) so với 42% (1,71).

### Kèm theo: dọn nốt "T+6" còn sót sau khi đổi sang T+4

`p3.js` (chú thích đường vốn, nhãn preset), `p4.js` (ba chỗ), `p15.js` (bảng
việc-cần-làm). Preset `tvalve4` nay trùng PROD nên đổi thành **`tvalve6` — cấu
hình cũ trước 30/08**, để bảng so sánh vẫn còn ý nghĩa.
