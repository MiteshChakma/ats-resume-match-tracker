class ATSScorer:
    """
    ATS Scorer v2
    Compares parsed resume data against parsed JD data.
    """

    WEIGHTS = {
    'skills': 45,
    'experience': 20,
    'role_level': 15,
    'candidate_keywords': 20
    }

    ROLE_LEVEL_ORDER = {
        'intern': 1,
        'junior': 2,
        'mid': 3,
        'senior': 4,
        'lead': 5,
        'staff': 6,
        'principal': 7
    }

    @staticmethod
    def normalize_list(values):
        if not values:
            return []

        normalized = []
        seen = set()

        for value in values:
            if value is None:
                continue

            clean = str(value).strip().lower()
            if clean and clean not in seen:
                seen.add(clean)
                normalized.append(clean)

        return normalized

    @staticmethod
    def tokenize_title(title):
        if not title:
            return set()

        words = [word.strip().lower() for word in str(title).split() if word.strip()]
        return set(words)

    @staticmethod
    def calculate_skill_score(resume_skills, jd_skills):
        resume_skills = set(ATSScorer.normalize_list(resume_skills))
        jd_skills = set(ATSScorer.normalize_list(jd_skills))

        if not jd_skills:
            return {
                'score': 0,
                'matched': [],
                'missing': [],
                'resume_only': sorted(list(resume_skills)),
                'status': 'jd_skills_missing'
            }

        matched = sorted(list(resume_skills.intersection(jd_skills)))
        missing = sorted(list(jd_skills - resume_skills))
        resume_only = sorted(list(resume_skills - jd_skills))

        score = round((len(matched) / len(jd_skills)) * ATSScorer.WEIGHTS['skills'])

        return {
            'score': score,
            'matched': matched,
            'missing': missing,
            'resume_only': resume_only,
            'status': 'ok'
        }

    @staticmethod
    def calculate_candidate_keyword_score(resume_keywords, jd_keywords):
        resume_keywords = set(ATSScorer.normalize_list(resume_keywords))
        jd_keywords = set(ATSScorer.normalize_list(jd_keywords))

        if not jd_keywords:
            return {
                'score': 0,
                'matched': [],
                'missing': [],
                'resume_only': sorted(list(resume_keywords)),
                'status': 'jd_candidate_keywords_missing'
            }

        matched = sorted(list(resume_keywords.intersection(jd_keywords)))
        missing = sorted(list(jd_keywords - resume_keywords))
        resume_only = sorted(list(resume_keywords - jd_keywords))

        score = round((len(matched) / len(jd_keywords)) * ATSScorer.WEIGHTS['candidate_keywords'])

        return {
            'score': score,
            'matched': matched,
            'missing': missing,
            'resume_only': resume_only,
            'status': 'ok'
        }

    @staticmethod
    def calculate_experience_score(resume_years, jd_years):
        if jd_years is None:
            return {
                'score': ATSScorer.WEIGHTS['experience'],
                'gap': None,
                'status': 'not_required'
            }

        if resume_years is None:
            return {
                'score': 0,
                'gap': jd_years,
                'status': 'missing_resume_experience'
            }

        gap = resume_years - jd_years

        if resume_years >= jd_years:
            return {
                'score': ATSScorer.WEIGHTS['experience'],
                'gap': gap,
                'status': 'meets_or_exceeds'
            }

        ratio = resume_years / jd_years if jd_years > 0 else 0
        score = round(ratio * ATSScorer.WEIGHTS['experience'])

        return {
            'score': score,
            'gap': gap,
            'status': 'below_requirement'
        }

    @staticmethod
    def calculate_role_level_score(resume_role_level, jd_role_level):
        if not jd_role_level:
            return {
                'score': 0,
                'status': 'jd_role_not_found'
            }

        if not resume_role_level:
            return {
                'score': 0,
                'status': 'resume_role_not_found'
            }

        resume_rank = ATSScorer.ROLE_LEVEL_ORDER.get(str(resume_role_level).lower(), 3)
        jd_rank = ATSScorer.ROLE_LEVEL_ORDER.get(str(jd_role_level).lower(), 3)

        if resume_rank == jd_rank:
            return {
                'score': ATSScorer.WEIGHTS['role_level'],
                'status': 'exact_match'
            }

        if resume_rank > jd_rank:
            return {
                'score': ATSScorer.WEIGHTS['role_level'],
                'status': 'resume_above_jd'
            }

        if jd_rank - resume_rank == 1:
            return {
                'score': round(ATSScorer.WEIGHTS['role_level'] * 0.6),
                'status': 'slightly_below'
            }

        return {
            'score': 0,
            'status': 'significantly_below'
        }

    @staticmethod
    def calculate_title_score(resume_titles, jd_title):
        resume_titles = ATSScorer.normalize_list(resume_titles)

        if not jd_title:
            return {
                'score': 0,
                'status': 'jd_title_missing',
                'matched_titles': [],
                'best_overlap_ratio': 0
            }

        jd_title_clean = str(jd_title).strip().lower()

        if not resume_titles:
            return {
                'score': 0,
                'status': 'resume_titles_missing',
                'matched_titles': [],
                'best_overlap_ratio': 0
            }

        exact_matches = [title for title in resume_titles if title == jd_title_clean]
        if exact_matches:
            return {
                'score': ATSScorer.WEIGHTS['title'],
                'status': 'exact_match',
                'matched_titles': exact_matches,
                'best_overlap_ratio': 1.0
            }

        jd_tokens = ATSScorer.tokenize_title(jd_title_clean)

        best_overlap_ratio = 0
        best_titles = []

        for resume_title in resume_titles:
            resume_tokens = ATSScorer.tokenize_title(resume_title)
            if not resume_tokens or not jd_tokens:
                continue

            overlap = len(resume_tokens.intersection(jd_tokens))
            ratio = overlap / len(jd_tokens)

            if ratio > best_overlap_ratio:
                best_overlap_ratio = ratio
                best_titles = [resume_title]
            elif ratio == best_overlap_ratio and ratio > 0:
                best_titles.append(resume_title)

        if best_overlap_ratio >= 0.75:
            return {
                'score': ATSScorer.WEIGHTS['title'],
                'status': 'strong_partial_match',
                'matched_titles': best_titles,
                'best_overlap_ratio': round(best_overlap_ratio, 2)
            }

        if best_overlap_ratio >= 0.4:
            return {
                'score': round(ATSScorer.WEIGHTS['title'] * 0.5),
                'status': 'weak_partial_match',
                'matched_titles': best_titles,
                'best_overlap_ratio': round(best_overlap_ratio, 2)
            }

        return {
            'score': 0,
            'status': 'no_match',
            'matched_titles': [],
            'best_overlap_ratio': round(best_overlap_ratio, 2)
        }

    @staticmethod
    def score(resume_parsed, jd_parsed, jd_title=None):
        resume_parsed = resume_parsed or {}
        jd_parsed = jd_parsed or {}

        resume_skills = resume_parsed.get('known_skills', [])
        jd_skills = jd_parsed.get('known_skills', [])

        resume_keywords = resume_parsed.get('candidate_keywords', [])
        jd_keywords = jd_parsed.get('candidate_keywords', [])

        resume_years = resume_parsed.get('experience_years')
        jd_years = jd_parsed.get('experience_years')

        resume_role = resume_parsed.get('role_level')
        jd_role = jd_parsed.get('role_level')

        resume_titles = resume_parsed.get('job_titles', [])

        skill_result = ATSScorer.calculate_skill_score(resume_skills, jd_skills)
        keyword_result = ATSScorer.calculate_candidate_keyword_score(resume_keywords, jd_keywords)
        experience_result = ATSScorer.calculate_experience_score(resume_years, jd_years)
        role_result = ATSScorer.calculate_role_level_score(resume_role, jd_role)


        overall_score = (
            skill_result['score'] +
            keyword_result['score'] +
            experience_result['score'] +
            role_result['score'] 
        )

        overall_score = max(0, min(100, overall_score))

        return {
            'overall_score': overall_score,
            'breakdown': {
                'skills_score': skill_result['score'],
                'candidate_keyword_score': keyword_result['score'],
                'experience_score': experience_result['score'],
                'role_level_score': role_result['score'],

            },
            'matched_skills': skill_result['matched'],
            'missing_skills': skill_result['missing'],
            'resume_only_skills': skill_result['resume_only'],
            'skill_status': skill_result['status'],

            'matched_candidate_keywords': keyword_result['matched'],
            'missing_candidate_keywords': keyword_result['missing'],
            'resume_only_candidate_keywords': keyword_result['resume_only'],
            'candidate_keyword_status': keyword_result['status'],

            'experience_gap': experience_result['gap'],
            'experience_status': experience_result['status'],

            'role_level_status': role_result['status'],

            'resume_snapshot': {
                'known_skills': ATSScorer.normalize_list(resume_skills),
                'candidate_keywords': ATSScorer.normalize_list(resume_keywords),
                'experience_years': resume_years,
                'role_level': resume_role,
                'job_titles': ATSScorer.normalize_list(resume_titles)
            },
            'jd_snapshot': {
                'known_skills': ATSScorer.normalize_list(jd_skills),
                'candidate_keywords': ATSScorer.normalize_list(jd_keywords),
                'experience_years': jd_years,
                'role_level': jd_role,
                'job_title': jd_title
            }
        }

    @staticmethod
    def calculate_score(resume_text=None, job_description=None):
        """
        Backward-compatible shim.
        Keep this only if some older route or test still expects calculate_score().
        For the real app flow, prefer score(resume_parsed, jd_parsed, jd_title).
        """
        return {
            'overall_score': 0,
            'breakdown': {
                'skills_score': 0,
                'candidate_keyword_score': 0,
                'experience_score': 0,
                'role_level_score': 0,
                'title_score': 0
            },
            'matched_skills': [],
            'missing_skills': [],
            'matched_candidate_keywords': [],
            'missing_candidate_keywords': [],
            'experience_gap': None,
            'experience_status': 'deprecated_method',
            'role_level_status': 'deprecated_method',
            'title_alignment_status': 'deprecated_method',
            'matched_titles': []
        }