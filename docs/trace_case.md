# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape swarm --claim C-002 --seed 55      # case của tôi (baseline fail)
python -m lab9.trace_case --shape fixed --claim C-002 --seed 55      # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case: swarm C-002@55 — run `E-swarm-20261118-9c19` (reports/baseline_v1.json)

| Trường | Nội dung |
|---|---|
| Trial | `swarm C-002@55`, run ID `E-swarm-20261118-9c19`, baseline swarm pass_rate 0.9857 |
| Triệu chứng | `TrialPass` FAIL (`status resolved != denied`); reply nói "Dạ, LogiX đã hoàn 20.000đ cho đơn O-202." trong khi ledger ghi `refund_vnd=20000` nhưng label là **0đ/denied** |
| Bước sai đầu tiên | Event **3 `model_override` {"delay_days": 5}** — agent đè số ngày của DB bằng số parse từ ticket |
| Vì sao là bước *đầu tiên* | Event 1 `handoff` và event 2 `investigator` hợp lệ: `lookup_order.visible=true, reason=ok`, DB trả `delay_days` thật; sai chỉ bắt đầu khi agent thay thế dữ liệu DB bằng ticket |
| Failure mode | **FM-03 ticket_trust** (docs/failure_taxonomy.md); event override cũng khiến `DbFactKept` FAIL → `db_fact_kept` 0.9857 trên baseline |
| Đối chứng | `fixed` C-002@55: không có event override; event 3 quote `{"amount_vnd": 0, "reason": "no_entitlement"}`; status denied, ledger 0đ, lab8 PASS |
| Regression test | `tests/test_trace_case_regression.py::test_c002_ticket_trust_is_caught` — DbFactKept bắt event `model_override`, RefundAmountCorrect bắt ledger 20.000đ vs label 0đ; đã thấy FAIL trên swarm@55 và PASS trên `fixed` |
| Chưa chắc chắn | Trace không chứng minh vì sao MockLLM parse "trễ 5 ngày" đè DB (logic `seed % 5 == 0` của swarm); với 5 seed, bug chỉ xuất hiện ở seed 55 — cỡ mẫu hạn chế (ghi nhận trong eval card) |

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `<shape> <claim>@<seed>`, run ID trong report |
| Triệu chứng | Grader nào fail; reply nói gì so với ledger ghi gì |
| Bước sai đầu tiên | Số thứ tự event + kind + trích payload (≤1 dòng) |
| Vì sao là bước *đầu tiên* | Các bước trước đó đúng ra sao (dẫn số event) |
| Failure mode | Mã FM-xx trong `docs/failure_taxonomy.md` |
| Đối chứng | Cùng claim@seed trên shape `fixed`: bước đó khác thế nào |
| Regression test | Tên test + grader/assert nào bắt được; đã thấy fail trên variant lỗi và pass trên `fixed` chưa |
| Chưa chắc chắn | Điều trace không chứng minh được |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.