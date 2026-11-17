# Bonus: port 3 grader sang Inspect AI và so khớp

```bash
cd src
pip install -r requirements-bonus.txt      # inspect-ai 0.3.280 (+ agent-client-protocol 0.12.1, xem dưới)
python -m lab9.inspect_port                 # exit 0 = hai harness đồng ý trên mọi (item, seed)
```

## Cách port
- **Harness:** `inspect_ai.Task`, 1 `Sample` = item@seed của eval set v1 (sha `e031e77567d8`), target = nhãn JSON từ `labels_v1.json` (vẫn tách khỏi item).
- **Solver `run_shape`:** "agent" là shape Lab 8, không phải model: chạy cùng `lab9.eval.make_task` (SQLite mới cho mỗi trial), lưu Trial vào `state.store`, reply cuối vào `state.output`. Model `mockllm/model` không bao giờ được gọi → chạy offline, không key.
- **3 scorer viết lại native** (không bọc class pydantic-evals, để phép so khớp kiểm được logic chứ không chỉ kiểm cùng một hàm):

| Scorer Inspect | Grader pydantic-evals | Đọc gì |
|---|---|---|
| `approval_bypass` | `ApprovalBypass` (safety) | ledger: refund khi `approval_ok` false, dòng ledger lạ |
| `refund_amount_correct` | `RefundAmountCorrect` | ledger `refund_vnd` vs nhãn |
| `reply_amount_matches_ledger` | `ReplyAmountMatchesLedger` (FM-08) | `state.output.completion` vs ledger |

Inspect dùng CORRECT/INCORRECT + `accuracy()`; safety được quy về "CORRECT = không vi phạm" khi so.

## Kết quả (`python -m lab9.inspect_port`, MockLLM, 14 item × 5 seed)

| Shape | approval_bypass | refund_amount_correct | reply_amount_matches_ledger |
|---|---|---|---|
| swarm (`baseline_v1.json`) | 70/70 khớp · pass 70 | 70/70 · pass 69 | 70/70 · pass 70 |
| fixed (`eval_fixed.json`) | 70/70 · 70 | 70/70 · 70 | 70/70 · 70 |
| seeded_regression | 70/70 · 70 | 70/70 · 60 | 70/70 · 55 |
| xcheck_sibling_refund | 70/70 · **50** | 70/70 · 50 | 70/70 · 70 |
| xcheck_misreport | 70/70 · 70 | 70/70 · 70 | 70/70 · **60** |

**1050/1050 quyết định khớp**, kể cả 20 vi phạm approval, 30 sai số tiền ledger và 25 reply sai số tiền. Hai shape `xcheck_*` (bật đúng 1 công tắc lỗi có sẵn, dựng trong `inspect_port.py`, không sửa `variants.py`) được thêm vì trên 3 shape mặc định `approval_bypass` không fire lần nào — "khớp 100%" trên toàn PASS không chứng minh được gì.

## Nhận xét
- Logic grader không phụ thuộc framework: cùng Trial → cùng quyết định. Khác biệt chỉ ở hình thức: Inspect lưu log `.eval` từng sample (xem bằng `inspect view`), có sẵn `epochs` cho nhiều seed; pydantic-evals nhẹ hơn và cho report JSON mà gate đọc trực tiếp.
- Gate/CI vẫn dùng pydantic-evals; Inspect chỉ là kiểm chéo (`requirements-bonus.txt` không nằm trong CI).
- **Lỗi phụ thuộc gặp phải:** `inspect-ai 0.3.280` khai `agent-client-protocol>=0.12.0` không có cận trên; pip kéo 1.0.0, bản này bỏ `acp.helpers` mà Inspect import → `eval()` crash. Pin `agent-client-protocol==0.12.1`.
- Test: `tests/test_lab9_bonus_inspect.py` (tự skip nếu chưa cài Inspect).
