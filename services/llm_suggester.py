import json
import re
from datetime import datetime

import ollama


class LLMSuggester:
    MODEL_A_NAME = "qwen2.5:7b"
    MODEL_B_NAME = "mistral"

    RISKY_TERMS = [
        "azure",
        "cloud services",
        "api monitoring",
        "monitoring",
        "observability",
        "kubernetes",
        "terraform",
        "microservices",
        "fastapi",
        "gcp",
        "google cloud",
        "aws",
        "s3",
        "postgresql",
        "mongodb",
        "django",
        "docker"
    ]

    @staticmethod
    def fallback_summary(scoring_result):
        missing_skills = scoring_result.get("missing_skills", [])
        missing_keywords = scoring_result.get("missing_candidate_keywords", [])

        skill_text = ", ".join(missing_skills[:3]) if missing_skills else "core JD skills"
        keyword_text = ", ".join(missing_keywords[:3]) if missing_keywords else "JD-specific keywords"

        return (
            f"Your resume has ATS gaps around {skill_text}. "
            f"Focus on strengthening truthful evidence for these areas and aligning bullets with {keyword_text}."
        )

    @staticmethod
    def build_prompt_qwen(resume_text, job_description, resume_parsed, jd_parsed, scoring_result):
        payload = {
            "resume_text": resume_text,
            "job_description": job_description,
            "resume_parsed": resume_parsed,
            "jd_parsed": jd_parsed,
            "scoring_result": scoring_result,
            "task": "Generate detailed truthful ATS resume improvement suggestions with bullet rewrites.",
            "instructions": [
                "The summary field is mandatory and must always be filled.",
                "Write a concise 2-3 sentence summary explaining the biggest ATS gaps.",
                "Do not invent experience, tools, employers, metrics, platforms, or achievements.",
                "Only suggest adding skills or keywords if they are supported by the resume text.",
                "Do not add a technology, platform, tool, metric, or architecture detail to an improved bullet unless it is explicitly present in the original bullet or clearly present elsewhere in the resume text.",
                "If a JD keyword is relevant but not clearly supported by the original bullet, mention it in ats_keywords_to_add_if_truthful but do not insert it into improved.",
                "Improved bullets must preserve the factual scope of the original bullet.",
                "Do not add Azure unless Azure appears in the resume text.",
                "Do not add cloud services unless the resume text explicitly supports cloud work.",
                "Do not add API monitoring unless monitoring or observability appears in the resume text.",
                "priority_fixes must contain only short plain-text action items.",
                "Do not put JSON objects inside priority_fixes.",
                "bullet_improvement_suggestions is the only place where bullet rewrite objects are allowed.",
                "Identify exact resume sentences or bullets that need rewriting to better align with the JD.",
                "For every bullet suggestion, set needs_rewrite to true or false.",
                "If needs_rewrite is true, explain the specific ATS/JD alignment issue in rewrite_reason.",
                "jd_alignment_target must contain the exact JD requirement, responsibility, skill, or keyword the rewrite is targeting.",
                "ats_keywords_to_add_if_truthful must include only JD keywords that are supported by the resume.",
                "If needs_rewrite is false, keep improved identical to original and explain briefly why no rewrite is needed.",
                "Review the full resume text, not only the first experience section.",
                "Select rewrite candidates from multiple experience sections when available.",
                "Do not limit suggestions to the first role unless it is the only relevant role.",
                "Return valid JSON only. No markdown. No text outside JSON."
            ],
            "output_schema": {
                "summary": "string",
                "priority_fixes": ["string"],
                "missing_skills_to_address": ["string"],
                "missing_keywords_to_consider": ["string"],
                "bullet_improvement_suggestions": [
                    {
                        "original": "string",
                        "needs_rewrite": "boolean",
                        "rewrite_reason": "string",
                        "jd_alignment_target": "string",
                        "ats_keywords_to_add_if_truthful": ["string"],
                        "improved": "string"
                    }
                ],
                "honesty_warnings": ["string"]
            }
        }

        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def build_prompt_mistral(resume_text, job_description, resume_parsed, jd_parsed, scoring_result):
        payload = {
            "resume_text": resume_text,
            "job_description": job_description,
            "resume_parsed": resume_parsed,
            "jd_parsed": jd_parsed,
            "scoring_result": scoring_result,
            "task": "Generate concise high-level ATS improvement suggestions.",
            "instructions": [
                "Return JSON only.",
                "The summary field is mandatory.",
                "Write a concise 1-2 sentence summary.",
                "Do not invent experience, tools, employers, metrics, platforms, or achievements.",
                "Focus on high-level improvement priorities rather than detailed rewrites.",
                "priority_fixes must contain only short plain-text action items.",
                "missing_skills_to_address should list important missing skills from the scoring result.",
                "missing_keywords_to_consider should list important JD keywords from the scoring result.",
                "bullet_improvement_suggestions may be empty.",
                "If you provide bullet rewrites, provide at most 2.",
                "Only rewrite bullets using information already present in the resume.",
                "honesty_warnings must contain at least one warning about not adding unsupported claims.",
                "No markdown. No text outside JSON."
            ],
            "output_schema": {
                "summary": "string",
                "priority_fixes": ["string"],
                "missing_skills_to_address": ["string"],
                "missing_keywords_to_consider": ["string"],
                "bullet_improvement_suggestions": [
                    {
                        "original": "string",
                        "needs_rewrite": "boolean",
                        "rewrite_reason": "string",
                        "jd_alignment_target": "string",
                        "ats_keywords_to_add_if_truthful": ["string"],
                        "improved": "string"
                    }
                ],
                "honesty_warnings": ["string"]
            }
        }

        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def fallback_response(model_name, scoring_result):
        missing_skills = scoring_result.get("missing_skills", [])
        missing_keywords = scoring_result.get("missing_candidate_keywords", [])

        priority_fixes = []

        for skill in missing_skills[:3]:
            priority_fixes.append(
                f"Add or strengthen evidence for '{skill}' only if it is supported by your real experience."
            )

        for keyword in missing_keywords[:3]:
            priority_fixes.append(
                f"Use the phrase '{keyword}' naturally in a resume bullet only if it truthfully reflects your work."
            )

        return {
            "model_name": model_name,
            "summary": LLMSuggester.fallback_summary(scoring_result),
            "priority_fixes": priority_fixes[:5],
            "missing_skills_to_address": missing_skills[:8],
            "missing_keywords_to_consider": missing_keywords[:8],
            "bullet_improvement_suggestions": [],
            "honesty_warnings": [
                "Only add skills, tools, and claims that you can support with real experience, projects, or coursework."
            ]
        }

    @staticmethod
    def extract_json(content):
        if not content:
            return None

        content = content.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        matches = re.findall(r"\{.*\}", content, flags=re.DOTALL)

        for match in sorted(matches, key=len, reverse=True):
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None

    @staticmethod
    def normalize_string_list(values):
        if not isinstance(values, list):
            return []

        normalized = []
        seen = set()

        for value in values:
            if isinstance(value, dict):
                continue

            clean = str(value).strip()
            key = clean.lower()

            if clean and key not in seen:
                seen.add(key)
                normalized.append(clean)

        return normalized

    @staticmethod
    def normalize_boolean(value):
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in {
                "true",
                "yes",
                "1",
                "rewrite",
                "needs_rewrite"
            }

        return bool(value)

    @staticmethod
    def text_contains_term(text, term):
        if not text or not term:
            return False

        return term.lower() in text.lower()

    @staticmethod
    def find_unsupported_risky_terms(original, improved, resume_text):
        unsupported = []

        for term in LLMSuggester.RISKY_TERMS:
            appears_in_improved = LLMSuggester.text_contains_term(improved, term)
            appears_in_original = LLMSuggester.text_contains_term(original, term)
            appears_in_resume = LLMSuggester.text_contains_term(resume_text, term)

            if appears_in_improved and not appears_in_original and not appears_in_resume:
                unsupported.append(term)

        return unsupported

    @staticmethod
    def split_priority_fixes_and_bullets(priority_fixes, bullet_suggestions):
        clean_priority_fixes = []
        recovered_bullets = []

        if isinstance(priority_fixes, list):
            for item in priority_fixes:
                if isinstance(item, dict) and "original" in item and "improved" in item:
                    recovered_bullets.append(item)
                else:
                    clean = str(item).strip()
                    if clean:
                        clean_priority_fixes.append(clean)

        if isinstance(bullet_suggestions, list):
            for item in bullet_suggestions:
                if isinstance(item, dict):
                    recovered_bullets.append(item)

        return clean_priority_fixes, recovered_bullets

    @staticmethod
    def normalize_bullet_suggestions(items, resume_text=""):
        normalized = []

        if not isinstance(items, list):
            return normalized

        for item in items:
            if not isinstance(item, dict):
                continue

            original = str(item.get("original", "")).strip()
            improved = str(item.get("improved", original)).strip()

            if not original:
                continue

            needs_rewrite = LLMSuggester.normalize_boolean(
                item.get("needs_rewrite", False)
            )

            rewrite_reason = str(item.get("rewrite_reason", "")).strip()
            jd_alignment_target = str(item.get("jd_alignment_target", "")).strip()
            ats_keywords = LLMSuggester.normalize_string_list(
                item.get("ats_keywords_to_add_if_truthful", [])
            )

            unsupported_terms = LLMSuggester.find_unsupported_risky_terms(
                original=original,
                improved=improved,
                resume_text=resume_text
            )

            if unsupported_terms:
                improved = original
                needs_rewrite = False
                warning_text = (
                    "Rewrite rejected because it introduced unsupported terms: "
                    + ", ".join(unsupported_terms)
                    + "."
                )
                rewrite_reason = (rewrite_reason + " " + warning_text).strip()

            normalized.append({
                "original": original,
                "needs_rewrite": needs_rewrite,
                "rewrite_reason": rewrite_reason,
                "jd_alignment_target": jd_alignment_target,
                "ats_keywords_to_add_if_truthful": ats_keywords,
                "improved": improved or original
            })

        return normalized

    @staticmethod
    def build_honesty_warnings(existing_warnings, missing_skills, missing_keywords, resume_text):
        warnings = LLMSuggester.normalize_string_list(existing_warnings)

        unsupported_terms = []

        for term in list(missing_skills or []) + list(missing_keywords or []):
            if not LLMSuggester.text_contains_term(resume_text, term):
                unsupported_terms.append(term)

        if unsupported_terms:
            warnings.append(
                "Do not add these JD terms unless you can truthfully support them: "
                + ", ".join(unsupported_terms[:8])
                + "."
            )

        if not warnings:
            warnings.append(
                "Only add skills, tools, and claims that you can support with real experience, projects, or coursework."
            )

        return LLMSuggester.normalize_string_list(warnings)

    @staticmethod
    def normalize_model_output(model_name, parsed, scoring_result=None, resume_text=""):
        scoring_result = scoring_result or {}

        if not isinstance(parsed, dict):
            return LLMSuggester.fallback_response(model_name, scoring_result)

        clean_priority_fixes, recovered_bullets = LLMSuggester.split_priority_fixes_and_bullets(
            parsed.get("priority_fixes", []),
            parsed.get("bullet_improvement_suggestions", [])
        )

        summary = str(parsed.get("summary", "")).strip()
        if not summary:
            summary = LLMSuggester.fallback_summary(scoring_result)

        missing_skills = LLMSuggester.normalize_string_list(
            parsed.get("missing_skills_to_address", scoring_result.get("missing_skills", []))
        )

        missing_keywords = LLMSuggester.normalize_string_list(
            parsed.get("missing_keywords_to_consider", scoring_result.get("missing_candidate_keywords", []))
        )

        return {
            "model_name": model_name,
            "summary": summary,
            "priority_fixes": LLMSuggester.normalize_string_list(clean_priority_fixes),
            "missing_skills_to_address": missing_skills,
            "missing_keywords_to_consider": missing_keywords,
            "bullet_improvement_suggestions": LLMSuggester.normalize_bullet_suggestions(
                recovered_bullets,
                resume_text=resume_text
            ),
            "honesty_warnings": LLMSuggester.build_honesty_warnings(
                existing_warnings=parsed.get("honesty_warnings", []),
                missing_skills=missing_skills,
                missing_keywords=missing_keywords,
                resume_text=resume_text
            )
        }

    @staticmethod
    def call_qwen(prompt):
        response = ollama.chat(
            model=LLMSuggester.MODEL_A_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict JSON generator for resume rewrite analysis. "
                        "Return only one valid JSON object. "
                        "The summary field is mandatory. "
                        "No markdown. No comments. No explanations outside JSON. "
                        "Do not place bullet rewrite objects inside priority_fixes. "
                        "Use bullet_improvement_suggestions for rewrite objects only. "
                        "Do not invent technologies, tools, platforms, employers, metrics, or achievements."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.1
            }
        )

        return LLMSuggester.extract_json(response["message"]["content"])

    @staticmethod
    def call_mistral(prompt):
        response = ollama.chat(
            model=LLMSuggester.MODEL_B_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate concise ATS improvement JSON. "
                        "Return only valid JSON. "
                        "The summary field is mandatory. "
                        "No markdown. No comments. No extra text. "
                        "Bullet rewrites are optional. "
                        "Do not invent technologies, tools, platforms, employers, metrics, or achievements."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.0
            }
        )

        return LLMSuggester.extract_json(response["message"]["content"])

    @staticmethod
    def call_local_model_a(prompt):
        return LLMSuggester.call_qwen(prompt)

    @staticmethod
    def call_local_model_b(prompt):
        return LLMSuggester.call_mistral(prompt)

    @staticmethod
    def safe_model_call(model_name, caller, prompt, scoring_result, resume_text):
        try:
            parsed = caller(prompt)

            if not isinstance(parsed, dict):
                parsed = caller(prompt)

            if isinstance(parsed, dict):
                return LLMSuggester.normalize_model_output(
                    model_name=model_name,
                    parsed=parsed,
                    scoring_result=scoring_result,
                    resume_text=resume_text
                )

            return LLMSuggester.fallback_response(model_name, scoring_result)

        except Exception as exc:
            print(f"[LLMSuggester] {model_name} failed: {exc}")
            return LLMSuggester.fallback_response(model_name, scoring_result)

    @staticmethod
    def generate_dual(resume_text, job_description, resume_parsed, jd_parsed, scoring_result):
        qwen_prompt = LLMSuggester.build_prompt_qwen(
            resume_text=resume_text,
            job_description=job_description,
            resume_parsed=resume_parsed,
            jd_parsed=jd_parsed,
            scoring_result=scoring_result
        )

        mistral_prompt = LLMSuggester.build_prompt_mistral(
            resume_text=resume_text,
            job_description=job_description,
            resume_parsed=resume_parsed,
            jd_parsed=jd_parsed,
            scoring_result=scoring_result
        )

        model_a_result = LLMSuggester.safe_model_call(
            model_name=LLMSuggester.MODEL_A_NAME,
            caller=LLMSuggester.call_local_model_a,
            prompt=qwen_prompt,
            scoring_result=scoring_result,
            resume_text=resume_text
        )

        model_b_result = LLMSuggester.safe_model_call(
            model_name=LLMSuggester.MODEL_B_NAME,
            caller=LLMSuggester.call_local_model_b,
            prompt=mistral_prompt,
            scoring_result=scoring_result,
            resume_text=resume_text
        )

        return {
            "model_a": model_a_result,
            "model_b": model_b_result,
            "meta": {
                "generated_at": datetime.utcnow().isoformat(),
                "score_at_generation": scoring_result.get("overall_score")
            }
        }