"""Service to build the Restructured Summary Report directly from per-question analyses.

This generates the new report format with:
- reportId (UUID)
- candidateInfo
- scoreSummary (with numeric scores and percentages)
- overallFeedback (speech fluency only)
- questionAnalysis (per-question feedback, null if not attempted)
"""

from __future__ import annotations

import uuid
import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession
import sqlalchemy

from src.models.db.question_attempt import QuestionAttempt
from src.models.db.interview_question import InterviewQuestion
from src.models.schemas.summary_report import (
    SummaryReportResponse,
    CandidateInfo,
    ScoreSummary,
    KnowledgeCompetenceScore,
    ScoreCriteria,
    SpeechAndStructureScore,
    SpeechCriteria,
    OverallFeedback,
    SpeechFluencyFeedback,
    ActionableStep,
    QuestionAnalysisItem,
    QuestionFeedback,
    QuestionFeedbackSubsection,
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


def _to_int_0_5(score_pct: Optional[float]) -> int:
    """Convert 0-100 percentage to 0-5 integer score."""
    if score_pct is None:
        return 0
    # Convert percentage to 0-5 scale and round
    return round(max(0.0, min(100.0, score_pct)) / 20.0)


def _unique(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for s in items:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


class SummaryReportServiceV2:
    def __init__(self, db: SQLAlchemyAsyncSession) -> None:
        self._db = db

    async def generate_for_interview(
        self,
        interview_id: int,
        question_attempts: Iterable[QuestionAttempt],
        track: str,
        resume_used: bool | None = None,
        candidate_name: str | None = None,
    ) -> Dict[str, Any]:
        """Generate the new restructured summary report."""
        
        question_attempts = list(question_attempts)
        
        # Fetch all InterviewQuestions for this interview
        stmt = sqlalchemy.select(InterviewQuestion).where(
            InterviewQuestion.interview_id == interview_id
        ).order_by(InterviewQuestion.order.asc())
        result = await self._db.execute(stmt)
        all_interview_questions = list(result.scalars().all())
        
        # Build a map of question_id -> QuestionAttempt
        attempts_by_question_id: Dict[int, QuestionAttempt] = {}
        for qa in question_attempts:
            if qa.question_id is not None:
                attempts_by_question_id[qa.question_id] = qa
        
        total_questions = len(all_interview_questions)
        
        # Collect metrics from analyses
        kc_accuracy: List[float] = []
        kc_depth: List[float] = []
        kc_relevance: List[float] = []
        kc_examples: List[float] = []
        kc_terminology: List[float] = []
        
        ssf_fluency: List[float] = []
        ssf_structure: List[float] = []
        ssf_pacing: List[float] = []
        ssf_grammar: List[float] = []
        
        # Collect feedback strings
        speech_strengths: List[str] = []
        speech_improvements: List[str] = []
        
        # Build per-question inputs for LLM
        per_question_inputs: List[dict] = []
        
        for interview_question in all_interview_questions:
            qa = attempts_by_question_id.get(interview_question.id)
            
            if qa is None:
                # Unattempted question - add to LLM input but with no analysis
                per_question_inputs.append({
                    "questionId": interview_question.id,
                    "questionAttemptId": None,
                    "questionText": interview_question.text,
                    "questionCategory": interview_question.category,
                    "attempted": False,
                    "domain": {},
                    "communication": {},
                    "pace": {},
                    "pause": {},
                })
                continue
            
            # Attempted question - process analysis
            analysis: Dict[str, Any] = getattr(qa, "analysis_json", None) or {}
            
            # Domain/knowledge metrics
            d = analysis.get("domain") or {}
            criteria = d.get("criteria") or {}
            
            # Extract scores for each criterion (0-100 scale from LLM)
            accuracy_score = _as_float(((criteria.get("correctness") or {}).get("score")))
            if accuracy_score is not None:
                kc_accuracy.append(max(0.0, min(100.0, accuracy_score)))
            
            depth_score = _as_float(((criteria.get("depth") or {}).get("score")))
            if depth_score is not None:
                kc_depth.append(max(0.0, min(100.0, depth_score)))
            
            relevance_score = _as_float(((criteria.get("relevance") or {}).get("score")))
            if relevance_score is not None:
                kc_relevance.append(max(0.0, min(100.0, relevance_score)))
            
            # Examples and terminology - may not always be present
            examples_score = _as_float(((criteria.get("examples") or {}).get("score")))
            if examples_score is not None:
                kc_examples.append(max(0.0, min(100.0, examples_score)))
            
            terminology_score = _as_float(((criteria.get("terminology") or {}).get("score")))
            if terminology_score is not None:
                kc_terminology.append(max(0.0, min(100.0, terminology_score)))
            
            # Communication/speech metrics
            c = analysis.get("communication") or {}
            ccrit = c.get("criteria") or {}
            
            structure_val = _as_float(c.get("structure_score") or (ccrit.get("structure", {}) or {}).get("score"))
            if structure_val is not None:
                ssf_structure.append(max(0.0, min(100.0, structure_val)))
            
            grammar_val = _as_float(c.get("grammar_score") or (ccrit.get("grammar", {}) or {}).get("score"))
            if grammar_val is not None:
                ssf_grammar.append(max(0.0, min(100.0, grammar_val)))
            
            # Pace/Pause analyses
            p = analysis.get("pace") or {}
            z = analysis.get("pause") or {}
            
            pace_raw = p.get("score")
            if isinstance(pace_raw, (int, float)):
                pace_scaled = pace_raw * 20 if pace_raw <= 5 else pace_raw
                ssf_pacing.append(max(0.0, min(100.0, pace_scaled)))
            
            # Collect speech feedback
            speech_strengths.extend(_as_list_str(c.get("strengths")))
            speech_improvements.extend(_as_list_str(c.get("recommendations")))
            speech_improvements.extend(_as_list_str(p.get("recommendations")))
            speech_improvements.extend(_as_list_str(z.get("recommendations")))
            
            # Build input for LLM
            per_question_inputs.append({
                "questionId": interview_question.id,
                "questionAttemptId": qa.id,
                "questionText": interview_question.text,
                "questionCategory": interview_question.category,
                "attempted": True,
                "domain": d,
                "communication": c,
                "pace": p,
                "pause": z,
            })
        
        # Compute aggregated metrics
        computed_metrics = {
            "kc_accuracy_pct": _avg(kc_accuracy),
            "kc_depth_pct": _avg(kc_depth),
            "kc_relevance_pct": _avg(kc_relevance),
            "kc_examples_pct": _avg(kc_examples) if kc_examples else 0.0,
            "kc_terminology_pct": _avg(kc_terminology) if kc_terminology else 0.0,
            "ssf_fluency_pct": _avg(ssf_fluency) if ssf_fluency else _avg([
                x for x in [_avg(ssf_structure), _avg(ssf_grammar)] if x is not None
            ]),
            "ssf_structure_pct": _avg(ssf_structure),
            "ssf_pacing_pct": _avg(ssf_pacing),
            "ssf_grammar_pct": _avg(ssf_grammar),
            "total_questions": total_questions,
            "attempted_questions": len(question_attempts),
            "speech_strengths": _unique(speech_strengths)[:6],
            "speech_improvements": _unique(speech_improvements)[:6],
        }
        
        # Call LLM to synthesize the report
        interview_date = datetime.now(timezone.utc).isoformat()
        llm_data, llm_error, latency_ms, model_name = await synthesize_summary_sections(
            per_question_inputs=per_question_inputs,
            computed_metrics=computed_metrics,
            max_questions=None,  # Include all questions
            interview_track=track,
            interview_date=interview_date,
            candidate_name=candidate_name,
            total_questions=total_questions,
        )
        
        # If LLM failed, build a fallback report
        if not llm_data or llm_error:
            return self._build_fallback_report(
                interview_id=interview_id,
                track=track,
                computed_metrics=computed_metrics,
                all_questions=all_interview_questions,
                attempts_map=attempts_by_question_id,
                interview_date=interview_date,
                candidate_name=candidate_name,
            )
        
        # Calculate final scores from LLM's per-question scores
        try:
            final_report = self._calculate_final_scores(
                llm_data=llm_data,
                total_questions=total_questions,
                all_questions=all_interview_questions,
                track=track,
                interview_date=interview_date,
                candidate_name=candidate_name,
            )
            # Validate the final report
            parsed = SummaryReportResponse(**final_report)
            return parsed.model_dump(exclude_none=False)
        except Exception as e:
            # LLM data invalid or calculation failed - fall back
            return self._build_fallback_report(
                interview_id=interview_id,
                track=track,
                computed_metrics=computed_metrics,
                all_questions=all_interview_questions,
                attempts_map=attempts_by_question_id,
                interview_date=interview_date,
                candidate_name=candidate_name,
            )
    
    def _calculate_final_scores(
        self,
        llm_data: Dict[str, Any],
        total_questions: int,
        all_questions: List[InterviewQuestion],
        track: str,
        interview_date: str,
        candidate_name: str | None,
    ) -> Dict[str, Any]:
        """Calculate final scores with attempt-based penalty from LLM's per-question scores.
        
        Also builds reportId, candidateInfo, and questionAnalysis from code (not LLM).
        
        Formula:
        1. Sum individual criterion scores across all attempted questions
        2. Apply attempt penalty: final_score = sum × (attempted / total)
        3. Calculate percentage: (final_score / maxScore) × 100
        """
        per_question_scores = llm_data.get("perQuestionScores", [])
        per_question_feedback = llm_data.get("perQuestionFeedback", [])
        attempted_questions = len(per_question_scores)
        
        if attempted_questions == 0 or total_questions == 0:
            # No attempts - return zeros
            attempt_ratio = 0.0
        else:
            attempt_ratio = attempted_questions / total_questions
        
        # Sum knowledge scores across all attempted questions
        kc_accuracy_sum = 0
        kc_depth_sum = 0
        kc_relevance_sum = 0
        kc_examples_sum = 0
        kc_terminology_sum = 0
        
        # Sum speech scores across all attempted questions
        ssf_fluency_sum = 0
        ssf_structure_sum = 0
        ssf_pacing_sum = 0
        ssf_grammar_sum = 0
        
        for q_scores in per_question_scores:
            k_scores = q_scores.get("knowledgeScores", {})
            kc_accuracy_sum += k_scores.get("accuracy", 0)
            kc_depth_sum += k_scores.get("depth", 0)
            kc_relevance_sum += k_scores.get("relevance", 0)
            kc_examples_sum += k_scores.get("examples", 0)
            kc_terminology_sum += k_scores.get("terminology", 0)
            
            s_scores = q_scores.get("speechScores", {})
            ssf_fluency_sum += s_scores.get("fluency", 0)
            ssf_structure_sum += s_scores.get("structure", 0)
            ssf_pacing_sum += s_scores.get("pacing", 0)
            ssf_grammar_sum += s_scores.get("grammar", 0)
        
        # Calculate total sums from attempted questions
        kc_total_from_attempted = (kc_accuracy_sum + kc_depth_sum + kc_relevance_sum + 
                                   kc_examples_sum + kc_terminology_sum)
        ssf_total_from_attempted = (ssf_fluency_sum + ssf_structure_sum + 
                                    ssf_pacing_sum + ssf_grammar_sum)
        
        # Calculate AVERAGE scores per question (not sum!)
        # This prevents score inflation when multiple questions are attempted
        if attempted_questions > 0:
            kc_avg_per_question = kc_total_from_attempted / attempted_questions
            ssf_avg_per_question = ssf_total_from_attempted / attempted_questions
        else:
            kc_avg_per_question = 0
            ssf_avg_per_question = 0
        
        # Apply attempt penalty: scale average by completion ratio
        # Max possible score is (max_score × completion_ratio)
        kc_score_total = round(kc_avg_per_question * attempt_ratio)
        ssf_score_total = round(ssf_avg_per_question * attempt_ratio)
        
        # Distribute the final penalized score back to criteria proportionally
        # This ensures criteria sum exactly to the final score
        if kc_total_from_attempted > 0:
            kc_accuracy_final = round(kc_score_total * (kc_accuracy_sum / kc_total_from_attempted))
            kc_depth_final = round(kc_score_total * (kc_depth_sum / kc_total_from_attempted))
            kc_relevance_final = round(kc_score_total * (kc_relevance_sum / kc_total_from_attempted))
            kc_examples_final = round(kc_score_total * (kc_examples_sum / kc_total_from_attempted))
            # Give remaining to last criterion to ensure exact sum
            kc_terminology_final = kc_score_total - (kc_accuracy_final + kc_depth_final + kc_relevance_final + kc_examples_final)
        else:
            kc_accuracy_final = kc_depth_final = kc_relevance_final = kc_examples_final = kc_terminology_final = 0
        
        if ssf_total_from_attempted > 0:
            ssf_fluency_final = round(ssf_score_total * (ssf_fluency_sum / ssf_total_from_attempted))
            ssf_structure_final = round(ssf_score_total * (ssf_structure_sum / ssf_total_from_attempted))
            ssf_pacing_final = round(ssf_score_total * (ssf_pacing_sum / ssf_total_from_attempted))
            # Give remaining to last criterion to ensure exact sum
            ssf_grammar_final = ssf_score_total - (ssf_fluency_final + ssf_structure_final + ssf_pacing_final)
        else:
            ssf_fluency_final = ssf_structure_final = ssf_pacing_final = ssf_grammar_final = 0
        
        # Calculate averages
        kc_avg = kc_score_total / 5.0
        ssf_avg = ssf_score_total / 4.0
        
        # Calculate percentages (max: KC=25, SSF=20)
        kc_pct = int((kc_score_total / 25.0) * 100)
        ssf_pct = int((ssf_score_total / 20.0) * 100)
        
        # Build the score summary
        score_summary = {
            "knowledgeCompetence": {
                "score": kc_score_total,
                "maxScore": 25,
                "average": round(kc_avg, 2),
                "maxAverage": 5.0,
                "percentage": kc_pct,
                "criteria": {
                    "accuracy": kc_accuracy_final,
                    "depth": kc_depth_final,
                    "relevance": kc_relevance_final,
                    "examples": kc_examples_final,
                    "terminology": kc_terminology_final,
                }
            },
            "speechAndStructure": {
                "score": ssf_score_total,
                "maxScore": 20,
                "average": round(ssf_avg, 2),
                "maxAverage": 5.0,
                "percentage": ssf_pct,
                "criteria": {
                    "fluency": ssf_fluency_final,
                    "structure": ssf_structure_final,
                    "pacing": ssf_pacing_final,
                    "grammar": ssf_grammar_final,
                }
            }
        }
        
        # Build candidateInfo in code
        candidate_info = {
            "name": candidate_name,
            "interviewDate": interview_date,
            "roleTopic": track.title(),
        }
        
        # Build questionAnalysis from code (question metadata) + LLM (feedback)
        # Create a map of questionId to feedback from LLM
        feedback_by_question_id = {}
        for idx, score in enumerate(per_question_scores):
            q_id = score.get("questionId")
            if idx < len(per_question_feedback):
                llm_feedback = per_question_feedback[idx]
                if llm_feedback is not None:
                    # Only include feedback if it has actual content
                    feedback_data = llm_feedback.get("knowledgeRelated", {})
                    has_content = (
                        feedback_data.get("strengths") or
                        feedback_data.get("areasOfImprovement") or
                        feedback_data.get("actionableInsights")
                    )
                    if has_content:
                        feedback_by_question_id[q_id] = {"knowledgeRelated": feedback_data}
        
        question_analysis = []
        for idx, iq in enumerate(all_questions):
            # Map question category to type string
            category_map = {
                "tech": "Technical question",
                "tech_allied": "Technical Allied question", 
                "behavioral": "Behavioral question",
            }
            question_type = category_map.get(iq.category, "Technical question")
            
            # Get feedback from LLM if available for this question
            feedback = feedback_by_question_id.get(iq.id)
            
            question_analysis.append({
                "id": idx + 1,  # 1-indexed for display
                "totalQuestions": total_questions,
                "type": question_type,
                "question": iq.text,
                "feedback": feedback,
            })
        
        # Return the complete report with calculated scores and code-generated metadata
        return {
            "reportId": str(uuid.uuid4()),  # Generate in code
            "candidateInfo": candidate_info,  # Generate in code
            "scoreSummary": score_summary,
            "overallFeedback": llm_data.get("overallFeedback"),
            "questionAnalysis": question_analysis,  # Built from code + LLM feedback
        }
    
    def _build_fallback_report(
        self,
        interview_id: int,
        track: str,
        computed_metrics: Dict[str, Any],
        all_questions: List[InterviewQuestion],
        attempts_map: Dict[int, QuestionAttempt],
        interview_date: str,
        candidate_name: str | None,
    ) -> Dict[str, Any]:
        """Build a fallback report when LLM fails."""
        
        # Generate report ID
        report_id = str(uuid.uuid4())
        
        # Candidate info
        candidate_info = CandidateInfo(
            name=candidate_name,
            interviewDate=interview_date,
            roleTopic=track.title(),
        )
        
        # Calculate base scores (from attempted questions average)
        kc_accuracy = _to_int_0_5(computed_metrics.get("kc_accuracy_pct"))
        kc_depth = _to_int_0_5(computed_metrics.get("kc_depth_pct"))
        kc_relevance = _to_int_0_5(computed_metrics.get("kc_relevance_pct"))
        kc_examples = _to_int_0_5(computed_metrics.get("kc_examples_pct"))
        kc_terminology = _to_int_0_5(computed_metrics.get("kc_terminology_pct"))
        
        ssf_fluency = _to_int_0_5(computed_metrics.get("ssf_fluency_pct"))
        ssf_structure = _to_int_0_5(computed_metrics.get("ssf_structure_pct"))
        ssf_pacing = _to_int_0_5(computed_metrics.get("ssf_pacing_pct"))
        ssf_grammar = _to_int_0_5(computed_metrics.get("ssf_grammar_pct"))
        
        # Calculate attempt penalty
        total_questions = computed_metrics.get("total_questions", len(all_questions))
        attempted_questions = computed_metrics.get("attempted_questions", len(attempts_map))
        
        if attempted_questions == 0 or total_questions == 0:
            attempt_ratio = 0.0
        else:
            attempt_ratio = attempted_questions / total_questions
        
        # Calculate totals BEFORE penalty
        kc_total_before_penalty = kc_accuracy + kc_depth + kc_relevance + kc_examples + kc_terminology
        ssf_total_before_penalty = ssf_fluency + ssf_structure + ssf_pacing + ssf_grammar
        
        # Apply attempt penalty to totals (not individual criteria)
        kc_score = round(kc_total_before_penalty * attempt_ratio)
        ssf_score = round(ssf_total_before_penalty * attempt_ratio)
        
        # Distribute the final penalized score back to criteria proportionally
        if kc_total_before_penalty > 0:
            kc_accuracy_final = round(kc_score * (kc_accuracy / kc_total_before_penalty))
            kc_depth_final = round(kc_score * (kc_depth / kc_total_before_penalty))
            kc_relevance_final = round(kc_score * (kc_relevance / kc_total_before_penalty))
            kc_examples_final = round(kc_score * (kc_examples / kc_total_before_penalty))
            # Give remaining to last criterion to ensure exact sum
            kc_terminology_final = kc_score - (kc_accuracy_final + kc_depth_final + kc_relevance_final + kc_examples_final)
        else:
            kc_accuracy_final = kc_depth_final = kc_relevance_final = kc_examples_final = kc_terminology_final = 0
        
        if ssf_total_before_penalty > 0:
            ssf_fluency_final = round(ssf_score * (ssf_fluency / ssf_total_before_penalty))
            ssf_structure_final = round(ssf_score * (ssf_structure / ssf_total_before_penalty))
            ssf_pacing_final = round(ssf_score * (ssf_pacing / ssf_total_before_penalty))
            # Give remaining to last criterion to ensure exact sum
            ssf_grammar_final = ssf_score - (ssf_fluency_final + ssf_structure_final + ssf_pacing_final)
        else:
            ssf_fluency_final = ssf_structure_final = ssf_pacing_final = ssf_grammar_final = 0
        
        # Calculate averages and percentages
        kc_avg = kc_score / 5.0
        kc_pct = int((kc_score / 25.0) * 100)
        
        ssf_avg = ssf_score / 4.0
        ssf_pct = int((ssf_score / 20.0) * 100)
        
        score_summary = ScoreSummary(
            knowledgeCompetence=KnowledgeCompetenceScore(
                score=kc_score,
                maxScore=25,
                average=round(kc_avg, 2),
                maxAverage=5.0,
                percentage=kc_pct,
                criteria=ScoreCriteria(
                    accuracy=kc_accuracy_final,
                    depth=kc_depth_final,
                    relevance=kc_relevance_final,
                    examples=kc_examples_final,
                    terminology=kc_terminology_final,
                ),
            ),
            speechAndStructure=SpeechAndStructureScore(
                score=ssf_score,
                maxScore=20,
                average=round(ssf_avg, 2),
                maxAverage=5.0,
                percentage=ssf_pct,
                criteria=SpeechCriteria(
                    fluency=ssf_fluency_final,
                    structure=ssf_structure_final,
                    pacing=ssf_pacing_final,
                    grammar=ssf_grammar_final,
                ),
            ),
        )
        
        # Overall feedback (speech only)
        speech_strengths = computed_metrics.get("speech_strengths", [])
        speech_improvements = computed_metrics.get("speech_improvements", [])
        
        overall_feedback = OverallFeedback(
            speechFluency=SpeechFluencyFeedback(
                strengths=speech_strengths[:4],
                areasOfImprovement=speech_improvements[:4],
                actionableSteps=[
                    ActionableStep(
                        title="Practice Regular Speaking",
                        description="Record yourself answering technical questions and review for fluency improvements.",
                    ),
                    ActionableStep(
                        title="Structured Response Framework",
                        description="Use a clear structure: state the problem, explain your approach, provide examples, and summarize.",
                    ),
                ],
            ),
        )
        
        # Question analysis
        question_analysis: List[QuestionAnalysisItem] = []
        total_questions = len(all_questions)
        
        for interview_question in all_questions:
            qa = attempts_map.get(interview_question.id)
            
            # Map category
            q_type = "Technical question"
            if interview_question.category == "tech_allied":
                q_type = "Technical Allied question"
            elif interview_question.category == "behavioral":
                q_type = "Behavioral question"
            
            if qa is None:
                # Not attempted
                question_analysis.append(QuestionAnalysisItem(
                    id=interview_question.id,
                    totalQuestions=total_questions,
                    type=q_type,
                    question=interview_question.text,
                    feedback=None,
                ))
            else:
                # Attempted - extract feedback from analysis
                analysis = getattr(qa, "analysis_json", None) or {}
                d = analysis.get("domain") or {}
                
                strengths = _as_list_str(d.get("strengths"))[:3]
                improvements = _as_list_str(d.get("improvements"))[:3]
                
                question_analysis.append(QuestionAnalysisItem(
                    id=interview_question.id,
                    totalQuestions=total_questions,
                    type=q_type,
                    question=interview_question.text,
                    feedback=QuestionFeedback(
                        knowledgeRelated=QuestionFeedbackSubsection(
                            strengths=strengths,
                            areasOfImprovement=improvements,
                            actionableInsights=[
                                ActionableStep(
                                    title="Deepen Understanding",
                                    description="Review core concepts related to this question and practice explaining them clearly.",
                                ),
                            ],
                        ),
                    ),
                ))
        
        # Build final response
        report = SummaryReportResponse(
            reportId=report_id,
            candidateInfo=candidate_info,
            scoreSummary=score_summary,
            overallFeedback=overall_feedback,
            questionAnalysis=question_analysis,
        )
        
        return report.model_dump(exclude_none=False)
