import pdfplumber

with pdfplumber.open("data/Dataset_VoidHacks_compressed.pdf") as pdf:
    p = pdf.pages[0]
    # Let's inspect characters sorted by (top, x0)
    # Group characters into vertical bands (lines)
    chars = p.chars
    # Let's find characters on the header line and the first data row
    # Header line is near top
    header_chars = [c for c in chars if c['top'] < 60]
    print(f"Header chars count: {len(header_chars)}")
    
    # First data row
    # Let's see the tops
    tops = sorted(list(set(round(c['top'], 1) for c in chars)))
    print("Unique top coordinates (first 5 lines):", tops[:5])
    
    for t in tops[1:4]:
        line_chars = [c for c in chars if abs(c['top'] - t) < 3.0]
        # Sort by x0
        line_chars_sorted = sorted(line_chars, key=lambda c: c['x0'])
        print(f"\n--- Line around top={t} (char count: {len(line_chars)}) ---")
        
        # Print x positions
        clusters = []
        current_cluster = [line_chars_sorted[0]]
        for c in line_chars_sorted[1:]:
            if c['x0'] - current_cluster[-1]['x1'] > 3.0: # gap
                clusters.append(current_cluster)
                current_cluster = [c]
            else:
                current_cluster.append(c)
        clusters.append(current_cluster)
        
        for idx, cl in enumerate(clusters):
            word = "".join(c['text'] for c in cl)
            print(f"  Field {idx}: x=[{cl[0]['x0']:.1f}, {cl[-1]['x1']:.1f}] text='{word}'")
