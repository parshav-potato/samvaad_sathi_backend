def calculate_pace_metrics(words):
    """
    Calculates detailed pace metrics from a list of word timestamps.

    Args:
        words (list): List of dicts, each with 'start', 'end', and 'word' keys representing word timings.

    Returns:
        dict: {
            'avg_wpm': float,         # Average words per minute
            'too_slow_pct': float,    # Percentage of time speaking too slow (<105 WPM)
            'ideal_pct': float,       # Percentage of time at ideal pace (105-170 WPM)
            'too_fast_pct': float,    # Percentage of time speaking too fast (>170 WPM)
            'segments': list          # List of segments with pace classification and text
        }
        or None if insufficient data.
    """
    # Handle invalid words and zero-duration words
    valid_words = []
    for w in words:
        start, end = w['start'], w['end']
        if end <= start:
            end = start + 0.01  # Add minimal duration
        valid_words.append({'start': start, 'end': end, 'word': w['word']})
    
    if not valid_words:
        return None
    
    # Calculate average WPM
    total_words = len(valid_words)
    first_start = min(w['start'] for w in valid_words)
    last_end = max(w['end'] for w in valid_words)
    total_time = last_end - first_start
    if total_time <= 0:
        return None
    
    avg_wpm = (total_words / total_time) * 60

    # Initialize counters for pace classification
    too_slow_sec = 0.0
    ideal_sec = 0.0
    too_fast_sec = 0.0
    total_windows = 0
    
    # Initialize segment tracking
    segments = []
    current_start = first_start
    current_label = None
    
    # Use 5-second sliding windows with 1-second step
    current = first_start
    while current <= last_end - 5:
        window_start = current
        window_end = current + 5
        window_duration = 5.0
        
        # Count words in this window
        word_count = 0
        for w in valid_words:
            # Check if word overlaps with window
            if w['start'] < window_end and w['end'] > window_start:
                word_count += 1
        
        # Calculate WPM for this window
        wpm = (word_count / window_duration) * 60
        
        # Classify pace
        if wpm < 105:
            label = 'too_slow'
            too_slow_sec += 1
        elif 105 <= wpm <= 170:
            label = 'ideal'
            ideal_sec += 1
        elif wpm > 170:
            label = 'too_fast'
            too_fast_sec += 1
        
        # Track segments
        if label != current_label:
            if current_label:  # Finalize previous segment
                segments.append({
                    'start': current_start,
                    'end': current,
                    'label': current_label,
                    'text': get_text_in_interval(valid_words, current_start, current)
                })
            current_start = current
            current_label = label
        
        total_windows += 1
        current += 1  # Move to next window
    
    # Finalize last segment
    if current_label:
        segments.append({
            'start': current_start,
            'end': last_end,
            'label': current_label,
            'text': get_text_in_interval(valid_words, current_start, last_end)
        })
    
    # Calculate percentages
    if total_windows > 0:
        too_slow_pct = (too_slow_sec / total_windows) * 100
        ideal_pct = (ideal_sec / total_windows) * 100
        too_fast_pct = (too_fast_sec / total_windows) * 100
    else:
        too_slow_pct = ideal_pct = too_fast_pct = 0
    
    return {
        'avg_wpm': round(avg_wpm, 1),
        'too_slow_pct': round(too_slow_pct, 1),
        'ideal_pct': round(ideal_pct, 1),
        'too_fast_pct': round(too_fast_pct, 1),
        'segments': segments
    }

def get_text_in_interval(words, start_time, end_time):
    """Extract text from words overlapping with the time interval"""
    words_in_interval = []
    for w in words:
        if w['end'] > start_time and w['start'] < end_time:
            words_in_interval.append(w)
    
    # Sort by start time and extract text
    words_in_interval.sort(key=lambda x: x['start'])
    return " ".join(w['word'] for w in words_in_interval)

