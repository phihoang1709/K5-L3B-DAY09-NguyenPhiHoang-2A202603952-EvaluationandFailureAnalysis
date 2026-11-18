## Kế hoạch hoàn thiện Lab 9 (Evaluation & Failure Analysis) — fork K5-L3B-DAY09-NguyenPhiHoang-2A202603952

Fork hiện là starter sạch 0%. Hoàn thành **toàn bộ M0–M7** và nộp đúng quy trình: nhánh `starter/d09` → PR trong fork → CI xanh → merge vào `main` (Core là PR #1, Advanced/Expert là PR #2).

1. **Preflight**: kiểm tra `git remote` (phải là fork của bạn), `gh auth`, Python 3.11–3.13; tạo nhánh `starter/d09`.
2. **M0**: clone repo gốc Day 8, chép `src/` vào fork, tạo venv + cài deps, `lab9.smoke` PASS, `lab9.evalset --build` → eval_set_v1 + labels_v1. Commit.
3. **M1**: đọc trace swarm thật, điền `docs/failure_taxonomy.md` (≥5 FM), gắn `failure_modes` vào eval set, `evalset --check` 0 lỗi.
4. **M2**: implement TODO M2 trong `stats.py` (confusion, P/R, kappa, Rogan-Gladen — self-check với test tham chiếu của giảng viên), chạy `lab9.judge --audit 5`, điền `docs/judge_audit.md`.
5. **M3**: implement `ApprovalBypass`, `RefundAmountCorrect` + metric FM-08 trong `graders.py`/spec (đăng ký `GRADERS`), pytest core xanh; viết `docs/trace_case.md` + regression test.
6. **M4**: implement `paired_bootstrap`, sinh 3 reports (`baseline_v1`, `eval_fixed`, `eval_seeded_regression` — `git add -f`), gate: seeded_regression exit 1 / fixed exit 0; merge `harness_map.eval.yaml` vào `harness_map.yaml`.
7. **Docs Core**: `eval_card.md`, `PRD_v1.1.md`. Push, mở PR #1 trong fork (mô tả dán output gate exit 1), bật Actions (gh API hoặc bạn bấm tay), chờ `eval-gate` xanh, **merge**.
8. **M5**: điền `fm_map.yaml`, `evalset --v2 --build`, TODO `metric_spec_v2.yaml` + `gate.slice_check`, baseline_v2.
9. **M6**: `stats.pass_at_k/pass_hat_k`, chạy `mutation --aa`, chọn ngưỡng ngoài dải nhiễu A/A.
10. **M7**: `gate.integrity_check` (NaN, số dòng, tập (item,seed), ratchet vs `--base-spec`...), `lab9.traps` exit 0, `lab9.mutation` scorecard exit 0, pytest advanced xanh, thêm mục v2 vào eval_card.
11. **PR #2**: push, PR mới (mô tả dán mutation scorecard + `--aa` + 4 dòng trap exit 1), `eval-gate-v2` xanh, merge trước hạn LMS.

**Ràng buộc**: không sửa `src/lab8/`, không sửa tay reports, labels tách khỏi item, grader viết tổng quát (chấm bằng variant ẩn), ngưỡng không hạ để 'bắt' bug 1/3 seed.
**Verify**: smoke, evalset check v1+v2, judge đạt sàn κ/P/R, pytest core+advanced, gate exit1/exit0, mutation exit 0, traps exit 0, CI xanh cả 2 PR, main đủ docs+reports để nộp LMS.