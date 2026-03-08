"""Service layer for speech pacing practice.

Responsibilities
----------------
* Load and vend prompts from the static JSON bank.
* Compute WPM and pause-distribution metrics from Whisper word timestamps.
* Score a single attempt (0-100) based on WPM and pause interval targets.
* Derive level unlock status and overall readiness from persisted best scores.
"""

import json
import re
import random
from pathlib import Path
from typing import Optional

from src.services.pace_analysis import calculate_pace_metrics

# ---------------------------------------------------------------------------
# Prompt bank
# ---------------------------------------------------------------------------

_PROMPT_BANK: dict | None = None

# Level metadata kept here so it is always consistent across service + routes
LEVEL_META: dict[int, dict] = {
    1: {
        "name": "Level 1 - Sentence Control",
        "description": "Master basic sentence delivery and pacing",
    },
    2: {
        "name": "Level 2 - Paragraph Fluency",
        "description": "Build confidence with longer responses",
    },
    3: {
        "name": "Level 3 - Interview Mastery",
        "description": "Handle complex questions with confidence",
    },
}

# Score needed at level N to unlock level N+1
UNLOCK_THRESHOLD = 90


# ---------------------------------------------------------------------------
# Filler word detection
# ---------------------------------------------------------------------------

# Unambiguous non-lexical fillers only — contextual words ("like", "actually",
# "right") are deliberately excluded to avoid false-positives.
FILLER_WORDS: set[str] = {
    "um", "uh", "hmm", "hm", "er", "ah", "erm",
    "uhh", "umm", "ahh", "uhm", "mhm", "ugh",
}


def detect_filler_words(transcript: str, words: list[dict]) -> dict:
    """Count filler words and classify density.

    Parameters
    ----------
    transcript:
        Full plain-text transcription string (unused beyond signature compat —
        detection is done at the word-token level via *words*).
    words:
        Whisper word-level list used to get individual spoken tokens.

    Returns
    -------
    dict with keys:
        count, total_words, filler_ratio, status, suggestion, fillers_found
    """
    tokens = [w.get("word", "").strip().lower().strip(".,!?;:") for w in words]
    total_words = len(tokens)

    fillers_found: list[str] = [t for t in tokens if t in FILLER_WORDS]
    count = len(fillers_found)
    filler_ratio = count / total_words if total_words > 0 else 0.0

    if filler_ratio <= 0.03:
        status = "Good"
        suggestion = (
            "Great job! Your speech is clean and free of filler sounds."
            if count == 0
            else "Very few filler sounds detected. Keep up the clean delivery."
        )
    elif filler_ratio <= 0.08:
        status = "Average"
        suggestion = (
            'A few filler sounds appeared while speaking. '
            'Try pausing silently instead of saying "um" or "uh".'
        )
    else:
        status = "Needs Adjustment"
        suggestion = (
            "Frequent filler sounds are interrupting your speech. "
            "Slow slightly and replace filler words with short silent pauses."
        )

    return {
        "count": count,
        "total_words": total_words,
        "filler_ratio": round(filler_ratio, 4),
        "status": status,
        "suggestion": suggestion,
        "fillers_found": fillers_found,
    }


def _filler_score(filler_ratio: float) -> float:
    """Map filler ratio to a 0-100 score.

    0.00 → 100  |  0.03 → 75  |  0.08 → 40  |  ≥ 0.20 → 0
    """
    if filler_ratio <= 0.03:
        return 100.0 - (filler_ratio / 0.03) * 25
    elif filler_ratio <= 0.08:
        return 75.0 - ((filler_ratio - 0.03) / 0.05) * 35
    elif filler_ratio <= 0.20:
        return max(0.0, 40.0 - ((filler_ratio - 0.08) / 0.12) * 40)
    return 0.0


# ---------------------------------------------------------------------------
# Pause distribution — linguistic-structure-aware scoring
# ---------------------------------------------------------------------------

# Gaps ≥ this many seconds between consecutive words count as a deliberate pause.
_PAUSE_THRESHOLD_S = 0.50

_STRONG_PUNCT = frozenset([".", "?", "!", ";", ":"])
_MEDIUM_PUNCT  = frozenset([",", "—", "–"])


