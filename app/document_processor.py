import os
from pypdf import PdfReader


def extract_text_from_pdf(file_path):
    """Extracts raw text content from multi-page PDFs locally on CPU."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Target document not found at: {file_path}")

    reader = PdfReader(file_path)
    extracted_text = []

    # Iterate over pages and cleanly accumulate the raw string characters
    for page_idx, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            # Basic normalization: clean up chaotic line breaks common in messy PDFs
            cleaned_text = " ".join(page_text.split())
            extracted_text.append(cleaned_text)

    return "\n\n".join(extracted_text)
