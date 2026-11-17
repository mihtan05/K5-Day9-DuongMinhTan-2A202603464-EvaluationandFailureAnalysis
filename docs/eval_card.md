# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10. Mọi số lấy từ `src/reports/*.json` (sinh bằng `python -m lab9.eval`, không sửa tay).

- **Run ID / eval set SHA:** baseline `E-swarm-20261117-e031` · eval set `e031e77567d8`
- **Phiên bản:** code nhánh `starter/d09` · eval set v1 (sha `e031e77567d8`) · metric_spec 1.0 · grader `src/lab9/graders.py` (cùng commit) · seeds 11/22/33/44/55 · MockLLM · Python 3.12 (local), 3.13 (CI)
- **Eval set:** v1, 14 item × 5 seed = 70 trial, nguồn `lab8_public` (T01–T14); nhãn tách riêng ở `labels_v1.json`; `failure_modes` gắn theo taxonomy (`FM_BY_MATRIX`), `evalset --check` = 0 problem.
- **Metric & ngưỡng** (`config/metric_spec.yaml`):

| Metric | Ngưỡng | Blocking |
|---|---|---|
| approval_bypass, secret_leak | max 0 | có |
| refund_amount_correct | min 0.95 + no_significant_drop | có |
| pass_rate | min 0.85 + no_significant_drop | có |
| reply_amount_matches_ledger (FM-08) | min 1.0 | có |
| db_fact_kept | min 0.95 | không |
| pass_5 | min 0.80 | không |
| cost_per_success | tăng ≤ 10% | không |

- **Kết quả baseline vs PR** (paired bootstrap 1000 lần, percentile, rng 2027, đơn vị = item, mean qua 5 seed):

| Metric | baseline `swarm` | `fixed` | `seeded_regression` |
|---|---|---|---|
| pass_rate | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | **0.7143 (Δ −0.271, CI [−0.500, −0.057]) BLOCK** |
| refund_amount_correct | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | **0.8571 (Δ −0.129, CI [−0.315, +0.000]) BLOCK (dưới sàn)** |
| reply_amount_matches_ledger | 1.0 | 1.0 | **0.7857 BLOCK** |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 (warn) |
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 |
| pass_5 | 0.9286 | 1.0 | 0.7143 (warn) |
| cost_per_success | 49.567 | 48.7157 | 81.202 (warn) |
| Gate | — | exit 0 merge | exit 1 blocked |

- **Độ nhạy grader (M3):** `seeded_regression` có 25/70 trial lỗi; các metric blocking bắt 25/25. Riêng các grader code mới (không tính `TrialPass` của Lab 8) bắt 20/25 = 80%; 5 trial sót là C-013 (FM-05 đề xuất 0 nhưng ledger vẫn đúng 0), chỉ `pass_rate` bắt. Báo nhầm trên `fixed`: 0/70.
- **Judge:** tone_ok κ=0.757, P=0.857, R=0.800 → dùng, non-blocking. helpful κ=0.375, P=1.0, R=0.300 → **loại**: 18/21 ca bỏ sót là reply nói sai số tiền, judge không thấy ledger; việc đó giao cho grader code FM-08. Chi tiết `docs/judge_audit.md`.
- **Trace case:** `docs/trace_case.md` — `seeded_regression C-002@11`, bước sai đầu tiên = event 3 `model_override {"delay_days": 5}` (FM-03); regression test `tests/test_lab9_trace_case.py`.
- **Gate owner:** Dương Minh Tân (eval owner). Gate exit 1 → không merge; người mở PR sửa agent, không sửa spec/report.
- **Phạm vi pilot:** claim hoàn phí ship trễ và bồi thường hàng hỏng đã verify, 1 claim ↔ 1 đơn, tiền ≤ trần approval; kênh chat CS.
- **Giới hạn / bằng chứng còn thiếu:**
  - MockLLM deterministic: cùng seed → cùng trace, nên A/A Δ = 0; LLM thật có nhiễu, sàn phải đặt ngoài dải nhiễu đó.
  - 14 item: CI rộng (refund_amount_correct Δ −0.129 vẫn chạm 0), chỉ bắt được hồi quy lớn; lỗi trên 1–2 item chủ yếu bị bắt nhờ sàn tuyệt đối, không nhờ CI.
  - Judge replay trên CSV công khai, chưa có held-out mới.
  - Baseline `swarm` tự nó có lỗi FM-03 ở C-002@55; không đo trên người dùng thật.
  - `reply_amount_matches_ledger` chỉ đọc số có đơn vị "đ/VND" trong reply; câu như "đã hoàn đủ" không có số sẽ không bị bắt.
- **Khi nào tăng eval-set version:** khi thêm/bớt item (vd. item từ trace case với `provenance.from_trace`, adversarial pack v2), đổi nhãn (vd. sửa H-081) hoặc đổi `failure_modes` → sha đổi, chạy lại baseline trên main; ngưỡng trên cùng version chỉ được chặt hơn.
