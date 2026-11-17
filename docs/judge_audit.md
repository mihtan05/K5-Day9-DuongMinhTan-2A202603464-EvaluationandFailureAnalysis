# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5` (backend replay, FAIL = lớp dương).

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Đạt | dùng (non-blocking, chỉ cho tone) |
| helpful | 100 | 0.375 | 1.000 | 0.300 | **Không** (κ, R dưới sàn) | loại |

Ma trận nhầm lẫn:
- tone_ok: tp 24, fp 4, fn 6, tn 66. Tỉ lệ FAIL quan sát 0.28 → Rogan-Gladen 0.30.
- helpful: tp 9, fp 0, fn 21, tn 70. Tỉ lệ FAIL quan sát 0.09 → Rogan-Gladen 0.30 (judge bỏ sót 2/3 lỗi).

## ≥5 case audit thủ công (tone_ok, 10/10 bất đồng + 3 case helpful)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú / sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 "Em đã hoàn tiền cho anh rồi nha…" | PASS | FAIL | Người | Rubric thêm: xưng "em/anh", "nha" là suồng sã với khách → FAIL. |
| 2 | H-017 "Dạ, bạn ơi LogiX đã hoàn…" | PASS | FAIL | Người | Rubric: xưng hô chuẩn "anh/chị"; "bạn" → FAIL. |
| 3 | H-029 "…không cần nhắn thêm." | PASS | FAIL | Người | Judge chỉ thấy "Dạ, vui lòng". Rubric: câu mệnh lệnh/gạt khách → FAIL dù có kính ngữ. |
| 4 | H-042 "…Tiền về trong 3–5 ngày ạ." | FAIL | PASS | Người | Judge phạt "thiếu xin lỗi". Rubric: xin lỗi không bắt buộc khi đã giải quyết xong. |
| 5 | H-051 "LogiX đã refund 90.000đ…" | FAIL | PASS | Người | Rubric: từ "refund" nằm trong whitelist thuật ngữ CS. |
| 6 | H-063 "…và sẽ hoàn thêm cho anh/chị ạ." | PASS | FAIL | Người | Hứa ngoài kết quả hệ thống — thực ra là lỗi nội dung, không phải tone; chuyển sang grader code (so reply với ledger, FM-08). |
| 7 | H-070 "…ạ 😂😂" | PASS | FAIL | Người | Rubric: emoji cười trong khiếu nại → FAIL. |
| 8 | H-081 "…chưa đủ điều kiện hoàn…" | FAIL | PASS | **Judge** | Nhãn người sai (đọc nhầm ticket) → sửa nhãn trong CSV đợt sau, ghi lại người sửa. |
| 9 | H-088 "Dạ, dạ, LogiX đã hoàn…" | FAIL | PASS | Không rõ | Lỗi gõ nhỏ; rubric ghi rõ lặp từ không làm FAIL tone. |
| 10 | H-094 "Da, LogiX da hoan…" (mất dấu) | PASS | FAIL | Người | Rubric: mất dấu tiếng Việt → FAIL. |
| 11 | HL-015 "đã hoàn 55.000đ" (ledger 40.000) | PASS | FAIL | Người | Judge không thấy ledger → không thể chấm đúng số tiền. |
| 12 | HL-047 "Ok bạn, đơn O-515 xử lý rồi nhé." | PASS | FAIL | Người | Không nói số tiền/kết quả → không helpful. |
| 13 | HL-016 xin lỗi dài + "đã hoàn 55.000đ" (ledger 35.000) | PASS | FAIL | Người | Judge bị câu xin lỗi dài "mua" điểm. |

## Kết luận
- **helpful bị loại**: R = 0.30 (21 fn / 30 FAIL thật), κ = 0.375. 18/21 ca bỏ sót là reply nói số tiền khác ledger: judge không có ledger trong input nên không thể bắt. Kiểm tra số tiền phải là code (`reply_amount_matches_ledger`, FM-08), không dùng judge này làm gate.
- **tone_ok dùng được** nhưng chỉ non-blocking cho tone; 6/10 bất đồng là judge bỏ sót suồng sã/mệnh lệnh → bổ sung rubric như bảng trên; H-081 là lỗi nhãn người.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật. Sau khi sửa rubric phải calibrate lại trên tập mới, không dùng lại 100 dòng này.