def format_time(seconds):
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def provide_pace_feedback(input_dict):
    """Generate pacing feedback and a numerical score.

    Args:
        input_dict (dict): Transcript dict as produced by Whisper (expects
            a "words" key with word-level timestamps).

    Returns:
        dict: {
            "feedback": str,   # Human-readable feedback paragraph
            "score": float     # 0-100 pacing score (higher is better)
        }
    """
    if input_dict.get('words_timestamp',None) is not None:
        input_dict = input_dict['words_timestamp']
        
    words = input_dict.get('words', [])
    
    # preprocess
    # Remove elements without 'start' or 'end' keys
    words = [w for w in words if 'start' in w and 'end' in w]
    if len(words)<1:
        return {
            "feedback": "len(words) less than 1",
            "score": -1
        }
    # Calculate metrics and segments
    result = calculate_pace_metrics(words)
    if not result:
        return "Insufficient data for pace analysis"
    
    # Prepare feedback text
    feedback = "Quantitative Feedback:\n"
    feedback += f"Words Per Minute (WPM): Your average pace: {result['avg_wpm']} WPM\n"
    feedback += "Benchmarking: Aim for 120-150 WPM in interviews\n\n"
    
    feedback += "Pace Range Classification:\n"
    feedback += f"- Too Slow: Your pace was slow {result['too_slow_pct']}% of the time\n"
    feedback += f"- Ideal: You spoke at ideal pace for {result['ideal_pct']}% of the time\n"
    feedback += f"- Too Fast: Your pace exceeded 170 WPM for {result['too_fast_pct']}% of the time\n\n"
    
    # Add detailed segments
    feedback += "Detailed Pace Segments:\n"
    
    # Group segments by type
    segment_types = {
        'too_slow': [],
        'ideal': [],
        'too_fast': []
    }
    
    for seg in result['segments']:
        if seg['label'] in segment_types:
            segment_types[seg['label']].append(seg)
    
    # Format each segment type
    for label, segments in segment_types.items():
        if not segments:
            continue
            
        feedback += f"\n{label.capitalize().replace('_', ' ')} segments:\n"
        for seg in segments:
            start_time = format_time(seg['start'])
            end_time = format_time(seg['end'])
            feedback += f"- [{start_time} - {end_time}]: {seg['text']}\n"
    
    # ------------------------------------------------------------
    # Scoring rubric
    # ------------------------------------------------------------
    # We evaluate pacing on two dimensions:
    #   1. Pace consistency – percentage of time spent in the ideal
    #      window (105-170 WPM). Worth 60 points.
    #        pace_consistency_score = ideal_pct * 0.6  (0-60)
    #   2. Average speed accuracy – how close the *average* WPM is
    #      to the recommended 120-150 WPM band. Worth 40 points.
    #         deviation = distance, in WPM, from the nearest bound
    #         accuracy_score = max(0, 40 - 2 * deviation)
    #         (we lose 2 points for every WPM outside the band)
    #   Total possible = 100. We clip the final score to [0, 100].

    # Calculate score components
    # 1. Pace consistency
    pace_consistency_score = result['ideal_pct'] * 0.6  # 0-60

    # 2. Average speed accuracy
    recommended_min, recommended_max = 120, 150
    avg_wpm = result['avg_wpm']
    if recommended_min <= avg_wpm <= recommended_max:
        accuracy_score = 40.0
    else:
        # deviation outside the recommended range
        if avg_wpm < recommended_min:
            deviation = recommended_min - avg_wpm
        else:
            deviation = avg_wpm - recommended_max
        accuracy_score = max(0.0, 40.0 - 2.0 * deviation)

    total_score = pace_consistency_score + accuracy_score
    # Ensure the score is between 0 and 100
    total_score = max(0.0, min(100.0, total_score))
    total_score /= 20
    total_score = round(total_score,1)
    
    return {
        "feedback": feedback,
        "score": total_score,
        'wpm':avg_wpm,
    }