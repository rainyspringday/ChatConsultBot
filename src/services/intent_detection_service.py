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

        # --- STRUCTURAL FRAMEWORK INDICATORS (safe + future-proof) ---
        # These detect ANY framework-like query without false positives.
        self.generic_framework_indicators = [
            # Matrix-type frameworks
            "matrix",            # GE–McKinsey, BCG, Ansoff, etc.

            # Canvas-type frameworks
            "canvas",            # BMC, Lean Canvas

            # Forces-type frameworks
            "forces",            # Porter’s Five Forces

            # 7S-type frameworks
            "7s", "7-s",

            # Blue Ocean Strategy markers
            "value curve",
            "strategic canvas",

            # Additional well-known frameworks (future-proofing)
            "vrio",
            "pestel", "pestle",
            "kano",
            "ansoff",
            "bcg",
            "balanced scorecard",
            "okrs", "okr",
            "value chain",
            "growth-share",
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

        # --- CONSULTING PHRASES (high precision only) ---
        self.consulting_phrases = [
            "which framework",
            "what framework should i use",
            "recommend a framework",
            "best framework for",
            "framework for",
            "analyze using a framework",
            "apply a framework",
        ]

    def detect(self, question: str) -> str:
        q = question.lower()

        # 1. Direct matches to your 6 frameworks
        if any(k in q for k in self.direct_frameworks):
            return "FRAMEWORK"

        # 2. Mentions of components of your frameworks
        if any(k in q for k in self.framework_components):
            return "FRAMEWORK"

        # 3. Structural indicators for ANY framework
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
