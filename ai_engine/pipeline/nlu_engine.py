import re
from typing import List, Dict, Optional


class NLUEngine:
    def __init__(self):
        # Common keywords patterns (can be extended)
        self.keyword_patterns = {
            "time": r"(\d{1,2}[点时:]\d{1,2}[分]?)|([上下]午)|([明昨今]天)|(周[一二三四五六日天])",
            "location": r"(在|到|去|从)([^\s,，。.！!？?]{2,8})",
            "number": r"\d+",
            "phone": r"1[3-9]\d{9}",
        }

        # Intent patterns
        self.intent_patterns = {
            "greeting": r"^(你好|您好|嗨|hi|hello)",
            "farewell": r"^(再见|拜拜|bye|goodbye)",
            "question": r"(什么|怎么|为什么|哪里|谁|几|多少|吗|呢|？|\?)",
            "request": r"(请|帮忙|能不能|可以|麻烦)",
            "complaint": r"(投诉|不满|太差|垃圾|骗人)",
            "emergency": r"(救命|紧急|报警|火灾|事故|抢劫)",
        }

    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        keywords = []

        # Pattern-based extraction
        for category, pattern in self.keyword_patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    keywords.extend([m for m in match if m])
                else:
                    keywords.append(match)

        # Remove duplicates and empty strings
        keywords = list(set([kw.strip() for kw in keywords if kw.strip()]))

        return keywords

    def classify_intent(self, text: str) -> str:
        """Classify intent from text"""
        text_lower = text.lower()

        for intent, pattern in self.intent_patterns.items():
            if re.search(pattern, text_lower):
                return intent

        return "other"

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text"""
        entities = {}

        # Time entities
        time_matches = re.findall(self.keyword_patterns["time"], text)
        if time_matches:
            entities["time"] = [m for match in time_matches for m in match if m]

        # Location entities
        loc_matches = re.findall(self.keyword_patterns["location"], text)
        if loc_matches:
            entities["location"] = [m[1] for m in loc_matches]

        # Phone numbers
        phone_matches = re.findall(self.keyword_patterns["phone"], text)
        if phone_matches:
            entities["phone"] = phone_matches

        return entities

    def analyze(self, text: str) -> dict:
        """
        Perform NLU analysis on text.

        Args:
            text: Input text

        Returns:
            {
                "keywords": ["keyword1", "keyword2"],
                "intent": "greeting",
                "entities": {"time": [...], "location": [...]}
            }
        """
        return {
            "keywords": self.extract_keywords(text),
            "intent": self.classify_intent(text),
            "entities": self.extract_entities(text),
        }


# Singleton instance
_nlu_engine: Optional[NLUEngine] = None


def get_nlu_engine() -> NLUEngine:
    global _nlu_engine
    if _nlu_engine is None:
        _nlu_engine = NLUEngine()
    return _nlu_engine
