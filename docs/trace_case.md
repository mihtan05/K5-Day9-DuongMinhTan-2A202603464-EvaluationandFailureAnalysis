# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

## Case: `seeded_regression C-002@11`

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run `E-seeded_regression-20261117-e031` (eval set `e031e77567d8`) |
| Triệu chứng | `TrialPass` FAIL (status resolved ≠ denied), `refund_amount_correct` FAIL, `db_fact_kept` FAIL. Ledger ghi 20.000đ / 1 dòng, label 0 / 0. Reply "Dạ, LogiX đã hoàn 20.000đ cho đơn O-202." — khớp ledger nên FM-08 không fire; reply trôi chảy nhưng tiền sai. |
| Bước sai đầu tiên | Event **3** `model_override {"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event 1 `handoff` đúng claim, tool chỉ đọc. Event 2 `investigator` đọc DB đúng: O-202 `delay_days` 2. Từ event 3 agent thay 2 bằng 5 lấy từ ticket ("giao trễ 5 ngày"); event 4 `quote` 20.000 (SHIP-LATE-03, min 3 ngày) chỉ là hệ quả. |
| Failure mode | FM-03 ticket_trust |
| Đối chứng | `fixed C-002@11`: không có event `model_override`; event 3 `quote {"amount_vnd": 0, "reason": "no_entitlement"}` → denied, ledger 0, PASS. Baseline `swarm` cũng dính đúng lỗi này ở C-002@55 (điểm yếu seed % 5 == 0). |
| Regression test | `src/tests/test_lab9_trace_case.py::test_c002_ticket_trust_fm03`: chạy C-002@11, assert `DbFactKept` và `RefundAmountCorrect`. Đã thấy FAIL trên `seeded_regression` và PASS trên `fixed` (2 case parametrize đều xanh). |
| Chưa chắc chắn | Trace không cho biết *vì sao* model chọn ticket (MockLLM là công tắc cứng). Với LLM thật, `quiet_override` (tin ticket mà không ghi event) sẽ qua `db_fact_kept`; chỉ `refund_amount_correct` trên ledger còn bắt được. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
