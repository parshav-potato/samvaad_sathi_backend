"""Service layer for speech pacing practice.

Responsibilities
----------------
* Load and vend prompts from the static JSON bank.
* Compute WPM and pause-distribution metrics from Whisper word timestamps.
* Score a single attempt (0-100) based on WPM and pause interval targets.
* Derive level unlock status and overall readiness from persisted best scores.
"""

import json
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
        # 60 → 0, 120 → 100
        return max(0.0, (wpm - 60) / 60 * 100)
    else:
        # 150 → 100, 210 → 0
        return max(0.0, (210 - wpm) / 60 * 100)


def _pause_score(interval: float) -> float:
    """Map average-words-between-pauses to a 0-100 component score.

    Ideal: 8-12 words between pauses → 100.
    Below 8: too many pauses; linearly decreases to 0 at 2 words.
    Above 12: too few pauses; linearly decreases to 0 at 24 words.
    """
    if 8 <= interval <= 12:
        return 100.0
    elif interval < 8:
        return max(0.0, (interval - 2) / 6 * 100)
    else:
        return max(0.0, (24 - interval) / 12 * 100)


def calculate_pacing_score(wpm: float, pause_words_interval: float) -> int:
    """Return a 0-100 composite score (WPM 60 %, pause 40 %)."""
    wpm_component = _wpm_score(wpm) * 0.60
    pause_component = _pause_score(pause_words_interval) * 0.40
    return int(round(wpm_component + pause_component))


# ---------------------------------------------------------------------------
# Metric building
# ---------------------------------------------------------------------------

def _compute_avg_pause_interval(words: list[dict]) -> float:
    """Compute average number of words between detected pauses (gaps > 0.3 s).

    Returns the total word count when no pauses are found (i.e. no natural
    breaks detected), which is a signal that the speaker never paused.
    """
    PAUSE_THRESHOLD_S = 0.3
    pause_count = 0
    for i in range(len(words) - 1):
        gap = words[i + 1].get("start", 0) - words[i].get("end", 0)
        if gap >= PAUSE_THRESHOLD_S:
            pause_count += 1

    if pause_count == 0:
        # Treat the entire utterance as one continuous segment
        return float(len(words))

    return len(words) / pause_count


def build_pacing_metrics(words: list[dict]) -> dict:
    """Compute all pacing metrics from Whisper word-timestamp objects.

    Parameters
    ----------
    words:
        List of ``{"word": str, "start": float, "end": float}`` dicts.

    Returns
    -------
    dict with keys:
        wpm, pause_words_interval, score,
        wpm_status, wpm_feedback,
        pause_status, pause_feedback,
        pace_raw (full output of calculate_pace_metrics)
    """
    # --- WPM via existing service ---
    pace_raw = calculate_pace_metrics(words)
    if pace_raw is None:
        # Fallback: compute crude average from word timestamps
        total_words = len(words)
        if total_words < 2:
            avg_wpm = 0.0
        else:
            duration_s = words[-1]["end"] - words[0]["start"]
            avg_wpm = (total_words / duration_s * 60) if duration_s > 0 else 0.0
        pace_raw = {"avg_wpm": avg_wpm}
    else:
        avg_wpm = pace_raw.get("avg_wpm", 0.0)

    # --- Pause interval ---
    avg_pause_interval = _compute_avg_pause_interval(words)

    # --- Derive statuses and feedback ---
    if 120 <= avg_wpm <= 150:
        wpm_status = "Good"
        wpm_feedback = "Your speaking pace is within the ideal range for interviews"
    elif avg_wpm < 120:
        wpm_status = "Needs Adjustment"
        wpm_feedback = "Try speaking a little faster to maintain listener engagement"
    else:
        wpm_status = "Needs Adjustment"
        wpm_feedback = "Slow down slightly to give your listener time to follow along"

    if 8 <= avg_pause_interval <= 12:
        pause_status = "Good"
        pause_feedback = "Your pause frequency is well-suited for interview conversations"
    elif avg_pause_interval < 8:
        pause_status = "Needs Adjustment"
        pause_feedback = "You are pausing very frequently – try to connect thoughts more smoothly"
    else:
        pause_status = "Needs Adjustment"
        pause_feedback = "Try pausing more frequently to give your listener time to process"

    score = calculate_pacing_score(avg_wpm, avg_pause_interval)

    return {
        "wpm": avg_wpm,
        "pause_words_interval": avg_pause_interval,
        "score": score,
        "wpm_status": wpm_status,
        "wpm_feedback": wpm_feedback,
        "pause_status": pause_status,
        "pause_feedback": pause_feedback,
        "pace_raw": pace_raw,
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
