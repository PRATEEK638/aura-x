"""
Aura-X Intent Classifier
Rule-based intent and complexity classification for model routing.
"""

import re
from typing import Tuple, List, Dict
from core.logger import setup_logger

logger = setup_logger("aura_x.ai.intent")

INTENT_PATTERNS = {
    "automation": [
        r"\b(open|launch|start|run|execute|close)\b.*\b(app|application|program|browser|chrome|firefox|word|excel|notepad|terminal)\b",
        r"\b(click|press|type|drag|scroll|move)\b",
        r"\b(organize|sort|move|copy|delete|rename)\b.*\b(file|folder|directory)\b",
        r"\b(screenshot|capture|screen)\b",
        r"\b(create|make|new)\b.*\b(folder|directory|file)\b",
        r"\b(open|go to|navigate)\b.*\b(website|url|http|www\.)\b",
        r"\b(open|launch|start|close)\s+\w+\s*$",
    ],
    "coding": [
        r"\b(write|create|generate|build|code|script|function|class|program|algorithm)\b.*\b(code|script|python|javascript|java|c\+\+|html|css|sql)\b",
        r"\b(debug|fix|refactor|optimize|review)\b.*\b(code|function|script|error|bug)\b",
        r"\b(implement|develop)\b",
        r"```",
        r"\bdef \b|\bclass \b|\bimport \b",
        r"\b(api|endpoint|database|query|sql|http|rest|graphql)\b"
    ],
    "office": [
        r"\b(word|document|docx|doc)\b",
        r"\b(excel|spreadsheet|xlsx|csv|table|chart)\b",
        r"\b(powerpoint|presentation|slides|pptx|slide)\b",
        r"\b(create|make|write|edit|update|format)\b.*\b(document|report|letter|spreadsheet|presentation|slide)\b",
    ],
    "web": [
        r"\b(search|find|look up|google|bing)\b.*\b(web|internet|online)\b",
        r"\b(scrape|extract|parse)\b.*\b(website|page|url|web)\b",
        r"\b(download|fetch)\b.*\b(from|website|url)\b",
        r"https?://\S+",
    ],
    "screen": [
        r"\b(what|what's|describe)\b.*\b(screen|display|showing|visible)\b",
        r"\b(read|analyze|look at)\b.*\b(screen|window|page)\b",
        r"\b(current|active)\b.*\b(window|application|screen)\b"
    ],
    "system": [
        r"\b(system|memory|cpu|disk|storage|ram|process|task)\b.*\b(info|status|usage|monitor)\b",
        r"\b(shutdown|restart|sleep|hibernate)\b",
        r"\b(install|uninstall|update)\b.*\b(app|program|package|software)\b",
        r"\b(run|execute)\b.*\b(command|cmd|terminal|shell|bash|powershell)\b"
    ],
    "conversation": [
        r"\b(hello|hi|hey|good morning|good afternoon|how are you)\b",
        r"\b(thank|thanks|thank you)\b",
        r"\b(what can you|what do you|help me understand|explain)\b",
        r"\?$"
    ]
}

# Intent → model type mapping
INTENT_MODEL_MAP = {
    "automation": "fast",       # phi3 for quick commands
    "coding": "coding",         # qwen for code
    "office": "general",        # llama3 for planning
    "web": "general",
    "screen": "fast",           # phi3 for quick screen queries
    "system": "general",
    "conversation": "general",  # llama3 for smart conversation
    "unknown": "general"
}

# Priority order — first match with high score wins
INTENT_PRIORITY = ["automation", "coding", "system", "office", "web", "screen", "conversation"]


def classify_intent(text: str) -> Tuple[str, float]:
    """Returns (intent, confidence). Automation > coding > conversation."""
    text_lower = text.lower().strip()
    scores: dict = {}

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 1
        if score > 0:
            scores[intent] = score / len(patterns)

    if not scores:
        return ("conversation", 0.3)

    # Use priority order for tie-breaking
    for intent in INTENT_PRIORITY:
        if intent in scores and scores[intent] > 0.15:
            confidence = min(scores[intent] * 2.5, 1.0)
            return (intent, confidence)

    best = max(scores, key=scores.get)
    return (best, min(scores[best] * 2, 1.0))


def get_model_for_intent(intent: str) -> str:
    return INTENT_MODEL_MAP.get(intent, "general")





def analyze_complexity(text: str) -> str:
    """Estimate task complexity: simple, moderate, complex."""
    word_count = len(text.split())
    has_multi = len(re.findall(r'\band\b|\bthen\b|\balso\b|\bafter\b', text.lower())) > 1
    has_code = bool(re.search(r'```|def |class |import |function ', text))

    score = 0
    if word_count > 20: score += 1
    if word_count > 50: score += 1
    if has_multi: score += 1
    if has_code: score += 1

    if score <= 1:
        return "simple"
    elif score <= 2:
        return "moderate"
    return "complex"
