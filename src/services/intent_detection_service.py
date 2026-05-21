class IntentDetectionService:
    """
    Clean, safe, and correct intent classifier for routing queries
    to the correct Chroma DB (frameworks vs economic reports).
    """

    def __init__(self):
        # --- WHITELIST: ONLY THESE FRAMEWORKS ARE ALLOWED ---
        self.allowed_frameworks = [
            "swot",
            "porter",
            "five forces",
            "business model canvas",
            "lean canvas",
            "mckinsey 7s",
            "7s",
            "blue ocean",
        ]

        # --- ANALYSIS INDICATORS (highest priority) ---
        # These mean: "User wants to CHOOSE a framework"
        self.analysis_indicators = [
            "which framework should i use",
            "what framework should i use",
            "recommend a framework",
            "help me choose a framework",
            "analyze my problem",
            "analyze my business",
            "what should i analyze",
            "how do i understand this problem",
            "how do i solve this problem",
        ]

        # --- DIRECT FRAMEWORK NAMES (for EXPLANATION intent) ---
        self.direct_frameworks = [
            "swot", "s.w.o.t",
            "porter", "five forces", "5 forces",
            "business model canvas", "bmc",
            "lean canvas",
            "mckinsey 7s", "7s", "7-s", "seven s",
            "blue ocean", "errc", "eliminate reduce raise create"
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

        # --- EXPLANATION PHRASES ---
        self.explanation_phrases = [
            "explain",
            "describe",
            "what is",
            "define",
            "tell me about",
        ]

    @staticmethod
    def detect(question: str) -> str:
        q = question.lower()

        # ANALYSIS: user wants to choose a framework
        if "which framework" in q or "what framework" in q or "choose a framework" in q:
            return "ANALYSIS"

        # FRAMEWORK: user wants to explain a framework
        if any(p in q for p in ["explain", "describe", "define", "what is"]):
            return "FRAMEWORK"

        # Default: economic report
        return "REPORT"

    # ---------------------------------------------------------
    # WHITELIST CHECK
    def is_known_framework(self, question: str) -> bool:
        q = question.lower()
        return any(k in q for k in self.allowed_frameworks)
