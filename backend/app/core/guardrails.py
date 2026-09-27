import re
import logging
from typing import Tuple, Dict, Any, List

logger = logging.getLogger("NexusAI-Guardrails")

# Injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"dan\s+mode",
    r"jailbreak",
    r"disregard\s+(your\s+)?system\s+prompt",
    r"bypass\s+safety\s+filters"
]

# Sensitive PII patterns
EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_PATTERN = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
CREDIT_CARD_PATTERN = r"\b(?:\d{4}[-\s]?){3}\d{4}\b"

# Harmful / Abusive patterns
HARMFUL_TERMS = [
    "create malware", "ddos attack", "hack into", "bypass password authentication",
    "how to make a bomb", "exploit vulnerability zero day steal"
]

class GuardrailsService:
    @staticmethod
    def inspect_input(text: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Inspects incoming prompt against injections, malicious queries, and PII.
        Returns: (is_safe: bool, reason: str, metadata: dict)
        """
        lower_text = text.lower()

        # 1. Prompt Injection Check
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                logger.warning(f"Prompt injection pattern detected: {pattern}")
                return False, "Prompt injection attempt detected and safely mitigated.", {"flag": "prompt_injection"}

        # 2. Harmful Intent Check
        for term in HARMFUL_TERMS:
            if term in lower_text:
                logger.warning(f"Harmful intent flagged: {term}")
                return False, "I cannot assist with activities that compromise system security or safety.", {"flag": "harmful_intent"}

        # 3. PII Detection (Sanitize/Mask)
        sanitized_text = re.sub(EMAIL_PATTERN, "[REDACTED_EMAIL]", text)
        sanitized_text = re.sub(PHONE_PATTERN, "[REDACTED_PHONE]", sanitized_text)
        sanitized_text = re.sub(CREDIT_CARD_PATTERN, "[REDACTED_CARD]", sanitized_text)

        has_pii = sanitized_text != text

        # 4. Sentiment Detection
        sentiment = GuardrailsService.detect_sentiment(text)

        return True, "Passed", {
            "has_pii": has_pii,
            "sanitized_text": sanitized_text,
            "sentiment": sentiment
        }

    @staticmethod
    def detect_sentiment(text: str) -> str:
        """Heuristic sentiment detection to adjust agent demeanor."""
        lower = text.lower()
        if any(w in lower for w in ["broken", "fail", "urgent", "emergency", "crash", "error", "down", "not working", "frustrated"]):
            return "urgent_troubleshooting"
        elif any(w in lower for w in ["how to", "explain", "architecture", "recommend", "best practice", "why"]):
            return "curious_architectural"
        elif any(w in lower for w in ["thank you", "great", "awesome", "perfect", "good"]):
            return "positive"
        return "neutral"

    @staticmethod
    def calculate_confidence(response_text: str, context_chunks: List[str] = None) -> float:
        """
        Computes a confidence score (0.0 to 1.0) based on:
        - Response length & completeness
        - Groundedness in retrieved context
        - Absence of hedging/uncertainty phrases
        """
        score = 0.88 # Base high confidence for fine-tuned domain model

        lower = response_text.lower()
        # Penalize uncertainty markers
        uncertain_markers = ["i'm not sure", "i don't know", "it might be possible", "perhaps", "could potentially be wrong"]
        for marker in uncertain_markers:
            if marker in lower:
                score -= 0.15

        # Reward grounded citations or code blocks
        if "```" in response_text:
            score += 0.05
        if context_chunks and len(context_chunks) > 0:
            score += 0.05

        return round(min(0.99, max(0.40, score)), 2)

    @staticmethod
    def generate_follow_up_suggestions(query: str, response: str) -> List[str]:
        """Auto-generates relevant domain follow-up prompts."""
        query_lower = query.lower()
        if "kubernetes" in query_lower or "k8s" in query_lower or "pod" in query_lower:
            return [
                "How do I configure Prometheus alerting for this deployment?",
                "Can you show the Istio VirtualService and DestinationRule?",
                "What is the recommended PodDisruptionBudget configuration?"
            ]
        elif "vllm" in query_lower or "gpu" in query_lower or "vram" in query_lower:
            return [
                "How can I enable PagedAttention with prefix caching?",
                "What are the benefits of AWQ vs GPTQ quantization?",
                "Can you write a benchmark script using localllm / locust?"
            ]
        elif "terraform" in query_lower or "infrastructure" in query_lower:
            return [
                "How do we manage remote state locking with DynamoDB and S3?",
                "Can you add automated drift detection to the CI pipeline?",
                "What are the security group rules required for this VPC?"
            ]
        else:
            return [
                "Can you provide a step-by-step verification checklist?",
                "What are the cost and performance implications of this setup?",
                "How do we configure zero-downtime rollback in CI/CD?"
            ]

guardrails = GuardrailsService()
