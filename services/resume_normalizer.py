import re


class ResumeNormalizer:
    SECTION_HEADERS = [
        "SUMMARY",
        "PROFILE",
        "PROFESSIONAL SUMMARY",
        "PERSONAL SUMMARY",
        "ABOUT ME",
        "SKILLS",
        "TECHNICAL SKILLS",
        "CORE SKILLS",
        "WORK EXPERIENCE",
        "WORK EXPERIENCES",
        "EXPERIENCE",
        "PROFESSIONAL EXPERIENCE",
        "EMPLOYMENT HISTORY",
        "EDUCATION",
        "PROJECTS",
        "CERTIFICATIONS",
        "LANGUAGES",
        "PUBLICATIONS",
        "VOLUNTEER",
        "AWARDS",
        "REFERENCES"
    ]

    INLINE_LABELS = [
        "Programming Language:",
        "Programming Languages:",
        "Version Control:",
        "Data Engineering:",
        "Development & Operation:",
        "Development & Operations:",
        "ML Tools:",
        "Database:",
        "Data Visualization:",
        "GenAI:",
        "Frameworks:",
        "Cloud:",
        "Tools:",
        "Languages:",
    ]

    MONTHS = (
        r'(January|February|March|April|May|June|July|August|September|October|November|December|'
        r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
    )

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ''

        text = ResumeNormalizer._basic_cleanup(text)
        text = ResumeNormalizer._force_section_breaks(text)
        text = ResumeNormalizer._split_inline_skill_labels(text)
        text = ResumeNormalizer._repair_broken_date_ranges(text)
        text = ResumeNormalizer._repair_hyphenated_line_breaks(text)
        text = ResumeNormalizer._clean_experience_block_spacing(text)
        text = ResumeNormalizer._collapse_excess_blank_lines(text)

        return text.strip()

    @staticmethod
    def _basic_cleanup(text: str) -> str:
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')

        # remove repeated spaces/tabs
        text = re.sub(r'[ \t]+', ' ', text)

        # trim trailing spaces on lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))

        return text.strip()

    @staticmethod
    def _force_section_breaks(text: str) -> str:
        for header in ResumeNormalizer.SECTION_HEADERS:
            pattern = rf'(?<!\n)({re.escape(header)})(?![^\n])'
            text = re.sub(pattern, r'\n\1', text, flags=re.IGNORECASE)

        return text

    @staticmethod
    def _split_inline_skill_labels(text: str) -> str:
        """
        If PDF extraction merged several label/value pairs into one line,
        split before known labels.
        """
        for label in ResumeNormalizer.INLINE_LABELS:
            escaped = re.escape(label)

            # insert newline before label if not already at line start
            text = re.sub(rf'(?<!\n)\s+({escaped})', r'\n\1', text, flags=re.IGNORECASE)

        return text

    @staticmethod
    def _repair_broken_date_ranges(text: str) -> str:
        """
        Fix cases like:
        January 2023 - AI Trainer ...
        July 2025

        into:
        January 2023 - July 2025
        AI Trainer ...
        """
        pattern = (
            rf'({ResumeNormalizer.MONTHS}\s+\d{{4}})\s*-\s*(.+?)\n'
            rf'({ResumeNormalizer.MONTHS}\s+\d{{4}})'
        )

        def repl(match):
            start_date = match.group(1)
            middle = match.group(2).strip()
            end_date = match.group(4)
            return f'{start_date} - {end_date}\n{middle}'

        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

        # Also fix numeric ranges split across lines
        pattern_numeric = r'(\d{1,2}/\d{4})\s*-\s*(.+?)\n(\d{1,2}/\d{4})'

        def repl_numeric(match):
            start_date = match.group(1)
            middle = match.group(2).strip()
            end_date = match.group(3)
            return f'{start_date} - {end_date}\n{middle}'

        text = re.sub(pattern_numeric, repl_numeric, text, flags=re.IGNORECASE)

        return text

    @staticmethod
    def _repair_hyphenated_line_breaks(text: str) -> str:
        """
        Fix words broken by PDF line wrap:
        large-
        scale -> large-scale
        """
        text = re.sub(r'(\w+)-\n(\w+)', r'\1-\2', text)
        return text

    @staticmethod
    def _clean_experience_block_spacing(text: str) -> str:
        """
        Improve readability in experience sections by separating obvious date lines,
        titles, and bullet-like content a bit more consistently.
        """
        lines = text.split('\n')
        cleaned = []

        date_line_pattern = re.compile(
            rf'^\s*({ResumeNormalizer.MONTHS}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})'
            rf'\s*-\s*'
            rf'({ResumeNormalizer.MONTHS}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}}|Present|Current|Now)\s*$',
            re.IGNORECASE
        )

        for i, line in enumerate(lines):
            stripped = line.strip()

            if not stripped:
                cleaned.append('')
                continue

            # ensure date lines stand on their own
            if date_line_pattern.match(stripped):
                if cleaned and cleaned[-1] != '':
                    cleaned.append('')
                cleaned.append(stripped)
                continue

            cleaned.append(stripped)

        return '\n'.join(cleaned)

    @staticmethod
    def _collapse_excess_blank_lines(text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text