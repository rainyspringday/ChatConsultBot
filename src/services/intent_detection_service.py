class IntentDetectionService:
    """
    Scaled rule-based intent classifier for routing queries
    to the correct Chroma DB (frameworks vs economic reports).
    """

    def __init__(self):
        # --- DIRECT FRAMEWORK NAMES (your 6 frameworks) ---
        self.direct_frameworks = [
            "swot", "s.w.o.t",
            "porter", "five forces", "5 forces",
            "business model canvas", "bmc",
            "lean canvas",
            "mckinsey 7s", "7s", "7-s", "seven s",
            "blue ocean", "errc", "eliminate reduce raise create"
        ]

        # --- GENERIC FRAMEWORK INDICATORS ---
        # These catch ANY framework-like query
        self.generic_framework_indicators = [
            "framework", "model", "matrix", "analysis", "tool",
            "strategic", "strategy tool", "evaluation tool",
            "diagnostic tool", "business tool", "consulting tool",
            "methodology", "approach", "conceptual model"
        ]

        # --- FRAMEWORK COMPONENTS (your 6 frameworks only) ---
        self.framework_components = [
            # SWOT
            "strengths", "weaknesses", "opportunities", "threats",

            # Porter
            "bargaining power", "competitive rivalry", "threat of substitutes",
            "industry attractiveness", "market forces",

            # BMC
            "value proposition", "customer segments", "key activities",
            "key resources", "key partners", "revenue streams", "cost structure",

            # Lean Canvas
            "problem statement", "solution statement", "unfair advantage",
            "key metrics", "early adopters",

            # McKinsey 7S
            "shared values", "organizational alignment", "systems and structure",
            "leadership style", "staff skills",

            # Blue Ocean
            "value curve", "strategic canvas", "non customers",
            "differentiation strategy"
        ]

        # --- CONSULTING PHRASES THAT IMPLY FRAMEWORK USE ---
        self.consulting_phrases = [
            "analyze my business model",
            "analyze my market",
            "evaluate my strategy",
            "diagnose my organization",
            "competitive pressure",
            "market structure",
            "industry analysis",
            "organizational misalignment",
            "business model redesign",
            "innovation strategy",
            "create a new market",
            "find competitive advantage",
            "framework for",
            "which framework",
            "what framework should i use",
            "how to analyze",
            "how to evaluate",
            "how to assess",
            "strategic decision",
            "portfolio analysis",
            "resource allocation",
            "market attractiveness",
            "competitive strength"
        ]

    def detect(self, question: str) -> str:
        """
        Returns:
            "FRAMEWORK" → use frameworks DB
            "REPORT"     → use economic reports DB
        """
        q = question.lower()

        # 1. Direct matches to your 6 frameworks
        if any(k in q for k in self.direct_frameworks):
            return "FRAMEWORK"

        # 2. Mentions of components of your frameworks
        if any(k in q for k in self.framework_components):
            return "FRAMEWORK"

        # 3. Generic framework-like language
        if any(k in q for k in self.generic_framework_indicators):
            return "FRAMEWORK"

        # 4. Consulting-style phrasing
        if any(k in q for k in self.consulting_phrases):
            return "FRAMEWORK"

        return "REPORT"

    @staticmethod
    def is_known_framework(question: str) -> bool:
        q = question.lower()

        known = [
            "swot",
            "porter",
            "five forces",
            "business model canvas",
            "lean canvas",
            "mckinsey 7s",
            "7s",
            "blue ocean",
        ]

        return any(k in q for k in known)