def _parse_prompt_pause_zones(prompt_text: str) -> dict:
    """Tokenise *prompt_text* and locate expected pause zones.

    Returns
    -------
    dict with keys:
        word_count, mandatory_zones (list[int]), optional_zones (list[int]),
        expected_pauses (float)
    """
    tokens = prompt_text.split()
    mandatory: list[int] = []
    optional_: list[int] = []
    word_idx = 0

    for token in tokens:
        bare = token.rstrip(".,!?;:—–")
        trailing = token[len(bare):]

        if bare:
            word_idx_for_this = word_idx
            word_idx += 1
        else:
            word_idx_for_this = max(0, word_idx - 1)

        for ch in trailing:
            if ch in _STRONG_PUNCT:
                mandatory.append(word_idx_for_this)
            elif ch in _MEDIUM_PUNCT:
                optional_.append(word_idx_for_this)

    expected = len(mandatory) + len(optional_) * 0.6

    return {
        "word_count": word_idx,
        "mandatory_zones": mandatory,
        "optional_zones": optional_,
        "expected_pauses": round(expected, 2),
    }


def _detect_audio_pauses(words: list[dict]) -> list[int]:
    """Return word-indices *after* which a pause ≥ 500 ms was detected."""
    pause_positions: list[int] = []
    for i in range(len(words) - 1):
        gap = words[i + 1].get("start", 0.0) - words[i].get("end", 0.0)
        if gap >= _PAUSE_THRESHOLD_S:
            pause_positions.append(i)
    return pause_positions


def _is_near_zone(pause_idx: int, zones: list[int], tolerance: int = 1) -> bool:
    return any(abs(pause_idx - z) <= tolerance for z in zones)


def _segment_lengths(words: list[dict], pause_positions: list[int]) -> list[int]:
    if not pause_positions:
        return [len(words)]
    segs: list[int] = []
    prev = 0
    for pos in sorted(pause_positions):
        segs.append(pos - prev + 1)
        prev = pos + 1
    segs.append(len(words) - prev)
    return [s for s in segs if s > 0]


def score_pause_distribution(words: list[dict], prompt_text: str) -> dict:
    """Full 4-component pause distribution scorer (0-100).

    Components
    ----------
    40 %  Placement Accuracy   – pauses at/near expected punctuation zones
    30 %  Mandatory Compliance – pauses at sentence-ending punctuation
    20 %  Segment Length       – word-chunks in ideal 6-12 range
    10 %  Over/Under Penalty   – extreme behaviour check

    Returns
    -------
    dict with all raw metrics + pause_score (0-100) + status + feedback.
    """
    structure       = _parse_prompt_pause_zones(prompt_text)
    mandatory_zones = structure["mandatory_zones"]
    optional_zones  = structure["optional_zones"]
    all_zones       = mandatory_zones + optional_zones
    expected_pauses = structure["expected_pauses"]

    detected       = _detect_audio_pauses(words)
    total_detected = len(detected)

    # ----- 1. Placement Accuracy (40 %) -----------------------------------
    total_zones = len(all_zones)
    if total_zones > 0:
        correct = sum(1 for p in detected if _is_near_zone(p, all_zones))
        placement_acc = correct / total_zones
    else:
        placement_acc = 1.0
        correct = total_detected

    placement_pts = placement_acc * 40

    # ----- 2. Mandatory Pause Compliance (30 %) ---------------------------
    n_mandatory = len(mandatory_zones)
    if n_mandatory > 0:
        mandatory_hit    = sum(
            1 for z in mandatory_zones
            if any(abs(p - z) <= 1 for p in detected)
        )
        mandatory_compliance = mandatory_hit / n_mandatory
        mandatory_missed     = n_mandatory - mandatory_hit
    else:
        mandatory_compliance = 1.0
        mandatory_hit    = 0
        mandatory_missed = 0

    mandatory_pts = mandatory_compliance * 30

    # ----- 3. Segment Length Accuracy (20 %) ------------------------------
    segs = _segment_lengths(words, detected)
    if segs:
        good_segs = sum(1 for s in segs if 6 <= s <= 12)
        seg_acc   = good_segs / len(segs)
    else:
        seg_acc = 1.0
    seg_pts = seg_acc * 20

    avg_words_per_pause = (
        len(words) / total_detected if total_detected > 0 else float(len(words))
    )

    # ----- 4. Over/Under Penalty (10 %) -----------------------------------
    penalty_score = 1.0
    if avg_words_per_pause < 4:
        penalty_score = 0.3
    elif avg_words_per_pause > 18:
        penalty_score = 0.3
    elif avg_words_per_pause > 15:
        penalty_score = 0.6
    elif avg_words_per_pause < 5:
        penalty_score = 0.6

    if expected_pauses > 0:
        ratio_vs_expected = total_detected / expected_pauses
        if ratio_vs_expected < 0.3 or ratio_vs_expected > 2.5:
            penalty_score = min(penalty_score, 0.4)

    penalty_pts = penalty_score * 10

    # ----- Final pause score ----------------------------------------------
    pause_score = int(round(placement_pts + mandatory_pts + seg_pts + penalty_pts))
    pause_score = max(0, min(100, pause_score))

    # ----- Comma misses (for user-facing report) --------------------------
    n_optional  = len(optional_zones)
    comma_hit   = sum(
        1 for z in optional_zones
        if any(abs(p - z) <= 1 for p in detected)
    )
    comma_missed = n_optional - comma_hit

    # ----- Status ---------------------------------------------------------
    if pause_score >= 80:
        pause_status   = "Good"
        pause_feedback = "Your pauses are well timed and naturally placed."
    elif pause_score >= 60:
        pause_status   = "Average"
        pause_feedback = (
            "Your pausing rhythm is developing. "
            "Try to pause at sentence boundaries and after commas."
        )
    else:
        pause_status   = "Needs Adjustment"
        pause_feedback = (
            "Work on pausing at natural linguistic breaks — especially "
            "after periods and commas — to improve clarity."
        )

    return {
        "score": pause_score,
        "status": pause_status,
        "feedback": pause_feedback,
        # Report-card summary numbers
        "avg_words_per_pause": round(avg_words_per_pause, 1),
        "total_pauses": total_detected,
        "expected_pauses": expected_pauses,
        "mandatory_pause_count": n_mandatory,
        "mandatory_pauses_hit": mandatory_hit,
        "mandatory_pauses_missed": mandatory_missed,
        "comma_pauses_missed": comma_missed,
        "mandatory_covered": mandatory_missed == 0,
        # Component breakdown (percentages)
        "placement_accuracy": round(placement_acc * 100, 1),
        "mandatory_compliance": round(mandatory_compliance * 100, 1),
        "segment_accuracy": round(seg_acc * 100, 1),
        "penalty_pct": round(penalty_score * 100, 1),
        # backward-compat alias
        "pause_words_interval": round(avg_words_per_pause, 2),
    }


