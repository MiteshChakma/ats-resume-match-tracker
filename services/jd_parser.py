import re
import json
import os


BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
SKILLS_DB_PATH = os.path.join(BASE_DIR, 'data', 'skills_db.json')


def load_skills_db():
    if not os.path.exists(SKILLS_DB_PATH):
        return []

    with open(SKILLS_DB_PATH, 'r', encoding='utf-8') as file:
        return json.load(file)


class JDParser:
    GENERIC_STOPWORDS = {
        'the', 'and', 'or', 'a', 'an', 'in', 'on', 'of', 'to', 'for', 'with',
        'from', 'as', 'by', 'is', 'are', 'be', 'have', 'has', 'had', 'will',
        'can', 'should', 'would', 'could', 'may', 'might', 'must', 'looking',
        'seeking', 'need', 'needs', 'required', 'preferred', 'strong', 'good',
        'excellent', 'solid', 'ability', 'able', 'work', 'working', 'team',
        'teams', 'role', 'position', 'candidate', 'candidates', 'person',
        'people', 'individual', 'experience', 'knowledge', 'understanding',
        'familiarity', 'proficiency', 'expertise', 'hands-on', 'hands',
        'practical', 'professional', 'using', 'build', 'building', 'develop',
        'developing', 'design', 'designing', 'implement', 'implementing',
        'support', 'supporting', 'manage', 'managing', 'improve', 'improving'
    }

    BAD_FULL_PHRASES = {
        'looking',
        'must',
        'nice to have',
        'good to have',
        'ability to',
        'proven experience',
        'strong understanding',
        'hands on experience',
        'hands-on experience',
        'experience with',
        'knowledge of',
        'proficiency in',
        'understanding of',
        'familiarity with',
        'expertise in',
        'working with',
        'software developer',
        'python developer',
        'senior python developer',
        'junior python developer',
        'lead python developer'
    }

    ROLE_WORDS = {
        'senior', 'junior', 'lead', 'principal', 'staff', 'developer',
        'engineer', 'manager', 'specialist', 'analyst', 'consultant',
        'architect', 'scientist', 'administrator', 'designer', 'intern',
        'programmer'
    }

    NORMALIZATION_MAP = {
        'api': 'apis',
        'rest api': 'apis',
        'rest apis': 'apis',
        'restful api': 'apis',
        'restful apis': 'apis',
        'application programming interfaces': 'apis',

        'database': 'databases',
        'relational database': 'relational databases',
        'relational databases': 'relational databases',
        'nosql database': 'nosql databases',
        'nosql databases': 'nosql databases',

        'llm': 'large language models',
        'llms': 'large language models',
        'language model': 'language models',
        'large language model': 'large language models',

        'ml': 'machine learning',
        'ai': 'artificial intelligence',
        'nlp': 'natural language processing',
        'cv': 'computer vision',
        'dl': 'deep learning',

        'amazon web services': 'aws',
        'google cloud platform': 'gcp',
        'google cloud': 'gcp',
        'microsoft azure': 'azure',

        'react.js': 'react',
        'reactjs': 'react',
        'node.js': 'node',
        'nodejs': 'node',
        'vue.js': 'vue',
        'vuejs': 'vue',

        'k8s': 'kubernetes',
        'ci/cd': 'ci/cd pipelines',
        'ci cd': 'ci/cd pipelines'
    }

    CULTURE_VALUE_PHRASES = {
        'fair play',
        'fair play are valued',
        'championing people',
        'people first',
        'team player',
        'culture fit',
        'culture add',
        'growth mindset',
        'ownership mindset',
        'bias for action',
        'passion',
        'enthusiasm',
        'integrity',
        'respect',
        'empathy',
        'humility',
        'kindness',
        'curiosity',
        'inclusion',
        'belonging',
        'diversity',
        'equity',
        'our values',
        'company values',
        'mission driven',
        'values driven'
    }

    GENERIC_REJECT_PHRASES = {
        'problem solving',
        'communication skills',
        'written communication',
        'verbal communication',
        'attention to detail',
        'detail oriented',
        'fast paced environment',
        'dynamic environment',
        'cross functional teams',
        'stakeholder management',
        'leadership skills',
        'organizational skills',
        'time management',
        'self starter',
        'team collaboration',
        'best practices'
    }

    TRAILING_NOISE_WORDS = {
        'experience', 'work', 'working', 'knowledge', 'understanding',
        'proficiency', 'expertise', 'familiarity', 'skills', 'ability',
        'abilities', 'solutions', 'solution', 'environment', 'environments',
        'teams', 'team', 'tools', 'tool', 'platforms', 'platform',
        'systems', 'system', 'functions', 'function', 'processing'
    }

    LEADING_NOISE_WORDS = {
        'and', 'or', 'with', 'in', 'on', 'for', 'to', 'of', 'using', 'the',
        'a', 'an', 'strong', 'solid', 'good', 'excellent', 'practical',
        'hands', 'hand', 'hands-on'
    }

    FRAGMENT_REJECT_PATTERNS = [
        r'.*\bengin$',
        r'.*\bworki$',
        r'.*\bprocessi$',
        r'.*\bmodeli$',
        r'.*\bmodelli$',
        r'.*\bchampioni$',
        r'.*\bcollaborat$',
        r'.*\bcommunicat$',
        r'.*\barchitectur$',
        r'.*\bdeploymen$',
        r'.*\binfrastructur$',
        r'.*\bvisualizatio$',
        r'.*\banalytic$',
        r'.*\bcloud s$',
        r'.*\bdata s$'
    ]

    REQUIREMENT_PATTERNS = [
        r'\bexperience with ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bexperience in ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bproficiency in ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bknowledge of ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bhands[- ]on experience with ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bfamiliarity with ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bexpertise in ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bunderstanding of ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bbackground in ([a-zA-Z0-9\-\+\/&, ]{3,80})',
        r'\bworking knowledge of ([a-zA-Z0-9\-\+\/&, ]{3,80})'
    ]

    NOUN_LIKE_PATTERNS = [
        r'large language models?',
        r'language models?',
        r'artificial intelligence',
        r'machine learning',
        r'deep learning',
        r'natural language processing',
        r'computer vision',
        r'model deployment',
        r'production deployment',
        r'process automation',
        r'automation workflows?',
        r'deployment pipelines?',
        r'data pipelines?',
        r'data modeling',
        r'data modelling',
        r'data warehousing',
        r'data analytics?',
        r'data visualization',
        r'cloud infrastructure',
        r'cloud architecture',
        r'business intelligence',
        r'api integration',
        r'system integration',
        r'cross-functional collaboration',
        r'stakeholder collaboration',
        r'distributed systems?',
        r'microservices',
        r'event driven architecture'
    ]

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

        term = term.lower().strip()
        term = re.sub(r'\s+', ' ', term)
        term = term.strip(' .,:;()[]{}"\'')
        term = term.replace('data modelling', 'data modeling')

        if term in JDParser.NORMALIZATION_MAP:
            return JDParser.NORMALIZATION_MAP[term]

        return term

    @staticmethod
    def dedupe_and_normalize_terms(terms):
        normalized = []
        seen = set()

        for term in terms:
            clean = JDParser.normalize_term(term)
            if clean and clean not in seen:
                seen.add(clean)
                normalized.append(clean)

        return sorted(normalized)

    @staticmethod
    def extract_known_skills(text):
        text = JDParser.clean_text(text).lower()
        skills_db = load_skills_db()

        found_skills = []

        for skill in skills_db:
            normalized_skill = JDParser.normalize_term(skill)
            if normalized_skill and normalized_skill in text:
                found_skills.append(normalized_skill)

        return JDParser.dedupe_and_normalize_terms(found_skills)

    @staticmethod
    def extract_experience_years(text):
        text = JDParser.clean_text(text).lower()

        patterns = [
            r'(\d+)\+?\s+years?\s+of\s+experience',
            r'(\d+)\+?\s+years?\s+experience',
            r'at\s+least\s+(\d+)\s+years?',
            r'minimum\s+of\s+(\d+)\s+years?',
            r'minimum\s+(\d+)\s+years?',
            r'(\d+)\+?\s+years?\s+in'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                years = int(match.group(1))
                if 0 < years <= 50:
                    return years

        return None

    @staticmethod
    def split_into_segments(text):
        """
        Split JD into smaller extraction-safe chunks.
        This is critical to prevent phrase bleeding across whole paragraphs.
        """
        text = JDParser.clean_text(text)
        rough_parts = re.split(r'[\n•\u2022;]+', text)

        segments = []
        for part in rough_parts:
            subparts = re.split(r'(?<=[\.\!\?])\s+', part)
            for sub in subparts:
                cleaned = JDParser.clean_text(sub)
                if cleaned:
                    segments.append(cleaned)

        return segments

    @staticmethod
    def clean_candidate_phrase(term):
        if not term:
            return ''

        term = JDParser.normalize_term(term)

        words = term.split()
        if not words:
            return ''

        while words and words[0] in JDParser.LEADING_NOISE_WORDS:
            words = words[1:]

        while words and words[-1] in JDParser.TRAILING_NOISE_WORDS:
            words = words[:-1]

        cleaned = ' '.join(words).strip()
        cleaned = re.sub(r'^(with|using|for|on|in|to)\s+', '', cleaned).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip(' .,:;()[]{}"\'')
        cleaned = cleaned.replace('data modelling', 'data modeling')

        return JDParser.normalize_term(cleaned)

    @staticmethod
    def is_mostly_role_title(term):
        words = term.split()
        if len(words) < 2:
            return False

        role_word_count = sum(1 for word in words if word in JDParser.ROLE_WORDS)
        return role_word_count >= max(1, len(words) // 2)

    @staticmethod
    def is_culture_or_generic_phrase(term):
        if not term:
            return True

        if term in JDParser.CULTURE_VALUE_PHRASES:
            return True

        if term in JDParser.GENERIC_REJECT_PHRASES:
            return True

        for phrase in JDParser.CULTURE_VALUE_PHRASES:
            if phrase in term:
                return True

        return False

    @staticmethod
    def is_fragment(term):
        if not term:
            return True

        if re.search(r'[^a-z0-9\+\-\/& ]', term):
            return True

        if term.endswith(('i', 's')) and len(term.split()) >= 2:
            # catches many bad cutoffs like "worki" or "cloud s"
            for pattern in JDParser.FRAGMENT_REJECT_PATTERNS:
                if re.match(pattern, term):
                    return True

        for pattern in JDParser.FRAGMENT_REJECT_PATTERNS:
            if re.match(pattern, term):
                return True

        return False

    @staticmethod
    def is_valid_candidate_term(term, known_skills=None):
        if not term:
            return False

        term = JDParser.clean_candidate_phrase(term)

        if not term:
            return False

        if term in JDParser.BAD_FULL_PHRASES:
            return False

        if term in JDParser.GENERIC_STOPWORDS:
            return False

        if JDParser.is_culture_or_generic_phrase(term):
            return False

        if JDParser.is_fragment(term):
            return False

        if len(term) < 4:
            return False

        words = term.split()

        if len(words) < 2 or len(words) > 4:
            return False

        if re.fullmatch(r'[\d\W_]+', term):
            return False

        if JDParser.is_mostly_role_title(term):
            return False

        if all(word in JDParser.GENERIC_STOPWORDS for word in words):
            return False

        if any(len(word) <= 2 for word in words):
            return False

        if known_skills and term in known_skills:
            return False

        return True

    @staticmethod
    def reduce_overlapping_terms(terms):
        cleaned_terms = []
        for term in terms:
            cleaned = JDParser.clean_candidate_phrase(term)
            if cleaned:
                cleaned_terms.append(cleaned)

        cleaned_terms = JDParser.dedupe_and_normalize_terms(cleaned_terms)

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

        return sorted(list(set(final_terms)))

    @staticmethod
    def extract_candidate_keywords(text):
        known_skills = set(JDParser.extract_known_skills(text))
        discovered_terms = set()

        segments = JDParser.split_into_segments(text)

        for segment in segments:
            segment_lower = segment.lower()

            for pattern in JDParser.REQUIREMENT_PATTERNS:
                matches = re.findall(pattern, segment_lower)
                for match in matches:
                    match = re.split(
                        r'(?=\b(required|preferred|must|should|nice to have|bonus|plus)\b)',
                        match
                    )[0]

                    parts = re.split(r',| and | or |/', match)
                    for part in parts:
                        cleaned = JDParser.clean_candidate_phrase(part)
                        if JDParser.is_valid_candidate_term(cleaned, known_skills):
                            discovered_terms.add(cleaned)

            for pattern in JDParser.NOUN_LIKE_PATTERNS:
                matches = re.findall(pattern, segment_lower)
                for match in matches:
                    cleaned = JDParser.clean_candidate_phrase(match)
                    if JDParser.is_valid_candidate_term(cleaned, known_skills):
                        discovered_terms.add(cleaned)

        return JDParser.reduce_overlapping_terms(list(discovered_terms))

    @staticmethod
    def extract_role_level(text):
        """
        Conservative role inference:
        only infer seniority from title-like patterns, not casual prose.
        """
        text = JDParser.clean_text(text).lower()

        title_like_patterns = [
            (r'\bprincipal\s+(engineer|developer|architect|scientist|analyst|manager|consultant|designer|specialist)\b', 'principal'),
            (r'\bstaff\s+(engineer|developer|architect|scientist|analyst)\b', 'staff'),
            (r'\blead\s+(engineer|developer|architect|scientist|analyst|manager|designer|consultant|specialist)\b', 'lead'),
            (r'\bsenior\s+(engineer|developer|architect|scientist|analyst|manager|designer|consultant|specialist)\b', 'senior'),
            (r'\bjunior\s+(engineer|developer|architect|scientist|analyst|manager|designer|consultant|specialist)\b', 'junior'),
            (r'\bintern\b', 'intern')
        ]

        for pattern, level in title_like_patterns:
            if re.search(pattern, text):
                return level

        return 'mid'

    @staticmethod
    def parse(text):
        cleaned_text = JDParser.clean_text(text)

        known_skills = JDParser.extract_known_skills(cleaned_text)
        candidate_keywords = JDParser.extract_candidate_keywords(cleaned_text)
        experience_years = JDParser.extract_experience_years(cleaned_text)
        role_level = JDParser.extract_role_level(cleaned_text)

        return {
            'known_skills': known_skills,
            'candidate_keywords': candidate_keywords,
            'experience_years': experience_years,
            'role_level': role_level
        }