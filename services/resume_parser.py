import re
import json
import os
from datetime import datetime


BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
SKILLS_DB_PATH = os.path.join(BASE_DIR, 'data', 'skills_db.json')


def load_skills_db():
    if not os.path.exists(SKILLS_DB_PATH):
        return []

    with open(SKILLS_DB_PATH, 'r', encoding='utf-8') as file:
        return json.load(file)


class ResumeParser:
    SECTION_HEADERS = {
        "summary": frozenset([
            "summary",
            "profile",
            "professional summary",
            "personal summary",
            "about me",
            "about",
            "career summary",
            "career objective",
            "objective",
            "professional profile",
            "executive summary",
            "overview",
        ]),
        "skills": frozenset([
            "skills",
            "technical skills",
            "core skills",
            "key skills",
            "competencies",
            "core competencies",
            "technologies",
            "tech stack",
            "tools & technologies",
            "tools and technologies",
            "tools",
            "expertise",
            "areas of expertise",
            "technical expertise",
            "technical competencies",
            "programming languages",
            "languages & frameworks",
            "languages and frameworks",
        ]),
        "experience": frozenset([
            "experience",
            "work experience",
            "professional experience",
            "employment history",
            "employment",
            "work history",
            "career history",
            "relevant experience",
            "industry experience",
            "positions held",
            "professional background",
            "work experiences",
        ]),
        "education": frozenset([
            "education",
            "academic background",
            "academic history",
            "qualifications",
            "educational background",
            "degrees",
            "academic qualifications",
            "training & education",
            "training and education",
        ]),
        "projects": frozenset([
            "projects",
            "project experience",
            "personal projects",
            "side projects",
            "open source",
            "open-source contributions",
            "portfolio",
            "notable projects",
            "selected projects",
        ]),
        "certifications": frozenset([
            "certifications",
            "certificates",
            "licenses",
            "licences",
            "accreditations",
            "professional certifications",
            "credentials",
            "awards & certifications",
            "awards and certifications",
        ]),
        "publications": frozenset([
            "publications",
            "papers",
            "research",
            "research & publications",
            "research and publications",
            "articles",
        ]),
        "languages": frozenset([
            "languages",
            "language skills",
            "spoken languages",
        ]),
        "volunteer": frozenset([
            "volunteer",
            "volunteering",
            "volunteer experience",
            "community involvement",
            "community service",
        ]),
        "awards": frozenset([
            "awards",
            "honours",
            "honors",
            "achievements",
            "recognition",
        ]),
        "references": frozenset([
            "references",
            "referees",
            "references available on request",
            "references available upon request",
        ])
    }

    ROLE_WORDS = {
        'senior', 'junior', 'lead', 'principal', 'staff', 'developer',
        'engineer', 'manager', 'specialist', 'analyst', 'consultant',
        'architect', 'scientist', 'administrator', 'designer', 'intern',
        'trainer', 'programmer', 'director', 'officer', 'coordinator'
    }

    TITLE_KEYWORDS = {
        'engineer', 'developer', 'analyst', 'scientist', 'manager',
        'architect', 'consultant', 'designer', 'administrator',
        'specialist', 'trainer', 'programmer', 'director', 'officer',
        'coordinator', 'associate', 'lead', 'principal', 'head'
    }

    COMPANY_HINT_WORDS = {
        'inc', 'llc', 'ltd', 'limited', 'corp', 'corporation', 'company',
        'technologies', 'technology', 'solutions', 'systems', 'group',
        'labs', 'lab', 'consulting', 'consultants', 'services', 'software',
        'bank', 'university', 'college', 'agency', 'studio', 'partners'
    }

    BULLET_PREFIXES = ('-', '•', '*', '●', '▪', '◦')

    NORMALIZATION_MAP = {
        # APIs
        "application programming interfaces": "apis",
        "rest api": "apis",
        "rest apis": "apis",
        "restful api": "apis",
        "restful apis": "apis",
        "api": "apis",

        # AI / ML
        "large language model": "large language models",
        "large language models": "large language models",
        "llm": "large language models",
        "llms": "large language models",
        "language model": "language models",
        "language models": "language models",
        "ml": "machine learning",
        "ai": "artificial intelligence",
        "dl": "deep learning",
        "nlp": "natural language processing",
        "cv": "computer vision",
        "rl": "reinforcement learning",
        "genai": "generative ai",
        "gen ai": "generative ai",
        "generative ai": "generative ai",

        # Cloud
        "amazon web services": "aws",
        "google cloud platform": "gcp",
        "google cloud": "gcp",
        "microsoft azure": "azure",
        "azure cloud": "azure",

        # Databases
        "database": "databases",
        "relational database": "relational databases",
        "relational databases": "relational databases",
        "rdbms": "relational databases",
        "nosql database": "nosql databases",
        "nosql databases": "nosql databases",
        "postgres": "postgresql",
        "postgresql database": "postgresql",

        # Containers / DevOps
        "k8s": "kubernetes",
        "k 8 s": "kubernetes",
        "docker container": "docker",
        "docker containers": "docker",

        # Frameworks
        "react.js": "react",
        "reactjs": "react",
        "react js": "react",
        "node.js": "node",
        "nodejs": "node",
        "node js": "node",
        "nextjs": "next.js",
        "vue.js": "vue",
        "vuejs": "vue",
        "tensorflow 2": "tensorflow",
        "tf": "tensorflow",

        # Misc
        "ci/cd": "ci/cd pipelines",
        "ci cd": "ci/cd pipelines",
        "oop": "object-oriented programming",
        "object oriented programming": "object-oriented programming",
        "tdd": "test-driven development",
        "bdd": "behaviour-driven development",
        "ddd": "domain-driven design",
        "agile methodology": "agile",
        "scrum methodology": "scrum",
    }

    GENERIC_STOPWORDS = {
        'the', 'and', 'or', 'a', 'an', 'in', 'on', 'of', 'to', 'for', 'with',
        'from', 'as', 'by', 'is', 'are', 'be', 'have', 'has', 'had', 'will',
        'can', 'should', 'would', 'could', 'may', 'might', 'must', 'worked',
        'work', 'working', 'responsible', 'responsibilities', 'helped',
        'managed', 'supported', 'built', 'developed', 'designed', 'created',
        'used', 'using', 'team', 'teams', 'project', 'projects', 'company',
        'clients', 'business', 'role', 'roles', 'experience', 'experiences',
        'including', 'across', 'various', 'multiple', 'different', 'within',
        'focusing', 'supporting', 'internal', 'structured', 'reliable'
    }

    LEADING_VERBS = {
        'built', 'developed', 'designed', 'implemented', 'created', 'managed',
        'used', 'worked', 'working', 'led', 'supported', 'improved', 'delivered',
        'optimized', 'analysed', 'analyzed', 'focusing', 'supporting'
    }

    TRAILING_NOISE_WORDS = {
        'solutions', 'solution', 'improvements', 'improvement', 'initiatives',
        'initiative', 'activities', 'activity', 'tasks', 'task', 'processes',
        'process', 'systems', 'system'
    }

    MONTH_MAP = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }

    @staticmethod
    def clean_text(text):
        if not text:
            return ''

        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @staticmethod
    def normalize_term(term):
        if not term:
            return ''

        term = ResumeParser.clean_text(term).lower().strip(' .,:;()[]{}"\'')
        term = re.sub(r'\s+', ' ', term)

        if term in ResumeParser.NORMALIZATION_MAP:
            return ResumeParser.NORMALIZATION_MAP[term]

        return term

    @staticmethod
    def dedupe_and_normalize_terms(terms):
        seen = set()
        result = []

        for term in terms:
            normalized = ResumeParser.normalize_term(term)
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)

        return sorted(result)

    @staticmethod
    def extract_known_skills(text):
        cleaned = ResumeParser.clean_text(text).lower()
        skills_db = load_skills_db()

        found = []
        for skill in skills_db:
            normalized_skill = ResumeParser.normalize_term(skill)
            if normalized_skill and normalized_skill in cleaned:
                found.append(normalized_skill)

        return ResumeParser.dedupe_and_normalize_terms(found)

    @staticmethod
    def split_sections(text):
        text = ResumeParser.clean_text(text)
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        sections = {}
        current_section = 'other'
        buffer = []

        def flush_buffer():
            if buffer:
                joined = '\n'.join(buffer).strip()
                if joined:
                    sections[current_section] = (
                        sections.get(current_section, '') + '\n' + joined
                    ).strip()

        for line in lines:
            matched_section = None
            lower_line = line.lower().strip(':').strip()

            for section_name, headers in ResumeParser.SECTION_HEADERS.items():
                if lower_line in headers:
                    matched_section = section_name
                    break

            if matched_section:
                flush_buffer()
                buffer = []
                current_section = matched_section
            else:
                buffer.append(line)

        flush_buffer()
        return sections

    @staticmethod
    def normalize_line_for_title(line):
        line = ResumeParser.clean_text(line)
        line = line.strip(' -|,')
        line = re.sub(r'\s+', ' ', line)
        return line.strip()

    @staticmethod
    def is_date_range_line(line):
        if not line:
            return False

        line = line.strip()

        patterns = [
            r'^[A-Za-z]{3,9}\s+\d{4}\s*(?:-|–|to)\s*(?:[A-Za-z]{3,9}\s+\d{4}|Present|Current|Now)$',
            r'^\d{1,2}/\d{4}\s*(?:-|–|to)\s*(?:\d{1,2}/\d{4}|Present|Current|Now)$',
            r'^\d{4}\s*(?:-|–|to)\s*(?:\d{4}|Present|Current|Now)$'
        ]

        return any(re.match(pattern, line, flags=re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def line_looks_like_bullet(line):
        stripped = line.strip()
        return bool(stripped) and stripped.startswith(ResumeParser.BULLET_PREFIXES)

    @staticmethod
    def line_looks_like_company(line):
        lower = line.lower().strip()
        if not lower:
            return False

        if any(hint in lower for hint in ResumeParser.COMPANY_HINT_WORDS):
            return True

        if re.search(r'\b(at|for)\s+[a-z0-9&.,\- ]+$', lower):
            return True

        return False

    @staticmethod
    def line_looks_like_title(line):
        if not line:
            return False

        raw = ResumeParser.normalize_line_for_title(line)
        lower = raw.lower()

        if not raw:
            return False

        if ResumeParser.is_date_range_line(raw):
            return False

        if ResumeParser.line_looks_like_bullet(raw):
            return False

        if len(raw) > 80:
            return False

        if len(raw.split()) < 1 or len(raw.split()) > 8:
            return False

        if re.search(r'[@/\\]', raw):
            return False

        if re.search(r'^\d+$', raw):
            return False

        if re.search(r'\b(university|college|school|bachelor|master|phd)\b', lower):
            return False

        if ResumeParser.line_looks_like_company(raw):
            return False

        if any(keyword in lower.split() for keyword in ResumeParser.TITLE_KEYWORDS):
            return True

        patterns = [
            r'^(senior|junior|lead|principal|staff)\s+.+$',
            r'^head\s+of\s+.+$',
            r'^director\s+of\s+.+$',
            r'^vp\s+.+$',
            r'^vice president\s+.+$'
        ]

        return any(re.match(pattern, lower) for pattern in patterns)

    @staticmethod
    def extract_role_level(text, sections=None):
        """
        Conservative role-level inference.
        Prefer summary and extracted titles.
        Avoid inferring lead from verbs like 'led'.
        """
        extracted_titles = ResumeParser.extract_job_titles(text, sections)
        combined_titles = ' '.join(extracted_titles).lower()

        title_patterns = [
            (r'\bprincipal\b', 'principal'),
            (r'\bstaff\b', 'staff'),
            (r'\blead\b', 'lead'),
            (r'\bsenior\b', 'senior'),
            (r'\bjunior\b', 'junior'),
            (r'\bintern\b', 'intern')
        ]

        for pattern, level in title_patterns:
            if re.search(pattern, combined_titles):
                return level

        search_areas = []

        if sections and sections.get('summary'):
            search_areas.append(sections['summary'][:400])

        if sections and sections.get('experience'):
            search_areas.append(sections['experience'][:400])

        search_areas.append(text[:300])

        combined = ' '.join(search_areas).lower()

        fallback_patterns = [
            (r'\bprincipal\s+(engineer|developer|analyst|scientist|architect|consultant|specialist|trainer|manager)\b', 'principal'),
            (r'\bstaff\s+(engineer|developer|analyst|scientist|architect|consultant|specialist|trainer|manager)\b', 'staff'),
            (r'\blead\s+(engineer|developer|analyst|scientist|architect|consultant|specialist|trainer|manager)\b', 'lead'),
            (r'\bsenior\s+(engineer|developer|analyst|scientist|architect|consultant|specialist|trainer|manager)\b', 'senior'),
            (r'\bjunior\s+(engineer|developer|analyst|scientist|architect|consultant|specialist|trainer|manager)\b', 'junior'),
            (r'\bintern\b', 'intern')
        ]

        for pattern, level in fallback_patterns:
            if re.search(pattern, combined):
                return level

        return 'mid'

    @staticmethod
    def extract_job_titles(text, sections=None):
        """
        Extract likely job titles from line-based resume structure instead of a fixed whitelist.
        Strongest source is the experience section.
        """
        source_text = sections.get('experience') if sections and sections.get('experience') else text
        source_text = ResumeParser.clean_text(source_text)

        lines = [ResumeParser.normalize_line_for_title(line) for line in source_text.split('\n') if line.strip()]

        found_titles = []
        seen = set()

        for i, line in enumerate(lines):
            if not ResumeParser.line_looks_like_title(line):
                continue

            lower = line.lower().strip()

            # ignore common section/header leakage
            if lower in ResumeParser.SECTION_HEADERS:
                continue

            # stronger if followed or preceded by a date range nearby
            nearby_has_date = False
            for offset in (-2, -1, 1, 2):
                j = i + offset
                if 0 <= j < len(lines) and ResumeParser.is_date_range_line(lines[j]):
                    nearby_has_date = True
                    break

            # allow strong title lines even without nearby dates if they clearly look like titles
            if nearby_has_date or any(word in lower.split() for word in ResumeParser.TITLE_KEYWORDS):
                if lower not in seen:
                    seen.add(lower)
                    found_titles.append(lower)

        return sorted(found_titles)

    @staticmethod
    def is_mostly_role_title(term):
        words = term.split()
        if len(words) < 2:
            return False

        role_count = sum(1 for word in words if word in ResumeParser.ROLE_WORDS)
        return role_count >= max(1, len(words) // 2)

    @staticmethod
    def clean_candidate_phrase(term):
        if not term:
            return ''

        term = ResumeParser.normalize_term(term)
        words = term.split()

        if not words:
            return ''

        while words and words[0] in ResumeParser.LEADING_VERBS:
            words = words[1:]

        while words and words[-1] in ResumeParser.TRAILING_NOISE_WORDS:
            words = words[:-1]

        cleaned = ' '.join(words).strip()
        cleaned = re.sub(r'^(with|using|for|on|in)\s+', '', cleaned).strip()

        return ResumeParser.normalize_term(cleaned)

    @staticmethod
    def is_valid_candidate_term(term, known_skills=None):
        if not term:
            return False

        term = ResumeParser.clean_candidate_phrase(term)

        if not term:
            return False

        if len(term) < 4:
            return False

        words = term.split()

        if len(words) < 2 or len(words) > 4:
            return False

        if term in ResumeParser.GENERIC_STOPWORDS:
            return False

        if re.fullmatch(r'[\d\W_]+', term):
            return False

        if ResumeParser.is_mostly_role_title(term):
            return False

        if known_skills and term in known_skills:
            return False

        bad_fragment_patterns = [
            r'.*\bqual$',
            r'.*\bworki$',
            r'.*\bengin$',
            r'.*\bsuppor$',
            r'.*\bprocessi$',
            r'.*\bmodeli$',
        ]

        for pattern in bad_fragment_patterns:
            if re.match(pattern, term):
                return False

        if any(len(word) <= 2 for word in words):
            return False

        return True

    @staticmethod
    def reduce_overlapping_terms(terms):
        cleaned_terms = []
        for term in terms:
            cleaned = ResumeParser.clean_candidate_phrase(term)
            if cleaned:
                cleaned_terms.append(cleaned)

        cleaned_terms = ResumeParser.dedupe_and_normalize_terms(cleaned_terms)

        final_terms = []
        for term in cleaned_terms:
            should_skip = False

            for existing in list(final_terms):
                if term == existing:
                    should_skip = True
                    break

                if term in existing:
                    should_skip = True
                    break

                if existing in term:
                    if len(existing.split()) <= len(term.split()):
                        should_skip = True
                        break

            if not should_skip:
                final_terms.append(term)

        final_terms = sorted(final_terms, key=lambda x: (len(x.split()), len(x)))

        compact = []
        for term in final_terms:
            if not any(term != other and term in other for other in compact):
                compact.append(term)

        return sorted(list(set(compact)))

    @staticmethod
    def split_into_segments(text):
        text = ResumeParser.clean_text(text)
        rough_parts = re.split(r'[\n•\u2022;]+', text)

        segments = []
        for part in rough_parts:
            subparts = re.split(r'(?<=[\.\!\?])\s+', part)
            for sub in subparts:
                cleaned = ResumeParser.clean_text(sub)
                if cleaned:
                    segments.append(cleaned)

        return segments

    @staticmethod
    def extract_candidate_keywords(text):
        text = ResumeParser.clean_text(text)
        known_skills = set(ResumeParser.extract_known_skills(text))
        discovered = set()

        segments = ResumeParser.split_into_segments(text)

        phrase_patterns = [
            r'experience with ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'worked with ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'used ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'built ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'developed ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'designed ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'implemented ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'managed ([a-zA-Z0-9\-\+\/\s,]{3,80})',
            r'created ([a-zA-Z0-9\-\+\/\s,]{3,80})'
        ]

        for segment in segments:
            segment_lower = segment.lower()

            for pattern in phrase_patterns:
                matches = re.findall(pattern, segment_lower)
                for match in matches:
                    parts = re.split(r',| and | or ', match)
                    for part in parts:
                        candidate = ResumeParser.clean_candidate_phrase(part)
                        if ResumeParser.is_valid_candidate_term(candidate, known_skills):
                            discovered.add(candidate)

        noun_like_patterns = [
            r'large language models?',
            r'language models?',
            r'automation workflows?',
            r'production deployment',
            r'deployment pipelines?',
            r'cross-functional collaboration',
            r'stakeholder collaboration',
            r'data pipelines?',
            r'cloud infrastructure',
            r'cloud infrastructure improvements?',
            r'process automation',
            r'model deployment',
            r'business intelligence',
            r'data visualization',
            r'data analysis',
            r'system integration',
            r'api integration',
            r'performance optimization',
            r'reporting automation',
            r'dashboard development',
            r'dashboard development solutions?',
            r'internal applications',
            r'structured datasets',
            r'data quality'
        ]

        text_lower = text.lower()
        for pattern in noun_like_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                candidate = ResumeParser.clean_candidate_phrase(match)
                if ResumeParser.is_valid_candidate_term(candidate, known_skills):
                    discovered.add(candidate)

        return ResumeParser.reduce_overlapping_terms(list(discovered))

    @staticmethod
    def extract_claimed_experience_years(text):
        lower = ResumeParser.clean_text(text).lower()

        patterns = [
            r'\b(\d{1,2})\+?\s+years?\s+of\s+experience\b',
            r'\b(\d{1,2})\+?\s+years?\s+experience\b',
            r'\bover\s+(\d{1,2})\s+years?\b',
            r'\baround\s+(\d{1,2})\s+years?\b',
            r'\b(\d{1,2})\+?\s+years?\s+in\b'
        ]

        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                years = int(match.group(1))
                if 0 < years <= 50:
                    return years

        return None

    @staticmethod
    def parse_date_token(token):
        token = token.strip().lower()

        if token in {'present', 'current', 'now'}:
            return datetime.now()

        month_year_match = re.match(r'([a-zA-Z]{3,9})\s+(\d{4})', token)
        if month_year_match:
            month_text = month_year_match.group(1).lower()
            year = int(month_year_match.group(2))
            month = ResumeParser.MONTH_MAP.get(month_text)
            if month:
                return datetime(year, month, 1)

        numeric_month_year_match = re.match(r'(\d{1,2})/(\d{4})', token)
        if numeric_month_year_match:
            month = int(numeric_month_year_match.group(1))
            year = int(numeric_month_year_match.group(2))
            if 1 <= month <= 12:
                return datetime(year, month, 1)

        year_match = re.match(r'(\d{4})', token)
        if year_match:
            year = int(year_match.group(1))
            return datetime(year, 1, 1)

        return None

    @staticmethod
    def extract_date_ranges(text):
        text = ResumeParser.clean_text(text)

        patterns = [
            r'([A-Za-z]{3,9}\s+\d{4})\s*(?:-|–|to)\s*([A-Za-z]{3,9}\s+\d{4}|Present|Current|Now)',
            r'(\d{1,2}/\d{4})\s*(?:-|–|to)\s*(\d{1,2}/\d{4}|Present|Current|Now)',
            r'\b(\d{4})\s*(?:-|–|to)\s*(\d{4}|Present|Current|Now)\b'
        ]

        ranges = []

        for pattern in patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for start_raw, end_raw in matches:
                start_date = ResumeParser.parse_date_token(start_raw)
                end_date = ResumeParser.parse_date_token(end_raw)

                if not start_date or not end_date:
                    continue

                if end_date < start_date:
                    continue

                months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

                if months < 1 or months > 600:
                    continue

                ranges.append({
                    'start_raw': start_raw,
                    'end_raw': end_raw,
                    'months': months
                })

        unique_ranges = []
        seen = set()

        for item in ranges:
            key = (item['start_raw'].lower(), item['end_raw'].lower())
            if key not in seen:
                seen.add(key)
                unique_ranges.append(item)

        return unique_ranges

    @staticmethod
    def estimate_experience_years(text, sections=None):
        claimed = ResumeParser.extract_claimed_experience_years(text)
        if claimed is not None:
            return claimed

        base_text = text
        if sections and sections.get('experience'):
            base_text = sections['experience']

        date_ranges = ResumeParser.extract_date_ranges(base_text)

        if not date_ranges:
            return None

        total_months = sum(item['months'] for item in date_ranges)

        if total_months < 1 or total_months > 600:
            return None

        years = round(total_months / 12)

        if 0 < years <= 50:
            return years

        return None

    @staticmethod
    def extract_experience_blocks(text, sections=None):
        experience_text = sections.get('experience') if sections and sections.get('experience') else text
        experience_text = ResumeParser.clean_text(experience_text)

        raw_lines = [line.strip() for line in experience_text.split('\n') if line.strip()]
        if not raw_lines:
            return []

        blocks = []
        current_block = []

        for line in raw_lines:
            if ResumeParser.is_date_range_line(line) and current_block:
                current_block.append(line)
                blocks.append(current_block)
                current_block = []
                continue

            if ResumeParser.line_looks_like_title(line) and current_block:
                blocks.append(current_block)
                current_block = [line]
                continue

            current_block.append(line)

        if current_block:
            blocks.append(current_block)

        normalized_blocks = []
        for block in blocks:
            cleaned_block = [ResumeParser.normalize_line_for_title(line) for line in block if line.strip()]
            if cleaned_block:
                normalized_blocks.append(cleaned_block)

        return normalized_blocks

    @staticmethod
    def extract_experience_entries(text, sections=None):
        experience_text = sections.get('experience') if sections and sections.get('experience') else text
        date_ranges = ResumeParser.extract_date_ranges(experience_text)
        blocks = ResumeParser.extract_experience_blocks(text, sections)

        entries = []
        discovered_titles = []

        for block in blocks:
            title = None
            company = None
            date_line = None

            for line in block:
                if not title and ResumeParser.line_looks_like_title(line):
                    title = line.lower().strip()
                    discovered_titles.append(title)
                    continue

                if not company and ResumeParser.line_looks_like_company(line):
                    company = line.strip()
                    continue

                if not date_line and ResumeParser.is_date_range_line(line):
                    date_line = line.strip()

            if title or company or date_line:
                entries.append({
                    'job_title': title,
                    'company': company,
                    'date_range': date_line
                })

        return {
            'date_ranges': date_ranges,
            'job_titles': sorted(list(set(discovered_titles))),
            'entries': entries
        }

    @staticmethod
    def parse(text):
        cleaned_text = ResumeParser.clean_text(text)
        sections = ResumeParser.split_sections(cleaned_text)

        skills_source = cleaned_text
        if sections.get('skills'):
            skills_source += '\n' + sections['skills']

        known_skills = ResumeParser.extract_known_skills(skills_source)
        candidate_keywords = ResumeParser.extract_candidate_keywords(cleaned_text)
        job_titles = ResumeParser.extract_job_titles(cleaned_text, sections)
        role_level = ResumeParser.extract_role_level(cleaned_text, sections)
        experience_years = ResumeParser.estimate_experience_years(cleaned_text, sections)
        experience_entries = ResumeParser.extract_experience_entries(cleaned_text, sections)

        # keep top-level job_titles aligned with structured experience extraction
        if experience_entries.get('job_titles'):
            merged_titles = sorted(set(job_titles).union(set(experience_entries['job_titles'])))
        else:
            merged_titles = job_titles

        return {
            'sections': sections,
            'known_skills': known_skills,
            'candidate_keywords': candidate_keywords,
            'experience_years': experience_years,
            'role_level': role_level,
            'job_titles': merged_titles,
            'experience_entries': experience_entries
        }