def _load_prompt_bank() -> dict:
    """Load prompt bank from JSON file on first call (module-level cache)."""
    global _PROMPT_BANK
    if _PROMPT_BANK is not None:
        return _PROMPT_BANK
    prompts_file = Path(__file__).parent.parent / "data" / "pacing_practice_prompts.json"
    with open(prompts_file, "r", encoding="utf-8") as f:
        _PROMPT_BANK = json.load(f)
    return _PROMPT_BANK


def get_random_prompt(level: int) -> tuple[str, int]:
    """Return a randomly selected (prompt_text, prompt_index) for the given level."""
    bank = _load_prompt_bank()
    level_str = str(level)
    prompts: list[str] = bank.get(level_str, {}).get("prompts", [])
    if not prompts:
        raise ValueError(f"No prompts available for level {level}")
    prompt_index = random.randrange(len(prompts))
    return prompts[prompt_index], prompt_index


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _wpm_score(wpm: float) -> float:
    """Map WPM to a 0-100 component score.

    Ideal: 120-150 WPM → 100.
    Below 120: linearly decreases to 0 at 60 WPM.
    Above 150: linearly decreases to 0 at 210 WPM.
    """
    if 120 <= wpm <= 150:
        return 100.0
    elif wpm < 120:
        return max(0.0, (wpm - 60) / 60 * 100)
    else:
        return max(0.0, (210 - wpm) / 60 * 100)


def calculate_pacing_score(wpm: float, pause_score: float, filler_ratio: float) -> int:
    """Return a 0-100 composite score.

    Weights
    -------
    WPM          50 %
    Pause score  35 %  (linguistic 4-component scorer)
    Filler words 15 %
    """
    wpm_component    = _wpm_score(wpm) * 0.50
    pause_component  = pause_score * 0.35
    filler_component = _filler_score(filler_ratio) * 0.15
    return int(round(wpm_component + pause_component + filler_component))


# ---------------------------------------------------------------------------
# Metric building
# ---------------------------------------------------------------------------

