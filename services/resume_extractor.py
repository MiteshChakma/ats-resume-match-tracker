import pdfplumber


class ResumeExtractor:
    @staticmethod
    def extract_text_from_pdf(file):
        """
        Extract text from PDF using pdfplumber.

        Tries layout-aware extraction first.
        Falls back to plain extraction if layout extraction is weak.
        """
        file.seek(0)

        layout_pages = []

        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text(
                        x_tolerance=2,
                        y_tolerance=3,
                        layout=True
                    )
                    if text:
                        layout_pages.append(text)

            layout_text = "\n".join(layout_pages).strip()

            if len(layout_text) > 500:
                return layout_text

        except Exception:
            pass

        file.seek(0)

        plain_pages = []

        try:
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text(
                        x_tolerance=2,
                        y_tolerance=3,
                        layout=False
                    )
                    if text:
                        plain_pages.append(text)

            return "\n".join(plain_pages).strip()

        except Exception as exc:
            raise Exception(f"PDF extraction failed: {str(exc)}")