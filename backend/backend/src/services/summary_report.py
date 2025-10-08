"""Service to build the Summary Report directly from per-question analyses.

This does not depend on FinalReportService. It computes two high-level score
bands (Knowledge Competence, Speech & Structure) on a 5-point scale and %,
collects strengths and improvement areas, and proposes actionable steps.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.models.db.question_attempt import QuestionAttempt
from src.models.schemas.summary_report import (
    SummaryMetrics,
    SummarySection,
    SummarySectionGroup,
    KnowledgeCompetenceBreakdown,
    OverallScoreKnowledgeCompetence,
    OverallScoreSpeechStructure,
    SpeechStructureBreakdown,
    SummaryReportResponse,
    PerQuestionAnalysis,
    PerQuestionItem,
)
from src.services.llm import synthesize_summary_sections


def _as_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _as_list_str(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    return [str(v)]


def _avg(nums: List[float]) -> Optional[float]:
    return sum(nums) / len(nums) if nums else None


def _to5(score100: Optional[float]) -> Optional[float]:
    if score100 is None:
        return None
    return round(score100 / 20.0, 2)


def _unique(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for s in items:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _section_from_groups(heading: str, subtitle: str | None, groups_data: List[tuple[str, List[str]]]) -> SummarySection:
    groups = [
        SummarySectionGroup(label=label, items=_unique(items))
        for label, items in groups_data
        if items
    ]
    return SummarySection(heading=heading, subtitle=subtitle, groups=groups)


class SummaryReportService:
    def __init__(self, db: SQLAlchemyAsyncSession) -> None:
        self._db = db

    async def generate_for_interview(
        self, interview_id: int, question_attempts: Iterable[QuestionAttempt], track: str, resume_used: bool | None = None
    ) -> Dict[str, Any]:
        # Materialize attempts to allow multiple passes (metrics + LLM input build)
        question_attempts = list(question_attempts)
        # Buckets for KC (knowledge competence)
        kc_accuracy: List[float] = []
        kc_depth: List[float] = []
        kc_coverage: List[float] = []
        kc_relevance: List[float] = []

        # Buckets for SSF (speech & structure)
        ssf_pacing: List[float] = []
        ssf_structure: List[float] = []
        ssf_pauses: List[float] = []
        ssf_grammar: List[float] = []

        # Strengths / improvements
        strengths_kc: List[str] = []
        strengths_ssf: List[str] = []
        improvements_kc: List[str] = []
        improvements_ssf: List[str] = []

        # Map to store per-question computed percents
        per_q_scores: Dict[int, Dict[str, Optional[float]]] = {}
        per_question_defaults: List[Dict[str, Any]] = []
        per_question_analysis_defaults: List[Dict[str, Any]] = []

        # Gather from per-question analyses
        for qa in question_attempts:
            analysis: Dict[str, Any] = getattr(qa, "analysis_json", None) or {}

            # Domain/knowledge metrics
            d = analysis.get("domain") or {}
            criteria = d.get("criteria") or {}
            local_kc: List[float] = []
            q_strengths_kc = _as_list_str(d.get("strengths"))
            q_improvements_kc = _as_list_str(d.get("improvements"))
            # criteria may be in { correctness: {score}, depth: {score}, coverage: {score}, relevance: {score} }
            for key, target in (
                ("correctness", kc_accuracy),
                ("depth", kc_depth),
                ("coverage", kc_coverage),
                ("relevance", kc_relevance),
            ):
                score = _as_float(((criteria.get(key) or {}).get("score")))
                if score is None:
                    # fallback to domain.overall_score if specific missing
                    score = _as_float(d.get("overall_score"))
                if score is not None:
                    # Assume 0-100 scale coming from LLM; clamp to 0..100
                    score = max(0.0, min(100.0, score))
                    target.append(score)
                    local_kc.append(score)
                else:
                    # If no score available at all, use a default based on per-question scores
                    # This handles cases where the analysis structure is incomplete
                    # Look for per-question scores in the LLM data if available
                    if hasattr(qa, 'id') and qa.id in per_q_scores:
                        per_q_kc = per_q_scores[qa.id].get("kc_pct")
                        if per_q_kc is not None:
                            default_score = max(0.0, min(100.0, per_q_kc))
                            target.append(default_score)
                            local_kc.append(default_score)
            strengths_kc.extend(q_strengths_kc)
            improvements_kc.extend(q_improvements_kc)

            # Communication/speech metrics
            c = analysis.get("communication") or {}
            ccrit = c.get("criteria") or {}
            local_ssf: List[float] = []
            q_strengths_ssf = _as_list_str(c.get("strengths"))
            q_improvements_ssf = _as_list_str(c.get("recommendations"))
            # Map to pacing/structure/grammar; pauses handled separately
            pacing_val = _as_float(c.get("pace_score") or (ccrit.get("pacing", {}) or {}).get("score"))
            if pacing_val is None:
                pacing_val = _as_float(c.get("overall_score"))
            if pacing_val is not None:
                pv = max(0.0, min(100.0, pacing_val))
                ssf_pacing.append(pv)
                local_ssf.append(pv)

            structure_val = _as_float(c.get("structure_score") or (ccrit.get("structure", {}) or {}).get("score"))
            if structure_val is None:
                structure_val = _as_float(c.get("overall_score"))
            if structure_val is not None:
                sv = max(0.0, min(100.0, structure_val))
                ssf_structure.append(sv)
                local_ssf.append(sv)

            grammar_val = _as_float(c.get("grammar_score") or (ccrit.get("grammar", {}) or {}).get("score"))
            if grammar_val is None:
                grammar_val = _as_float(c.get("overall_score"))
            if grammar_val is not None:
                gv = max(0.0, min(100.0, grammar_val))
                ssf_grammar.append(gv)
                local_ssf.append(gv)

            strengths_ssf.extend(q_strengths_ssf)
            # Many times only recommendations exist; treat non-empty positive phrases as strengths if provided

            # Pace/Pause analyses
            p = analysis.get("pace") or {}
            z = analysis.get("pause") or {}
            pace_raw = p.get("score")
            pace_scaled = None
            if isinstance(pace_raw, (int, float)):
                pace_scaled = pace_raw * 20 if pace_raw <= 5 else pace_raw
            pace_score = _as_float(p.get("pace_score") or pace_scaled)
            if pace_score is not None:
                pp = max(0.0, min(100.0, pace_score))
                ssf_pacing.append(pp)
                local_ssf.append(pp)
            pause_raw = z.get("score")
            pause_scaled = None
            if isinstance(pause_raw, (int, float)):
                pause_scaled = pause_raw * 20 if pause_raw <= 5 else pause_raw
            pause_score = _as_float(z.get("pause_score") or pause_scaled)
            if pause_score is not None:
                zz = max(0.0, min(100.0, pause_score))
                ssf_pauses.append(zz)
                local_ssf.append(zz)
            q_improvements_ssf.extend(_as_list_str(p.get("recommendations")))
            q_improvements_ssf.extend(_as_list_str(z.get("recommendations")))
            q_improvements_ssf.extend(_as_list_str(p.get("pace_recommendations")))
            q_improvements_ssf.extend(_as_list_str(z.get("pause_recommendations")))
            improvements_ssf.extend(q_improvements_ssf)

            # Save per-question computed percents and detailed sections
            knowledge_topics = _as_list_str(d.get("knowledge_areas") or [])

            # Save per-question computed percents
            per_q_scores[qa.id] = {
                "kc_pct": _avg(local_kc),
                "ssf_pct": _avg(local_ssf),
            }

            key_takeaways = _unique(
                q_strengths_kc + q_strengths_ssf + q_improvements_kc + q_improvements_ssf
            )[:4]

            per_question_defaults.append(
                {
                    "questionAttemptId": qa.id,
                    "questionText": getattr(qa, "question_text", None),
                    "keyTakeaways": key_takeaways,
                    "knowledgeScorePct": per_q_scores[qa.id]["kc_pct"],
                    "speechScorePct": per_q_scores[qa.id]["ssf_pct"],
                }
            )

            targeted_concept = _unique(q_improvements_kc)[:3]
            speech_practice = _unique(q_improvements_ssf)[:3]
            conceptual_depth = _unique([
                f"Prepare a real-world example covering {topic}"
                for topic in knowledge_topics[:2]
            ])
            if not conceptual_depth:
                conceptual_depth = ["Rehearse the reasoning behind your answer to build deeper intuition."]

            strengths_section_q = _section_from_groups(
                heading="Strengths",
                subtitle="Question-specific positives",
                groups_data=[
                    ("Knowledge-Related", q_strengths_kc),
                    ("Speech & Delivery", q_strengths_ssf),
                ],
            )
            improvements_section_q = _section_from_groups(
                heading="Areas Of Improvement",
                subtitle="Next focus areas",
                groups_data=[
                    ("Knowledge-Related", q_improvements_kc),
                    ("Speech & Delivery", q_improvements_ssf),
                ],
            )
            actionable_section_q = _section_from_groups(
                heading="Actionable Insights",
                subtitle="How to practice",
                groups_data=[
                    ("Targeted Concept Reinforcement", targeted_concept),
                    ("Example Practice", speech_practice),
                    ("Conceptual Depth", conceptual_depth),
                ],
            )

            per_question_analysis_defaults.append(
                {
                    "questionAttemptId": qa.id,
                    "questionText": getattr(qa, "question_text", None),
                    "keyTakeaways": key_takeaways,
                    "knowledgeScorePct": per_q_scores[qa.id]["kc_pct"],
                    "speechScorePct": per_q_scores[qa.id]["ssf_pct"],
                    "strengths": strengths_section_q.model_dump(),
                    "areasOfImprovement": improvements_section_q.model_dump(),
                    "actionableInsights": actionable_section_q.model_dump(),
                }
            )

    # Averages and breakdowns
        kc_breakdown = KnowledgeCompetenceBreakdown(
            accuracy=_to5(_avg(kc_accuracy)),
            depth=_to5(_avg(kc_depth)),
            coverage=_to5(_avg(kc_coverage)),
            relevance=_to5(_avg(kc_relevance)),
        )
        kc_avg_pct = _avg([
            x for x in (
                _avg(kc_accuracy), _avg(kc_depth), _avg(kc_coverage), _avg(kc_relevance)
            ) if x is not None
        ])
        kc_summary = OverallScoreKnowledgeCompetence(
            average5pt=_to5(kc_avg_pct),
            averagePct=kc_avg_pct,
            breakdown=kc_breakdown,
        )

        ssf_breakdown = SpeechStructureBreakdown(
            pacing=_to5(_avg(ssf_pacing)),
            structure=_to5(_avg(ssf_structure)),
            pauses=_to5(_avg(ssf_pauses)),
            grammar=_to5(_avg(ssf_grammar)),
        )
        ssf_avg_pct = _avg([
            x for x in (
                _avg(ssf_pacing), _avg(ssf_structure), _avg(ssf_pauses), _avg(ssf_grammar)
            ) if x is not None
        ])
        ssf_summary = OverallScoreSpeechStructure(
            average5pt=_to5(ssf_avg_pct),
            averagePct=ssf_avg_pct,
            breakdown=ssf_breakdown,
        )

        metrics = SummaryMetrics(
            knowledgeCompetence=kc_summary,
            speechStructure=ssf_summary,
        )
        metrics_fallback_dict = metrics.model_dump()

        strengths_section = _section_from_groups(
            heading="Strengths",
            subtitle="What you did well",
            groups_data=[
                ("Knowledge-Related", strengths_kc),
                ("Speech & Delivery", strengths_ssf),
            ],
        )
        strengths_fallback_dict = strengths_section.model_dump()

        improvements_section = _section_from_groups(
            heading="Areas Of Improvement",
            subtitle="Where to focus next",
            groups_data=[
                ("Knowledge-Related", improvements_kc),
                ("Speech & Delivery", improvements_ssf),
            ],
        )
        improvements_fallback_dict = improvements_section.model_dump()

        actionable_section = _section_from_groups(
            heading="Actionable Insights",
            subtitle="Next steps for growth",
            groups_data=[
                ("Targeted Concept Reinforcement", improvements_kc[:4]),
                (
                    "Example Practice",
                    [
                        "Prepare 2-3 specific project scenarios with detailed code walkthroughs",
                    ],
                ),
                (
                    "Conceptual Depth",
                    [
                        "Practice answering 'why' and 'how' questions beyond surface-level recall",
                    ],
                ),
            ],
        )
        actionable_fallback_dict = actionable_section.model_dump()

        # Build LLM input from per-question items (cap to 5 for cost/latency)
        per_question_inputs: List[dict] = []
        for qa in question_attempts:
            analysis = getattr(qa, "analysis_json", None) or {}
            per_question_inputs.append({
                "questionAttemptId": qa.id,
                "questionText": getattr(qa, "question_text", None),
                "domain": analysis.get("domain", {}),
                "communication": analysis.get("communication", {}),
                "pace": analysis.get("pace", {}),
                "pause": analysis.get("pause", {}),
            })

        computed_metrics = {
            "kc_avg_pct": kc_avg_pct,
            "ssf_avg_pct": ssf_avg_pct,
            "kc_breakdown_pct": {
                "accuracy": _avg(kc_accuracy),
                "depth": _avg(kc_depth),
                "coverage": _avg(kc_coverage),
                "relevance": _avg(kc_relevance),
            },
            "ssf_breakdown_pct": {
                "pacing": _avg(ssf_pacing),
                "structure": _avg(ssf_structure),
                "pauses": _avg(ssf_pauses),
                "grammar": _avg(ssf_grammar),
            },
        }

        # Prefer LLM synthesis when API key is configured
        llm_data, llm_error, latency_ms, model_name = await synthesize_summary_sections(
            per_question_inputs=per_question_inputs,
            computed_metrics=computed_metrics,
            max_questions=5,
        )
        # If LLM returned something, normalize scales and enrich with metadata/perQuestion; otherwise raise
        if not llm_data:
            llm_data = {}

        # Normalization helpers
        def _norm_0_5(x: Any) -> Optional[float]:
            v = _as_float(x)
            if v is None:
                return None
            return max(0.0, min(5.0, v))

        def _norm_0_100(x: Any) -> Optional[float]:
            v = _as_float(x)
            if v is None:
                return None
            return max(0.0, min(100.0, v))

        metrics_json = deepcopy(llm_data.get("metrics", {})) if llm_data.get("metrics") else deepcopy(metrics_fallback_dict)
        kc = metrics_json.get("knowledgeCompetence", {}) or {}
        ss = metrics_json.get("speechStructure", {}) or {}
        # Normalize percentages and 5-pt
        kc["average5pt"] = _norm_0_5(kc.get("average5pt"))
        kc["averagePct"] = _norm_0_100(kc.get("averagePct"))
        kb = (kc.get("breakdown") or {})
        kb["accuracy"] = _norm_0_5(kb.get("accuracy"))
        kb["depth"] = _norm_0_5(kb.get("depth"))
        kb["coverage"] = _norm_0_5(kb.get("coverage"))
        kb["relevance"] = _norm_0_5(kb.get("relevance"))
        kc["breakdown"] = kb

        ss["average5pt"] = _norm_0_5(ss.get("average5pt"))
        ss["averagePct"] = _norm_0_100(ss.get("averagePct"))
        sb = (ss.get("breakdown") or {})
        sb["pacing"] = _norm_0_5(sb.get("pacing"))
        sb["structure"] = _norm_0_5(sb.get("structure"))
        sb["pauses"] = _norm_0_5(sb.get("pauses"))
        sb["grammar"] = _norm_0_5(sb.get("grammar"))
        ss["breakdown"] = sb
        metrics_json["knowledgeCompetence"] = kc
        metrics_json["speechStructure"] = ss

        # Per-question list (optional)
        pq = llm_data.get("perQuestion") or []
        per_question_analysis_llm = llm_data.get("perQuestionAnalysis") or []
        if isinstance(pq, list):
            for item in pq:
                if isinstance(item, dict):
                    item["knowledgeScorePct"] = _norm_0_100(item.get("knowledgeScorePct"))
                    item["speechScorePct"] = _norm_0_100(item.get("speechScorePct"))
                    qa_id = item.get("questionAttemptId")
                    if qa_id in per_q_scores:
                        if item.get("knowledgeScorePct") is None and per_q_scores[qa_id]["kc_pct"] is not None:
                            item["knowledgeScorePct"] = _norm_0_100(per_q_scores[qa_id]["kc_pct"])
                        if item.get("speechScorePct") is None and per_q_scores[qa_id]["ssf_pct"] is not None:
                            item["speechScorePct"] = _norm_0_100(per_q_scores[qa_id]["ssf_pct"])

        # Metadata
        md = llm_data.get("metadata") or {}
        if isinstance(md, dict):
            md.setdefault("totalQuestions", len(per_question_inputs))
            md.setdefault("usedQuestions", min(5, len(per_question_inputs)))
            if latency_ms is not None:
                md["latencyMs"] = latency_ms
            if model_name:
                md["model"] = model_name
            if resume_used is not None:
                md["resumeUsed"] = resume_used
            # Set the generation timestamp
            from datetime import datetime, timezone
            md["generatedAt"] = datetime.now(timezone.utc).isoformat()

        # Backfill missing KC averages/breakdown from computed metrics if LLM omitted them
        if kc.get("averagePct") is None and computed_metrics.get("kc_avg_pct") is not None:
            kc["averagePct"] = _norm_0_100(computed_metrics["kc_avg_pct"])  # type: ignore[index]
            kc["average5pt"] = _norm_0_5(_to5(kc["averagePct"]))
        kbd = computed_metrics.get("kc_breakdown_pct") or {}
        for k in ("accuracy", "depth", "coverage", "relevance"):
            if kb.get(k) is None and k in kbd and kbd[k] is not None:
                kb[k] = _norm_0_5(_to5(kbd[k]))

        def _build_section(data: Any, fallback_dict: Dict[str, Any]) -> Dict[str, Any]:
            if isinstance(data, SummarySection):
                candidate_dict = data.model_dump()
            elif isinstance(data, dict):
                candidate_dict = data
            else:
                candidate_dict = None

            if not candidate_dict:
                candidate_dict = fallback_dict

            try:
                return SummarySection(**candidate_dict).model_dump()
            except Exception:
                return SummarySection(**fallback_dict).model_dump()

        per_question_default_map = {
            item["questionAttemptId"]: item for item in per_question_defaults if item.get("questionAttemptId") is not None
        }
        per_question_analysis_default_map = {
            item["questionAttemptId"]: item for item in per_question_analysis_defaults if item.get("questionAttemptId") is not None
        }

        def _merge_per_question_item(base: Dict[str, Any], overrides: Dict[str, Any] | None) -> Dict[str, Any]:
            merged = dict(base)
            if overrides:
                for key, value in overrides.items():
                    if value is not None:
                        merged[key] = value
            merged["knowledgeScorePct"] = _norm_0_100(merged.get("knowledgeScorePct"))
            merged["speechScorePct"] = _norm_0_100(merged.get("speechScorePct"))
            merged["keyTakeaways"] = _unique(_as_list_str(merged.get("keyTakeaways")))[:4]
            return PerQuestionItem(**merged).model_dump()

        def _merge_per_question_analysis(base: Dict[str, Any], overrides: Dict[str, Any] | None) -> Dict[str, Any]:
            merged = dict(base)
            if overrides:
                if overrides.get("questionAttemptId") is not None:
                    merged["questionAttemptId"] = overrides["questionAttemptId"]
                for key in ("keyTakeaways", "knowledgeScorePct", "speechScorePct"):
                    if overrides.get(key) is not None:
                        merged[key] = overrides[key]
                for section_key in ("strengths", "areasOfImprovement", "actionableInsights"):
                    fallback_section = merged.get(section_key)
                    if not isinstance(fallback_section, dict):
                        fallback_section = base.get(section_key)
                    if not isinstance(fallback_section, dict):
                        fallback_section = SummarySection(
                            heading="",
                            subtitle=None,
                            groups=[],
                        ).model_dump()
                    merged[section_key] = _build_section(overrides.get(section_key), fallback_section)
            # Always prefer the canonical question text from the base attempt data
            merged["questionText"] = base.get("questionText")
            merged["knowledgeScorePct"] = _norm_0_100(merged.get("knowledgeScorePct"))
            merged["speechScorePct"] = _norm_0_100(merged.get("speechScorePct"))
            merged["keyTakeaways"] = _unique(_as_list_str(merged.get("keyTakeaways")))[:4]
            return PerQuestionAnalysis(**merged).model_dump()

        final_per_question: List[Dict[str, Any]] = []
        if isinstance(pq, list) and pq:
            for item in pq:
                if not isinstance(item, dict):
                    continue
                qa_id = item.get("questionAttemptId")
                if qa_id is None:
                    continue
                base = per_question_default_map.get(qa_id)
                if base is None:
                    # If the LLM returned a question we don't have locally, skip
                    continue
                final_per_question.append(_merge_per_question_item(base, item))
        else:
            final_per_question = [
                PerQuestionItem(**{
                    **entry,
                    "knowledgeScorePct": _norm_0_100(entry.get("knowledgeScorePct")),
                    "speechScorePct": _norm_0_100(entry.get("speechScorePct")),
                    "keyTakeaways": _unique(_as_list_str(entry.get("keyTakeaways")))[:4],
                }).model_dump()
                for entry in per_question_defaults
            ]

        final_per_question_map: Dict[int, Dict[str, Any]] = {
            item["questionAttemptId"]: item for item in final_per_question if item.get("questionAttemptId") is not None
        }

        per_question_analysis_map: Dict[int, Dict[str, Any]] = {}
        if isinstance(per_question_analysis_llm, list) and per_question_analysis_llm:
            for item in per_question_analysis_llm:
                if not isinstance(item, dict):
                    continue
                qa_id = item.get("questionAttemptId")
                if qa_id is None:
                    continue
                base = per_question_analysis_map.get(qa_id) or per_question_analysis_default_map.get(qa_id)
                if base is None:
                    continue
                per_question_analysis_map[qa_id] = _merge_per_question_analysis(base, item)
                final_per_question_map.pop(qa_id, None)

        # Backfill any questions the LLM missed or removed after deduplication
        for qa_id, base in per_question_analysis_default_map.items():
            if qa_id not in per_question_analysis_map:
                per_question_analysis_map[qa_id] = _merge_per_question_analysis(base, None)

        final_per_question_analysis: List[Dict[str, Any]] = []
        for item in final_per_question:
            qa_id = item.get("questionAttemptId")
            if qa_id is None:
                continue
            if qa_id not in per_question_analysis_map:
                continue
            final_per_question_analysis.append(per_question_analysis_map.pop(qa_id))

        if per_question_analysis_map:
            final_per_question_analysis.extend(per_question_analysis_map.values())

        candidate = {
            "interview_id": interview_id,
            "track": track,
            "metrics": metrics_json,
            "strengths": _build_section(llm_data.get("strengths"), strengths_fallback_dict),
            "areasOfImprovement": _build_section(llm_data.get("areasOfImprovement"), improvements_fallback_dict),
            "actionableInsights": _build_section(llm_data.get("actionableInsights"), actionable_fallback_dict),
            "metadata": md or None,
            "perQuestion": final_per_question,
            "perQuestionAnalysis": final_per_question_analysis,
            "topicHighlights": llm_data.get("topicHighlights") or None,
        }

        # Validate against schema; let exceptions bubble to FastAPI error handler if invalid
        parsed = SummaryReportResponse(**candidate)
        return parsed.model_dump()
