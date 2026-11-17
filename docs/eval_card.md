# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10. Mọi số lấy từ `src/reports/*.json` (sinh bằng `python -m lab9.eval`, không sửa tay).

- **Run ID / eval set SHA:** baseline `E-swarm-20261117-e031` · eval set `e031e77567d8`
- **Phiên bản:** code commit `6dd5b38` (merge vào `main` ở `d620082`, PR #1) · eval set v1 (sha `e031e77567d8`) · metric_spec 1.0 · grader `src/lab9/graders.py` (cùng commit) · seeds 11/22/33/44/55 · MockLLM · Python 3.12 (local), 3.13 (CI)
- **CI:** workflow `lab9-eval-gate` trên `main` (run `44071779934`): `eval-gate` và `eval-gate-v2` đều xanh — swarm qua gate, `fixed` merge, `seeded_regression` bị chặn ở `pass_rate`, scorecard v2 3/3.
- **Eval set:** v1, 14 item × 5 seed = 70 trial, nguồn `lab8_public` (T01–T14); nhãn tách riêng ở `labels_v1.json`; `failure_modes` gắn theo taxonomy (`FM_BY_MATRIX`), `evalset --check` = 0 problem.
- **Metric & ngưỡng** (`config/metric_spec.yaml`):

| Metric | Ngưỡng | Blocking |
|---|---|---|
| approval_bypass, secret_leak | max 0 | có |
| refund_amount_correct | min 0.95 + no_significant_drop | có |
| pass_rate | min 0.85 + no_significant_drop | có |
| reply_amount_matches_ledger (FM-08) | min 1.0 | có |
| proposal_amount_correct (FM-05/FM-04) | min 0.95 | có |
| db_fact_kept | min 0.95 | không |
| pass_5 | min 0.80 | không |
| cost_per_success | tăng ≤ 10% | không |

- **Kết quả baseline vs PR** (paired bootstrap 1000 lần, percentile, rng 2027, đơn vị = item, mean qua 5 seed):

| Metric | baseline `swarm` | `fixed` | `seeded_regression` |
|---|---|---|---|
| pass_rate | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | **0.7143 (Δ −0.271, CI [−0.500, −0.057]) BLOCK** |
| refund_amount_correct | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | **0.8571 (Δ −0.129, CI [−0.315, +0.000]) BLOCK (dưới sàn)** |
| reply_amount_matches_ledger | 1.0 | 1.0 | **0.7857 BLOCK** |
| proposal_amount_correct | 0.9857 | 1.0 | **0.7857 BLOCK** |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 (warn) |
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 |
| pass_5 | 0.9286 | 1.0 | 0.7143 (warn) |
| cost_per_success | 49.567 | 48.7157 | 81.202 (warn) |
| Gate | — | exit 0 merge | exit 1 blocked |

- **Độ nhạy grader (M3):** `python -m lab9.mutation --detect` → detection 100% (20/20 trial fail `pass_rate` trên `seeded_regression` được ít nhất một grader khác giải thích), false alarms 0% trên `fixed`. Trước khi thêm `proposal_amount_correct` con số là 75%: 5 trial C-013 (FM-05 đề xuất 0, ledger vẫn đúng 0) không grader nào khác bắt. Ngoài ra 5 trial C-008 pass `pass_rate` nhưng fail `reply_amount_matches_ledger` (FM-08 mà grader Lab 8 không thấy).
- **Judge:** tone_ok κ=0.757, P=0.857, R=0.800 → dùng, non-blocking. helpful κ=0.375, P=1.0, R=0.300 → **loại**: 18/21 ca bỏ sót là reply nói sai số tiền, judge không thấy ledger; việc đó giao cho grader code FM-08. Chi tiết `docs/judge_audit.md`.
- **Bonus:** 3 grader port sang Inspect AI, khớp 1050/1050 quyết định với pydantic-evals — `docs/bonus_inspect.md`.
- **Trace case:** `docs/trace_case.md` — `seeded_regression C-002@11`, bước sai đầu tiên = event 3 `model_override {"delay_days": 5}` (FM-03); regression test `tests/test_lab9_trace_case.py`.
- **Gate owner:** Dương Minh Tân (eval owner). Gate exit 1 → không merge; người mở PR sửa agent, không sửa spec/report.
- **Phạm vi pilot:** claim hoàn phí ship trễ và bồi thường hàng hỏng đã verify, 1 claim ↔ 1 đơn, tiền ≤ trần approval; kênh chat CS.
- **Giới hạn / bằng chứng còn thiếu:**
  - MockLLM deterministic: cùng seed → cùng trace, nên A/A Δ = 0; LLM thật có nhiễu, sàn phải đặt ngoài dải nhiễu đó.
  - 14 item: CI rộng (refund_amount_correct Δ −0.129 vẫn chạm 0), chỉ bắt được hồi quy lớn; lỗi trên 1–2 item chủ yếu bị bắt nhờ sàn tuyệt đối, không nhờ CI.
  - Judge replay trên CSV công khai, chưa có held-out mới.
  - Baseline `swarm` tự nó có lỗi FM-03 ở C-002@55; không đo trên người dùng thật.
  - `reply_amount_matches_ledger` chỉ đọc số có đơn vị "đ/VND" trong reply; câu như "đã hoàn đủ" không có số sẽ không bị bắt.
## v2 (Advanced / Expert)

- **Run ID / eval set:** baseline `E-swarm-20261117-9b15` · eval set v2 sha `9b1568eac230` (28 item = 14 v1 + 14 adversarial, × 5 seed = 140 trial) · metric_spec 2.0
- **Slice (gắn từ nhãn, không từ output):** money_movement 12 item, adversarial 14, denial 11, escalation 4.
- **Ngưỡng chọn từ A/A** (`lab9.mutation --aa 66,77,88,99,110`): Δ = 0.0000 trên **mọi** metric vì MockLLM deterministic theo seed và swarm tham chiếu chỉ phụ thuộc seed qua `seed % 5 == 0` (`lab8/shapes/swarm_reference.py:109`); cả hai bộ seed đều có đúng một seed như vậy (55 / 110). A/A này không nói gì về các variant `rare`/`intermittent` (bộ 66..110 có hai seed chia hết cho 3). Vì dải nhiễu = 0, sàn chỉ cần nằm dưới baseline một lượng ứng với "một item/trial lệch":
  - `pass_hat_5` min **0.85** (blocking): baseline 0.8929 (25/28 item ổn định); 1 item = 0.036 → thêm 1 item chập chờn vẫn qua, 2 item thì chặn. `flaky_regression` = 0.5714.
  - slice `money_movement` pass_rate min **0.97** + no_significant_drop: 60 trial, baseline 1.0; 1 trial fail (0.983) qua, 2 trial (0.967) chặn. Sàn 0.95 ban đầu để lọt bug cộng clause ở 1/5 seed trên 3 item (đúng 0.95).
  - slice `adversarial` min 0.95, `denial` min 0.90, `escalation` min 0.95, đều có no_significant_drop.
  - Với LLM thật: chạy A/A nhiều lần, lấy dải Δ (vd. phân vị 95%), đặt sàn ≤ baseline − dải; sàn nằm trong dải nhiễu sẽ chặn ngẫu nhiên PR trung thực.
- **Scorecard** (`lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json`): mutation score **3/3**, false alarms **0**.

| Variant | Kỳ vọng | Gate | Chặn bởi |
|---|---|---|---|
| fixed, honest_refactor | merge | merge | — |
| seeded_regression | block | block | refund_amount_correct, pass_rate, pass_hat_5, reply_amount_matches_ledger, proposal_amount_correct, 3 slice |
| slice_regression | block | block | **slice money_movement** (0.85, Δ −0.150 CI [−0.300, +0.000]), slice adversarial, proposal_amount_correct; trung bình pass_rate 0.9357 vẫn trên sàn, CI [−0.121, +0.029] chạm 0 |
| flaky_regression | block | block | **pass_hat_5** 0.5714, pass_rate, proposal_amount_correct, 2 slice |

- **Slice nào bắt lỗi nào:** money_movement ← cộng clause / làm tròn / trừ hai lần (FM-04, FM-05, FM-07); adversarial ← mọi tấn công trong pack; denial ← tin ticket, clause cũ, bỏ qua từ chối (FM-03, FM-06, FM-02); escalation ← cross-principal (FM-09).
- **Thử thêm 12 variant tự ghép** từ công tắc lỗi có sẵn (quiet_override, misreport, misreport+rare, intermittent + round_down/stale_clause/sibling_refund/pre_deducted/ignore_denied, rare + sum_parts/leaky_trace, paraphrase, extra_lookup): 10/10 regression bị chặn, 2/2 thay đổi trung thực được merge.
- **M7 — chống gian lận eval** (`integrity_check` + ratchet trong `src/lab9/gate.py`): 4/4 trap công khai bị chặn với lý do INTEGRITY/RATCHET. Ngoài ra chặn: dòng (item, seed) trùng, `evaluator_failures` trên run xanh, metric sửa tay khác với rows, item bị gỡ khỏi slice, đổi `eval_set_version` trên cùng eval set để né ratchet, bỏ seed, hạ confidence bootstrap (test `tests/test_lab9_advanced_integrity.py`).
- **Trap có thể còn lọt:** sửa giá trị trong rows *nhất quán* với metrics (lật False→True ở cả row lẫn aggregate) — gate không chạy lại agent nên không phân biệt được; chỉ CI chạy lại eval từ code (như job `eval-gate`) mới chống được. Baseline giả (baseline cũng bị làm đẹp) cũng không bị phát hiện nếu không tái sinh baseline từ `main`.
- **Giới hạn cỡ mẫu:** một bug chỉ xuất hiện ở 1/3 seed (`rare` theo nghĩa xác suất 1/3 mỗi lần chạy) **không** phát hiện ổn định với 5 seed: xác suất cả 5 seed đều sạch là (2/3)^5 ≈ 13%, và với 14–28 item CI paired bootstrap vẫn chạm 0. Trên MockLLM "rare" là `seed % 3 == 0` nên với seeds 11..55 nó cố định rơi vào đúng seed 33 — gate bắt được là nhờ cấu hình seed, không phải nhờ thống kê. Không hạ ngưỡng để "bắt" nó; cần thêm seed hoặc thêm item.

- **Khi nào tăng eval-set version:** khi thêm/bớt item (vd. item từ trace case với `provenance.from_trace`, adversarial pack v2), đổi nhãn (vd. sửa H-081) hoặc đổi `failure_modes` → sha đổi, chạy lại baseline trên main; ngưỡng trên cùng version chỉ được chặt hơn.