def build_pacing_metrics(words: list[dict], prompt_text: str, transcript: str) -> dict:
    """Compute all pacing metrics from Whisper word-timestamp objects.

    Parameters
    ----------
    words:
        List of ``{"word": str, "start": float, "end": float}`` dicts.
    prompt_text:
        The original prompt sentence(s) the user read aloud.
        Used to derive expected punctuation pause zones.
    transcript:
        Plain-text transcription (used for filler word detection).

    Returns
    -------
    dict with keys: wpm, wpm_status, wpm_feedback, pause (dict), filler (dict),
                    score, pace_raw, pause_words_interval (backward-compat alias)
    """
    # --- WPM via existing service ---
    pace_raw = calculate_pace_metrics(words)
    if pace_raw is None:
        total_words = len(words)
        if total_words < 2:
            avg_wpm = 0.0
        else:
            duration_s = words[-1]["end"] - words[0]["start"]
            avg_wpm = (total_words / duration_s * 60) if duration_s > 0 else 0.0
        pace_raw = {"avg_wpm": avg_wpm}
    else:
        avg_wpm = pace_raw.get("avg_wpm", 0.0)

    if 120 <= avg_wpm <= 150:
        wpm_status   = "Good"
        wpm_feedback = "Your speaking pace is within the ideal range for interviews"
    elif avg_wpm < 120:
        wpm_status   = "Needs Adjustment"
        wpm_feedback = "Try speaking a little faster to maintain listener engagement"
    else:
        wpm_status   = "Needs Adjustment"
        wpm_feedback = "Slow down slightly to give your listener time to follow along"

    # --- Pause distribution (linguistic scorer) ---
    pause = score_pause_distribution(words, prompt_text)

    # --- Filler words ---
    filler = detect_filler_words(transcript, words)

    # --- Composite score ---
    score = calculate_pacing_score(avg_wpm, pause["score"], filler["filler_ratio"])

    return {
        "wpm": avg_wpm,
        "wpm_status": wpm_status,
        "wpm_feedback": wpm_feedback,
        "pause": pause,
        "filler": filler,
        "score": score,
        "pace_raw": pace_raw,
        # backward-compat flat field used by CRUD .update_with_analysis()
        "pause_words_interval": pause["pause_words_interval"],
        "pause_status": pause["status"],
        "pause_feedback": pause["feedback"],
    }


# ---------------------------------------------------------------------------
# Level unlock + readiness
# ---------------------------------------------------------------------------

def score_label(score: int) -> str:
    """Human-readable label for a numeric score."""
    if score >= 90:
        return "Excellent! Keep it up!"
    elif score >= 75:
        return "Good Progress! Keep Practicing"
    elif score >= 60:
        return "Almost there! A little more practice"
    else:
        return "Keep Practicing – you can do it!"


def get_level_statuses(level_bests: dict[int, Optional[int]]) -> list[dict]:
    """Return status dicts for all three levels given a user's best scores.

    Level 1 is always unlocked.
    Level 2 unlocks when Level 1 best >= UNLOCK_THRESHOLD.
    Level 3 unlocks when Level 2 best >= UNLOCK_THRESHOLD.
    """
    unlock_msgs = {
        1: f"Unlock level-2 at {UNLOCK_THRESHOLD}%",
        2: f"Unlock level-3 at {UNLOCK_THRESHOLD}%",
        3: "Complete all levels",
    }

    statuses = []
    for level in (1, 2, 3):
        meta = LEVEL_META[level]
        best = level_bests.get(level)

        # Determine if this level is accessible
        if level == 1:
            is_unlocked = True
        elif level == 2:
            is_unlocked = (level_bests.get(1) or 0) >= UNLOCK_THRESHOLD
        else:  # level == 3
            is_unlocked = (level_bests.get(2) or 0) >= UNLOCK_THRESHOLD

        if not is_unlocked:
            level_status = "locked"
        elif best is not None and best >= UNLOCK_THRESHOLD:
            level_status = "complete"
        else:
            level_status = "in_progress"

        statuses.append(
            {
                "level": level,
                "name": meta["name"],
                "description": meta["description"],
                "status": level_status,
                "best_score": best,
                "unlock_threshold": UNLOCK_THRESHOLD,
                "unlock_message": unlock_msgs[level],
            }
        )
    return statuses


def compute_overall_readiness(level_bests: dict[int, Optional[int]]) -> int:
    """Return 0-100 overall readiness percentage.

    Each level contributes equally (33.33 %).  Within a level the contribution
    is ``min(best, UNLOCK_THRESHOLD) / UNLOCK_THRESHOLD * 33.33``.
    """
    total = 0.0
    per_level = 100.0 / 3
    for level in (1, 2, 3):
        best = level_bests.get(level)
        if best is not None:
            capped = min(best, UNLOCK_THRESHOLD)
            total += (capped / UNLOCK_THRESHOLD) * per_level
    return int(round(total))
