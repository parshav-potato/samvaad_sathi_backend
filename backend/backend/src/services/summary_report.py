"""Service to build the Summary Report directly from per-question analyses.

This does not depend on FinalReportService. It computes two high-level score
bands (Knowledge Competence, Speech & Structure) on a 5-point scale and %,
collects strengths and improvement areas, and proposes actionable steps.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.models.db.question_attempt import QuestionAttempt
from src.models.schemas.summary_report import (
    ActionableSteps,
    FinalSummary,
    FinalSummarySection,
    KnowledgeCompetenceBreakdown,
    KnowledgeDevelopmentSteps,
    OverallScoreKnowledgeCompetence,
    OverallScoreSpeechStructure,
    OverallScoreSummary,
    SpeechStructureBreakdown,
    SpeechStructureFluencySteps,
    SummaryReportResponse,
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

        # Gather from per-question analyses
        for qa in question_attempts:
            analysis: Dict[str, Any] = getattr(qa, "analysis_json", None) or {}

            # Domain/knowledge metrics
            d = analysis.get("domain") or {}
            criteria = d.get("criteria") or {}
            local_kc: List[float] = []
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
            strengths_kc.extend(_as_list_str(d.get("strengths")))
            improvements_kc.extend(_as_list_str(d.get("improvements")))

            # Communication/speech metrics
            c = analysis.get("communication") or {}
            ccrit = c.get("criteria") or {}
            local_ssf: List[float] = []
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

            strengths_ssf.extend(_as_list_str(c.get("strengths")))
            # Many times only recommendations exist; treat non-empty positive phrases as strengths if provided
            improvements_ssf.extend(_as_list_str(c.get("recommendations")))

            # Pace/Pause analyses
            p = analysis.get("pace") or {}
            z = analysis.get("pause") or {}
            pace_score = _as_float(p.get("pace_score") or (p.get("score") * 20 if isinstance(p.get("score"), (int, float)) and p.get("score") <= 5 else None))
            if pace_score is not None:
                pp = max(0.0, min(100.0, pace_score))
                ssf_pacing.append(pp)
                local_ssf.append(pp)
            pause_score = _as_float(z.get("pause_score") or (z.get("score") * 20 if isinstance(z.get("score"), (int, float)) and z.get("score") <= 5 else None))
            if pause_score is not None:
                zz = max(0.0, min(100.0, pause_score))
                ssf_pauses.append(zz)
                local_ssf.append(zz)
            improvements_ssf.extend(_as_list_str(p.get("recommendations")))
            improvements_ssf.extend(_as_list_str(z.get("recommendations")))

            # Save per-question computed percents
            per_q_scores[qa.id] = {
                "kc_pct": _avg(local_kc),
                "ssf_pct": _avg(local_ssf),
            }

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

        overall_score_summary = OverallScoreSummary(
            knowledgeCompetence=kc_summary,
            speechStructure=ssf_summary,
        )

        # Final summary strengths/improvements (dedup, preserve order)
        def _unique(items: List[str]) -> List[str]:
            seen: set[str] = set()
            out: List[str] = []
            for s in items:
                if s and s not in seen:
                    seen.add(s)
                    out.append(s)
            return out

        strengths = FinalSummarySection(
            knowledgeRelated=_unique(strengths_kc),
            speechFluencyRelated=_unique(strengths_ssf),
        )
        improvements = FinalSummarySection(
            knowledgeRelated=_unique(improvements_kc),
            speechFluencyRelated=_unique(improvements_ssf),
        )
        final_summary = FinalSummary(strengths=strengths, areasOfImprovement=improvements)

        # Actionable steps (baseline mapping from improvements)
        kd = KnowledgeDevelopmentSteps(
            targetedConceptReinforcement=_unique(improvements_kc[:4]),
            examplePractice=["Prepare 2-3 specific practice scenarios with detailed code walkthroughs"],
            conceptualDepth=["Practice answering 'why' and 'how' questions beyond surface-level recall"],
        )
        ssf_steps = SpeechStructureFluencySteps(
            fluencyDrills=[
                "Record 3-5 responses weekly and identify filler word patterns",
            ],
            grammarPractice=[
                "Focus on consistent verb tenses and article usage in technical explanations",
            ],
            structureFramework=[
                "Use the STAR method: Situation, Task, Action, Result for experience-based questions",
            ],
        )
        actionable = ActionableSteps(knowledgeDevelopment=kd, speechStructureFluency=ssf_steps)

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
        if not llm_data or not llm_data.get("overallScoreSummary"):
            raise RuntimeError("LLM summary synthesis failed: empty output")

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

        oss = llm_data.get("overallScoreSummary", {}) or {}
        kc = oss.get("knowledgeCompetence", {}) or {}
        ss = oss.get("speechStructure", {}) or {}
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
        oss["knowledgeCompetence"] = kc
        oss["speechStructure"] = ss

        # Per-question list (optional)
        pq = llm_data.get("perQuestion") or []
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

        # Backfill missing KC averages/breakdown from computed metrics if LLM omitted them
        if kc.get("averagePct") is None and computed_metrics.get("kc_avg_pct") is not None:
            kc["averagePct"] = _norm_0_100(computed_metrics["kc_avg_pct"])  # type: ignore[index]
            kc["average5pt"] = _norm_0_5(_to5(kc["averagePct"]))
        kbd = computed_metrics.get("kc_breakdown_pct") or {}
        for k in ("accuracy", "depth", "coverage", "relevance"):
            if kb.get(k) is None and k in kbd and kbd[k] is not None:
                kb[k] = _norm_0_5(_to5(kbd[k]))

        candidate = {
            "interview_id": interview_id,
            "track": track,
            "overallScoreSummary": oss,
            "finalSummary": llm_data.get("finalSummary", {}),
            "actionableSteps": llm_data.get("actionableSteps", {}),
            "metadata": md or None,
            "perQuestion": pq or [],
            "topicHighlights": llm_data.get("topicHighlights") or None,
        }

        # Validate against schema; let exceptions bubble to FastAPI error handler if invalid
        parsed = SummaryReportResponse(**candidate)
        return parsed.model_dump()
