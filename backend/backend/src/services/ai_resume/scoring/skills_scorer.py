from typing import Dict, Any, List, Set
from src.services.ai_resume.scoring.skill_normalizer import SkillNormalizer


class SkillsScorer:
    """
    Deterministic Skills Scorer for the ATS Engine.
    Evaluates technology keyword intersections matching real Job Description items.
    Uses SkillNormalizer to guarantee canonical equivalence (e.g. RESTful API == REST APIs).
    """

    def __init__(self):
        self.normalizer = SkillNormalizer()

    def score_skills(
        self,
        resume_skills: List[str] = None,
        jd_skills: List[str] = None,
        raw_resume_text: str = "",
        raw_jd_text: str = ""
    ) -> Dict[str, Any]:

        final_resume_set = self._extract_and_normalize(resume_skills, raw_resume_text)
        final_jd_set = self._extract_and_normalize(jd_skills, raw_jd_text)

        # Secure default baseline only if JD input is explicitly empty
        if not final_jd_set:
            final_jd_set = {"javascript", "react", "nodejs", "express", "mongodb", "git", "html", "css", "rest"}

        # Equivalence groups (having one item satisfies category requirement)
        skill_groups = [
            {"react", "angular", "vue", "svelte"},                   # Frontend
            {"nodejs", "python", "java", "go", "cpp"},                # Backend Languages
            {"express", "django", "fastapi", "springboot", "flask"}, # Backend Frameworks
            {"postgresql", "mysql", "mongodb", "sqlite", "redis"},   # Databases
            {"rest", "graphql", "soap", "websockets"},               # APIs
            {"html", "css", "javascript", "typescript", "tailwindcss"}# Web Basics
        ]

        strong_skills = final_jd_set.intersection(final_resume_set)

        # Filter missing skills: Only flag an item as missing if NO skill from its group is present
        missing_skills = set()
        for jd_item in final_jd_set.difference(final_resume_set):
            has_group_equivalent = False
            for group in skill_groups:
                if jd_item in group and group.intersection(final_resume_set):
                    has_group_equivalent = True
                    break

            if not has_group_equivalent:
                missing_skills.add(jd_item)

        additional_skills = final_resume_set.difference(final_jd_set)

        # Fair score math
        matched_count = len(strong_skills) + (len(final_jd_set.difference(final_resume_set)) - len(missing_skills))
        required_count = len(final_jd_set)

        raw_score = (matched_count / required_count) * 25.0 if required_count > 0 else 0.0
        total_score = round(min(raw_score, 25.0), 1)

        return {
            "totalScore": total_score,
            "maxScore": 25.0,
            "skillsAnalysis": {
                "strongSkills": sorted([self.normalizer.get_display_name(s) for s in strong_skills]),
                "missingSkills": sorted([self.normalizer.get_display_name(s) for s in missing_skills]),
                "additionalSkills": sorted([self.normalizer.get_display_name(s) for s in additional_skills])
            }
        }

    def _extract_and_normalize(self, explicit_list: List[str], raw_text: str) -> Set[str]:
        """Extracts and normalizes tokens from array or raw text buffer using canonical dictionary."""
        normalized_set = set()

        if explicit_list and isinstance(explicit_list, list):
            for skill in explicit_list:
                canonical = self.normalizer.normalize(skill)
                if canonical:
                    normalized_set.add(canonical)

        if raw_text and isinstance(raw_text, str):
            text_lower = raw_text.lower()
            for phrase, canonical_token in self.normalizer.alias_matrix.items():
                if phrase in text_lower:
                    normalized_set.add(canonical_token)

        return normalized_set