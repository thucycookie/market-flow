"""
Boss Agent

An AI-powered supervisor that reviews analyst reports and provides feedback.
The boss agent validates reports based on agent-specific criteria and
determines whether the report meets quality standards.
"""

import json
import re

from anthropic import Anthropic


# Review prompt for financial modeling reports
BOSS_AGENT_FINANCIAL_MODELING_PROMPT = """You are a senior investment analyst reviewing a financial modeling report.

## Validation Criteria

Evaluate the report against these criteria and provide a score (1-5) for each:

### a) Data Reasonableness (1-5)
- Are all data points within realistic bounds?
- Check: growth rates, margins, multiples against industry norms
- Flag any values that seem impossible or erroneous

### b) Outlier Detection (1-5)
- Are there any highly unusual data points?
- Values that are suspiciously high or low?
- Any metrics that deviate significantly from historical trends?

### c) Executive Summary Clarity (1-5)
- Is the investment recommendation clearly articulated?
- Can I understand the thesis in 30 seconds?
- Is it actionable (clear BUY/HOLD/SELL)?

### d) Data-Recommendation Alignment (1-5)
- Does the data strongly support the recommendation?
- Are there gaps in the analysis that need deeper investigation?
- What additional data points would strengthen the thesis?

### e) Scenario Analysis (1-5)
- Can I clearly see Bear, Neutral, and Bull cases?
- Are the assumptions for each scenario reasonable?
- Is the probability weighting sensible?

### f) Risk Assessment (1-5)
- Does the report explain what could cause the company to fail?
- Are headwind risks quantified with data?
- Are there any obvious risks not addressed?

## Output Format

You MUST respond with ONLY a valid JSON object (no markdown, no explanation before or after):
{
    "approved": true or false,
    "overall_score": <average of all scores as a number>,
    "scores": {
        "data_reasonableness": <1-5>,
        "outlier_detection": <1-5>,
        "executive_summary_clarity": <1-5>,
        "data_recommendation_alignment": <1-5>,
        "scenario_analysis": <1-5>,
        "risk_assessment": <1-5>
    },
    "feedback": "<specific actionable feedback if not approved, empty string if approved>",
    "strengths": ["<what the report did well>"],
    "improvements_needed": ["<specific items to address>"]
}

## Approval Threshold
- Overall score >= 4.0 AND no individual score below 3 = APPROVED
- Otherwise = NOT APPROVED (provide detailed feedback)
"""


class BossAgent:
    """
    AI-powered supervisor that reviews analyst reports and provides feedback.

    The boss agent validates reports based on agent-specific criteria and
    determines whether the report meets quality standards.

    Attributes:
        MAX_ITERATIONS: Maximum number of review-refine cycles (class attribute)

    Example:
        >>> boss = BossAgent()
        >>> result = await boss._review_analyst_report(analysis, "financial_modeling")
        >>> if result["approved"]:
        ...     print("Report approved!")
        ... else:
        ...     print(f"Feedback: {result['feedback']}")
    """

    # Class attribute for max iterations
    MAX_ITERATIONS = 2

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ):
        """
        Initialize the boss agent.

        Args:
            model: Claude model to use (default: claude-sonnet-4)
            max_tokens: Maximum tokens per response (default: 4096)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.client = Anthropic()

    def _get_review_prompt(self, agent_type: str) -> str:
        """
        Get agent-specific review prompt.

        Args:
            agent_type: Type of agent that produced the report

        Returns:
            System prompt for reviewing that agent type's reports

        Raises:
            ValueError: If agent_type is not supported
        """
        prompts = {
            "financial_modeling": BOSS_AGENT_FINANCIAL_MODELING_PROMPT,
            # Future agent types:
            # "research": BOSS_AGENT_RESEARCH_PROMPT,
            # "risk_analysis": BOSS_AGENT_RISK_PROMPT,
        }

        if agent_type not in prompts:
            supported = ", ".join(prompts.keys())
            raise ValueError(
                f"Unknown agent type: {agent_type}. Supported types: {supported}"
            )

        return prompts[agent_type]

    def _parse_review_response(self, response_text: str) -> dict:
        """
        Parse the JSON response from the review.

        Args:
            response_text: Raw text response from Claude

        Returns:
            Parsed review dict with approved, scores, feedback, etc.
        """
        # Try to extract JSON from the response
        # Sometimes the model wraps it in markdown code blocks
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # If parsing fails, return a default structure indicating review failure
        return {
            "approved": False,
            "overall_score": 0,
            "scores": {},
            "feedback": f"Failed to parse review response. Raw response: {response_text[:500]}",
            "strengths": [],
            "improvements_needed": ["Review response was not in expected JSON format"],
            "parse_error": True,
        }

    async def _review_analyst_report(
        self,
        analysis: str,
        agent_type: str,
    ) -> dict:
        """
        Review an analyst report and determine approval status.

        Args:
            analysis: The full analysis text to review
            agent_type: Type of agent that produced the report
                       (e.g., "financial_modeling", "research", etc.)

        Returns:
            dict with:
                - approved: bool - whether the report passes review
                - overall_score: float - average of all scores
                - scores: dict - scores for each validation criterion
                - feedback: str - specific feedback for improvement (if not approved)
                - strengths: list - what the report did well
                - improvements_needed: list - specific items to address
        """
        system_prompt = self._get_review_prompt(agent_type)

        prompt = f"""Please review the following analyst report and evaluate it against all criteria.

--- ANALYST REPORT ---
{analysis}
--- END REPORT ---

Evaluate this report and provide your assessment as a JSON object."""

        # Direct Anthropic API call (no tools needed for review)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        return self._parse_review_response(response_text)
