import pdfplumber

with pdfplumber.open("data/Dataset_VoidHacks_compressed.pdf") as pdf:
    p = pdf.pages[0]
    line_chars = [c for c in p.chars if abs(c['top'] - 71.4) < 3.0 and c['x0'] >= 350.0]
    print("Stream order from x >= 350:")
    for idx, c in enumerate(line_chars):
        print(f"{idx:2d}: '{c['text']}' x0={c['x0']:.2f}, x1={c['x1']:.2f}")
