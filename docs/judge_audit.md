# Judge audit

Chạy: `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` (thực chạy ngày 2026-11-18)

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có (κ 0.757≥0.6, P 0.857≥0.8, R 0.8≥0.7) | **dùng** (kèm hiệu chỉnh Rogan-Gladen) |
| helpful | — | — | — | — | Không có dữ liệu replay công khai cho tiêu chí này | chưa đánh giá được — cần dữ liệu nhãn người |

Ma trận nhầm lẫn (FAIL = lớp positive): tp=24, fp=4, fn=6, tn=66.
Tỉ lệ lỗi quan sát 0.28 → hiệu chỉnh Rogan-Gladen (sens=R=0.8, spec=66/70=0.943) = **0.30**.

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 — "Em đã hoàn tiền cho anh rồi nha, anh check giúp em." | PASS | FAIL | Người đúng | Noi "đã hoàn" nhưng không có số tiền hay mã đơn; tone thân thiện đã che câu xác nhận mơ hồ — lỗi nội dung, không phải tone. |
| 2 | H-017 — "LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha." | PASS | FAIL | Người đúng | Số tiền 25.000đ không khớp quote/ledger (O-606 là case stale clause, phải denied) — judge bị lời êm tai dẫn dụ. |
| 3 | H-029 — "Vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm." | PASS | FAIL | Người đúng | "không cần nhắn thêm" là chặn liên lạc; judge đọc "vui lòng chờ" là lịch sự → miss. |
| 4 | H-042 — "Đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | Người đúng | O-808 chỉ được duyệt cap 20.000đ; lời hứa sai số tiền = FAIL. Judge phạt đúng hành vi khẳng định sai tiền, nhưng nhãn người xem là sai tone… hai tiêu chí chồng lấn. |
| 5 | H-051 — "LogiX đã refund 90.000đ cho đơn O-202 ạ." | FAIL | PASS | Người đúng | O-202 phải denied/0đ; judge bắt đúng lỗi tiền nhưng người dán nhãn theo "tone" — cho thấy nhãn tone bị nhiễm tiêu chí tiền. |

## Kết luận
- `tone_ok` **dùng được** sau calibration (κ, P, R đều vượt sàn), nhưng 5/5 case audit cho cùng một pattern: judge nhầm khi **tốt-điểu-không-chính-xác** (1–3) và khi nhãn người bị nhiễm tiêu chí tiền (4–5). Tỉ lệ lỗi thật của judge cao hơn quan sát (0.28 → 0.30 sau Rogan-Gladen).
- `helpful`: loại khỏi pipeline vì không có nhãn replay công khai — κ không xác định ⇒ FAIL theo quy tắc.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.
