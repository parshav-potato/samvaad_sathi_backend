import re
import pydantic

class KnowledgeQuestionLevel(pydantic.BaseModel):
    level: int
    questions: list[str]

class KnowledgeQuestionTopic(pydantic.BaseModel):
    topicName: str
    candidateType: str
    levels: list[KnowledgeQuestionLevel]

class KnowledgeBaseExtraction(pydantic.BaseModel):
    topics: list[KnowledgeQuestionTopic]


def parse_knowledge_base_text(text: str) -> tuple[KnowledgeBaseExtraction | None, str | None, int | None, str]:
    """
    Parses a raw knowledge base text string using heuristic regular expressions.
    Returns the structured extraction, error, latency, and the model (which is now 'heuristic-parser').
    """
    import time
    start_time = time.perf_counter()

    topics = []
    
    current_topic_name = "General"
    current_candidate_type = "General"
    current_level_num = 1
    
    # State maps to build the output structure
    # topics_map[topic_name] = { candidateType: str, levels: { level_num: [questions] } }
    topics_map = {}
    
    def ensure_topic(topic_name, candidate_type):
        if topic_name not in topics_map:
            topics_map[topic_name] = {
                "candidateType": candidate_type,
                "levels": {}
            }
        # Update candidate type if we found a more specific one
        if candidate_type != "General" and topics_map[topic_name]["candidateType"] == "General":
             topics_map[topic_name]["candidateType"] = candidate_type

    def add_question(topic_name, candidate_type, level_num, question_text):
        ensure_topic(topic_name, candidate_type)
        if level_num not in topics_map[topic_name]["levels"]:
            topics_map[topic_name]["levels"][level_num] = []
        topics_map[topic_name]["levels"][level_num].append(question_text)

    # Split text by lines
    lines = text.split('\n')
    
    # Regex patterns
    topic_pattern = re.compile(r'^(?:Domain|Topic)\s*[\:\-]?\s*(.+)$', re.IGNORECASE)
    candidate_pattern = re.compile(r'^Candidate(?: Type)?\s*[\:\-]?\s*(.+)$', re.IGNORECASE)
    level_pattern = re.compile(r'^Level\s*[\:\-]?\s*(\d+)', re.IGNORECASE)
    question_start_pattern = re.compile(r'^\d+[\.\)]\s*(.+)$')
    
    last_added_topic = current_topic_name
    last_added_level = current_level_num
    
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue
            
        # Check for Domain / Topic
        topic_match = topic_pattern.match(stripped_line)
        if topic_match:
            current_topic_name = topic_match.group(1).strip()
            ensure_topic(current_topic_name, current_candidate_type)
            continue
            
        # Check for Candidate Type
        candidate_match = candidate_pattern.match(stripped_line)
        if candidate_match:
            current_candidate_type = candidate_match.group(1).strip()
            ensure_topic(current_topic_name, current_candidate_type)
            continue
            
        # Check for Level
        level_match = level_pattern.match(stripped_line)
        if level_match:
            try:
                current_level_num = int(level_match.group(1))
            except ValueError:
                pass
            continue
            
        # Check for Question
        question_match = question_start_pattern.match(stripped_line)
        if question_match:
            question_text = question_match.group(1).strip()
            add_question(current_topic_name, current_candidate_type, current_level_num, question_text)
            last_added_topic = current_topic_name
            last_added_level = current_level_num
            continue
            
        # If the line doesn't match a new heading, and we've added a question previously,
        # it might be a multi-line question continuation.
        if last_added_topic in topics_map and last_added_level in topics_map[last_added_topic]["levels"]:
            q_list = topics_map[last_added_topic]["levels"][last_added_level]
            if q_list:
                q_list[-1] = q_list[-1] + " " + stripped_line

    # Convert the map into the required Pydantic models
    final_topics = []
    for t_name, t_data in topics_map.items():
        levels_list = []
        for l_num, q_list in t_data["levels"].items():
            if q_list: # Only add levels that actually have questions
                levels_list.append(KnowledgeQuestionLevel(level=l_num, questions=q_list))
        
        if levels_list: # Only add topics that actually have levels with questions
            final_topics.append(KnowledgeQuestionTopic(
                topicName=t_name,
                candidateType=t_data["candidateType"],
                levels=levels_list
            ))
            
    result = KnowledgeBaseExtraction(topics=final_topics)
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    return result, None, latency_ms, "heuristic-regex-parser"
