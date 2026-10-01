import re
import pypdfium2 as pdfium

# Pattern matching:
# 1. Line starts with Transaction_ID (TXN[A-Za-z0-9]+)
# 2. Sender_Account: 12 chars (e.g. 4 letters + 8 digits or 12 digits)
# 3. Receiver_Account: 12 chars
# 4. Sender_IFSC: 11 chars (4 letters + '0' + 6 chars)
# 5. Receiver_IFSC: 11 chars
# 6. Amount: float/int
# 7. '########' (Timestamp)
# 8. Payment_Mode: (UPI|IMPS|NEFT|RTGS)
# 9. Narration
# 10. IP_Address at the end

LINE_RE = re.compile(
    r'^(TXN[A-Za-z0-9_]+)\s+'
    r'([A-Za-z0-9]{12})\s*'
    r'([A-Za-z0-9]{12})\s*'
    r'([A-Z]{4}0[A-Z0-9]{6})\s*'
    r'([A-Z]{4}0[A-Z0-9]{6})\s*'
    r'([0-9]+(?:\.[0-9]+)?)\s+'
    r'(#{4,16})\s+'
    r'(UPI|IMPS|NEFT|RTGS)\s+'
    r'(.+?)\s+'
    r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$'
)

pdf = pdfium.PdfDocument('data/Dataset_VoidHacks_compressed.pdf')

sample_pages = [0, 1, 10, 50, 100, 500, 1000, 2000, 3000]
total_lines = 0
matched_lines = 0
failed_lines = []

for p_no in sample_pages:
    text = pdf[p_no].get_textpage().get_text_range()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line_idx, line in enumerate(lines):
        if "Transaction_ID" in line or "Sender_Account" in line:
            continue
        total_lines += 1
        m = LINE_RE.match(line)
        if m:
            matched_lines += 1
        else:
            failed_lines.append((p_no + 1, line_idx + 1, line))

print(f"Total lines checked: {total_lines}")
print(f"Matched lines: {matched_lines} ({(matched_lines/total_lines)*100:.2f}%)")
print(f"Failed lines count: {len(failed_lines)}")

if failed_lines:
    print("\nSample failed lines:")
    for p, idx, l in failed_lines[:5]:
        print(f"  Page {p}, Line {idx}: '{l}'")
