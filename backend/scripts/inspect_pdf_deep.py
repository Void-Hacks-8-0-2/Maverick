import hashlib
import pdfplumber

pdf_path = "data/Dataset_VoidHacks_compressed.pdf"

# 1. SHA-256
h = hashlib.sha256()
with open(pdf_path, "rb") as f:
    while chunk := f.read(1024*1024):
        h.update(chunk)
sha256 = h.hexdigest()
print(f"PDF SHA-256: {sha256}")

# 2. pdfplumber inspection
with pdfplumber.open(pdf_path) as pdf:
    print(f"Total Pages: {len(pdf.pages)}")
    
    # Metadata
    print(f"Metadata: {pdf.metadata}")
    
    for page_idx in [0, 1, 10, 50, 100]:
        page = pdf.pages[page_idx]
        print(f"\n=== PAGE {page_idx + 1} ===")
        print(f"Dimensions: width={page.width}, height={page.height}, bbox={page.bbox}")
        
        tables = page.find_tables()
        print(f"find_tables count: {len(tables)}")
        
        # Check text lines
        lines = page.extract_text_lines()
        print(f"Text lines count: {len(lines)}")
        if lines:
            print("Header line text:", lines[0]['text'])
            print("First row line text:", lines[1]['text'] if len(lines) > 1 else 'N/A')
            print("Second row line text:", lines[2]['text'] if len(lines) > 2 else 'N/A')
            
        # Inspect words with x coordinates
        words = page.extract_words()
        print(f"Words count on page: {len(words)}")
        
        # Check max x coordinate of characters
        if page.chars:
            max_x1 = max(c['x1'] for c in page.chars)
            min_x0 = min(c['x0'] for c in page.chars)
            print(f"Character X bounds: min_x0={min_x0:.2f}, max_x1={max_x1:.2f} (page width={page.width:.2f})")
            
            # Print last 5 characters horizontally to see what is on the rightmost edge
            sorted_by_x = sorted(page.chars, key=lambda c: c['x1'], reverse=True)
            rightmost_words = "".join(c['text'] for c in sorted(sorted_by_x[:30], key=lambda c: (c['top'], c['x0'])))
            print(f"Rightmost text sample: {rightmost_words}")
