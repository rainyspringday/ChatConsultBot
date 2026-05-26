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

    def detect(self, question: str) -> str:
        """
        Returns one of: FRAMEWORK, ANALYSIS, REPORT

        Design goals (from PDD):
        - ANALYSIS: user wants a framework recommendation / mapping
        - FRAMEWORK: user wants explanation of a WHITELISTED framework/component
        - REPORT: everything else (including out-of-domain)
        """
        q = (question or "").lower().strip()
        if not q:
            return "REPORT"

        # -----------------------
        # ANALYSIS (highest priority)
        # -----------------------
        if any(indicator in q for indicator in self.analysis_indicators):
            return "ANALYSIS"
        if "which framework" in q or "what framework" in q or "choose a framework" in q:
            return "ANALYSIS"
        if "suggest framework" in q or "recommend framework" in q:
            return "ANALYSIS"

        # -----------------------
        # FRAMEWORK (only if whitelisted signal is present)
        # -----------------------
        explanation_requested = any(p in q for p in self.explanation_phrases)
        component_requested = any(comp in q for comp in self.framework_components)
        framework_signal = (
            self.is_known_framework(q)
            or any(name in q for name in self.direct_frameworks)
            or ("framework" in q and self.is_known_framework(q))
        )
        # Component clarification (PDD user story) should route to FRAMEWORK
        # even if the user didn't use "explain/define/what is" phrasing.
        if framework_signal and (explanation_requested or component_requested):
            return "FRAMEWORK"

        # If user explicitly asks about "a framework" but none is whitelisted, treat as REPORT.
        # (Whitelist rejection is handled in the RAG pipeline for clearer messaging.)
        return "REPORT"

    # ---------------------------------------------------------
    # WHITELIST CHECK
    def is_known_framework(self, question: str) -> bool:
        q = question.lower()
        return any(k in q for k in self.allowed_frameworks)
