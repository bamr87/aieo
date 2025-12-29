"""Scoring engine for AIEO patterns."""
from typing import Dict, List, Optional
import re
from datetime import datetime
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from .content_parser import ContentParser


class ScoringEngine:
    """Score content against AIEO patterns."""
    
    def __init__(self):
        self.parser = ContentParser()
        # Load spaCy model for NER (will need to download: python -m spacy download en_core_web_sm)
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except (OSError, IOError):
                # Fallback if model not installed
                self.nlp = None
    
    def score(self, content: str, format: str = "markdown") -> Dict:
        """
        Score content and return comprehensive results.
        
        Returns:
            Dictionary with score, grade, gaps, and pattern scores
        """
        # Parse content
        parsed = self.parser.parse(content, format)
        
        # Score each pattern
        pattern_scores = {}
        pattern_scores["structured_data"] = self._score_structured_data(parsed)
        pattern_scores["entity_density"] = self._score_entity_density(parsed)
        pattern_scores["citation_hooks"] = self._score_citation_hooks(parsed)
        pattern_scores["recursive_depth"] = self._score_recursive_depth(parsed)
        pattern_scores["temporal_anchoring"] = self._score_temporal_anchoring(parsed)
        pattern_scores["comparison_tables"] = self._score_comparison_tables(parsed)
        pattern_scores["definitional_precision"] = self._score_definitional_precision(parsed)
        pattern_scores["procedural_clarity"] = self._score_procedural_clarity(parsed)
        pattern_scores["faq_injection"] = self._score_faq_injection(parsed)
        pattern_scores["meta_context"] = self._score_meta_context(parsed)
        
        # Calculate total score
        total_score = self._calculate_total_score(pattern_scores, parsed)
        
        # Generate grade
        grade = self._score_to_grade(total_score)
        
        # Generate gaps
        gaps = self._generate_gaps(pattern_scores, parsed, total_score)
        
        # Detect anti-patterns
        anti_pattern_penalties = self._detect_anti_patterns(parsed)
        final_score = max(0, total_score - anti_pattern_penalties)
        final_grade = self._score_to_grade(final_score)
        
        return {
            "score": final_score,
            "grade": final_grade,
            "pattern_scores": pattern_scores,
            "gaps": gaps,
            "anti_pattern_penalties": anti_pattern_penalties,
            "word_count": parsed["word_count"],
        }
    
    def _score_structured_data(self, parsed: Dict) -> Dict:
        """Pattern 1: Structured Data (tables, lists, headers)."""
        word_count = parsed["word_count"]
        if word_count == 0:
            return {"score": 0, "max": 20, "detected": False}
        
        # Count structured elements per 500 words
        tables = len(parsed["tables"])
        lists = len(parsed["lists"])
        headers = len(parsed["headers"])
        
        elements_per_500 = ((tables + lists + headers) / word_count) * 500
        
        # Score: 20 points max, target 2+ elements per 500 words
        score = min(20, (elements_per_500 / 2) * 20)
        
        return {
            "score": round(score, 1),
            "max": 20,
            "detected": elements_per_500 >= 1,
            "tables": tables,
            "lists": lists,
            "headers": headers,
        }
    
    def _score_entity_density(self, parsed: Dict) -> Dict:
        """Pattern 2: Entity Density (named entities per 100 words)."""
        word_count = parsed["word_count"]
        if word_count == 0 or self.nlp is None:
            return {"score": 0, "max": 15, "detected": False}
        
        # Extract entities using spaCy
        doc = self.nlp(parsed["text"])
        entities = [ent.text for ent in doc.ents]
        entity_count = len(set(entities))  # Unique entities
        
        # Entities per 100 words
        entities_per_100 = (entity_count / word_count) * 100
        
        # Score: 15 points max, target 3+ entities per 100 words
        score = min(15, (entities_per_100 / 3) * 15)
        
        return {
            "score": round(score, 1),
            "max": 15,
            "detected": entities_per_100 >= 2,
            "entity_count": entity_count,
            "entities_per_100": round(entities_per_100, 1),
        }
    
    def _score_citation_hooks(self, parsed: Dict) -> Dict:
        """Pattern 3: Citation Hooks (explicit source attributions)."""
        text = parsed["text"].lower()
        
        # Citation patterns
        citation_patterns = [
            r"according to",
            r"research (from|by|at)",
            r"study (found|shows|indicates)",
            r"\[.*\]\(.*\)",  # Markdown links
            r"source:",
            r"references?:",
        ]
        
        citation_count = sum(len(re.findall(pattern, text)) for pattern in citation_patterns)
        
        # Score: 10 points max, target 2+ citations per 1000 words
        word_count = parsed["word_count"]
        citations_per_1000 = (citation_count / word_count) * 1000 if word_count > 0 else 0
        score = min(10, (citations_per_1000 / 2) * 10)
        
        return {
            "score": round(score, 1),
            "max": 10,
            "detected": citation_count > 0,
            "citation_count": citation_count,
        }
    
    def _score_recursive_depth(self, parsed: Dict) -> Dict:
        """Pattern 4: Recursive Depth (nested Q&A, follow-up questions)."""
        text = parsed["text"]
        
        # Detect questions
        question_pattern = r"\?[^?]*\?"
        questions = re.findall(question_pattern, text)
        
        # Detect nested structures (questions within answers)
        nested_pattern = r"(what|how|why|when|where|which).*\?.*(but|however|additionally|furthermore|moreover)"
        nested_count = len(re.findall(nested_pattern, text, re.IGNORECASE))
        
        # Score: 15 points max
        question_score = min(7.5, len(questions) * 1.5)
        nested_score = min(7.5, nested_count * 2.5)
        score = question_score + nested_score
        
        return {
            "score": round(score, 1),
            "max": 15,
            "detected": len(questions) > 0 or nested_count > 0,
            "question_count": len(questions),
            "nested_count": nested_count,
        }
    
    def _score_temporal_anchoring(self, parsed: Dict) -> Dict:
        """Pattern 5: Temporal Anchoring (dates, versions, freshness)."""
        text = parsed["text"]
        
        # Date patterns
        date_patterns = [
            r"\d{4}",  # Years
            r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}",
            r"as of",
            r"updated",
            r"version\s+\d+",
            r"v\d+\.\d+",
        ]
        
        date_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in date_patterns)
        
        # Score: 10 points max
        score = min(10, date_count * 2)
        
        return {
            "score": round(score, 1),
            "max": 10,
            "detected": date_count > 0,
            "date_count": date_count,
        }
    
    def _score_comparison_tables(self, parsed: Dict) -> Dict:
        """Pattern 6: Comparison Tables."""
        tables = parsed["tables"]
        text = parsed["text"].lower()
        
        # Check for comparison keywords
        comparison_keywords = ["vs", "versus", "compare", "comparison", "difference", "better", "worse"]
        has_comparison_keywords = any(keyword in text for keyword in comparison_keywords)
        
        # Score: 15 points max
        table_score = min(10, len(tables) * 5)
        keyword_score = 5 if has_comparison_keywords else 0
        score = table_score + keyword_score
        
        return {
            "score": round(score, 1),
            "max": 15,
            "detected": len(tables) > 0 or has_comparison_keywords,
            "table_count": len(tables),
            "has_comparison_keywords": has_comparison_keywords,
        }
    
    def _score_definitional_precision(self, parsed: Dict) -> Dict:
        """Pattern 7: Definitional Precision (explicit definitions)."""
        text = parsed["text"]
        
        # Definition patterns
        definition_patterns = [
            r"is defined as",
            r"means",
            r"refers to",
            r"is a",
            r"is an",
            r"\*\*.*\*\*.*is",  # Bold term followed by "is"
        ]
        
        definition_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in definition_patterns)
        
        # Score: 10 points max
        score = min(10, definition_count * 2)
        
        return {
            "score": round(score, 1),
            "max": 10,
            "detected": definition_count > 0,
            "definition_count": definition_count,
        }
    
    def _score_procedural_clarity(self, parsed: Dict) -> Dict:
        """Pattern 8: Step-by-Step Procedures."""
        text = parsed["text"]
        lists = parsed["lists"]
        
        # Step patterns
        step_patterns = [
            r"step\s+\d+",
            r"step\s+[a-z]",
            r"first.*second.*third",
            r"\d+\.\s+",  # Numbered list items
        ]
        
        step_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in step_patterns)
        
        # Ordered lists also count
        ordered_lists = [lst for lst in lists if lst["type"] == "ordered"]
        list_items = sum(lst["item_count"] for lst in ordered_lists)
        
        # Score: 5 points max
        step_score = min(3, step_count * 0.5)
        list_score = min(2, min(list_items / 5, 2))
        score = step_score + list_score
        
        return {
            "score": round(score, 1),
            "max": 5,
            "detected": step_count > 0 or len(ordered_lists) > 0,
            "step_count": step_count,
            "ordered_list_count": len(ordered_lists),
        }
    
    def _score_faq_injection(self, parsed: Dict) -> Dict:
        """Pattern 9: FAQ Injection."""
        text = parsed["text"]
        headers = parsed["headers"]
        
        # FAQ section detection
        faq_patterns = [
            r"frequently asked questions",
            r"faq",
            r"common questions",
        ]
        
        has_faq_section = any(re.search(pattern, text, re.IGNORECASE) for pattern in faq_patterns)
        
        # Questions in headers
        question_headers = [h for h in headers if "?" in h["text"]]
        
        # Score: 15 points max
        section_score = 10 if has_faq_section else 0
        header_score = min(5, len(question_headers) * 1)
        score = section_score + header_score
        
        return {
            "score": round(score, 1),
            "max": 15,
            "detected": has_faq_section or len(question_headers) > 0,
            "has_faq_section": has_faq_section,
            "question_header_count": len(question_headers),
        }
    
    def _score_meta_context(self, parsed: Dict) -> Dict:
        """Pattern 10: Meta-Context (importance explanations)."""
        text = parsed["text"]
        
        # Importance phrases
        importance_patterns = [
            r"this is important because",
            r"this is critical because",
            r"this matters because",
            r"significantly",
            r"crucially",
            r"essential",
        ]
        
        importance_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in importance_patterns)
        
        # Score: 10 points max (but this is low priority)
        score = min(10, importance_count * 2)
        
        return {
            "score": round(score, 1),
            "max": 10,
            "detected": importance_count > 0,
            "importance_count": importance_count,
        }
    
    def _calculate_total_score(self, pattern_scores: Dict, parsed: Dict) -> float:
        """Calculate total score from pattern scores."""
        # Weights from PRD Section 8
        weights = {
            "structured_data": 20,
            "comparison_tables": 15,
            "recursive_depth": 15,
            "entity_density": 15,
            "temporal_anchoring": 10,
            "citation_hooks": 10,
            "definitional_precision": 10,
            "procedural_clarity": 5,
            "faq_injection": 15,  # Added to match PRD
            "meta_context": 10,  # Added to match PRD
        }
        
        total = 0
        for pattern, score_data in pattern_scores.items():
            if pattern in weights:
                # Normalize score to weight
                max_score = score_data.get("max", weights[pattern])
                score = score_data.get("score", 0)
                normalized = (score / max_score) * weights[pattern] if max_score > 0 else 0
                total += normalized
        
        return round(total, 1)
    
    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"
    
    def _generate_gaps(self, pattern_scores: Dict, parsed: Dict, total_score: float) -> List[Dict]:
        """Generate gap analysis."""
        gaps = []
        
        gap_categories = {
            "structured_data": {
                "category": "structure",
                "severity": "high",
                "description": "Missing structured data (tables, lists, headers)",
            },
            "comparison_tables": {
                "category": "comparison",
                "severity": "high",
                "description": "No comparison tables found",
            },
            "recursive_depth": {
                "category": "recursion",
                "severity": "high",
                "description": "Missing recursive depth (nested Q&A)",
            },
            "entity_density": {
                "category": "entities",
                "severity": "medium",
                "description": "Low entity density",
            },
            "temporal_anchoring": {
                "category": "temporal",
                "severity": "medium",
                "description": "Missing temporal anchors (dates, versions)",
            },
            "citation_hooks": {
                "category": "citations",
                "severity": "medium",
                "description": "Missing citation hooks",
            },
            "definitional_precision": {
                "category": "definition",
                "severity": "low",
                "description": "Missing explicit definitions",
            },
            "procedural_clarity": {
                "category": "procedural",
                "severity": "low",
                "description": "Missing step-by-step procedures",
            },
            "faq_injection": {
                "category": "faq",
                "severity": "medium",
                "description": "Missing FAQ section",
            },
            "meta_context": {
                "category": "meta",
                "severity": "low",
                "description": "Missing meta-context explanations",
            },
        }
        
        for pattern, score_data in pattern_scores.items():
            if not score_data.get("detected", False) and pattern in gap_categories:
                gap_info = gap_categories[pattern]
                gaps.append({
                    "id": f"gap_{pattern}",
                    "category": gap_info["category"],
                    "severity": gap_info["severity"],
                    "description": gap_info["description"],
                    "location": {"start": 0, "end": 100},
                    "example_fix": f"Add {pattern.replace('_', ' ')} to improve score",
                })
        
        # Sort by severity (high > medium > low)
        severity_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda x: severity_order.get(x["severity"], 3))
        
        return gaps
    
    def _detect_anti_patterns(self, parsed: Dict) -> int:
        """Detect anti-patterns and return penalty points."""
        penalties = 0
        text = parsed["text"].lower()
        word_count = parsed["word_count"]
        
        # Over-optimization: Too many patterns in small space
        if word_count > 0:
            pattern_density = (
                len(parsed["tables"]) + len(parsed["lists"]) + len(parsed["headers"])
            ) / word_count * 1000
            if pattern_density > 10:  # More than 10 patterns per 1000 words
                penalties += 20
        
        # Keyword stuffing: Repeated phrases
        words = text.split()
        if len(words) > 0:
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Only check longer words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Check for excessive repetition
            for word, count in word_freq.items():
                if count > len(words) * 0.05:  # Word appears >5% of the time
                    penalties += 15
                    break
        
        # Missing structure in long content
        if word_count > 1000 and len(parsed["tables"]) == 0 and len(parsed["lists"]) == 0:
            penalties += 15
        
        return penalties


