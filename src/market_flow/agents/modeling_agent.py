"""
Financial Modeling Agent

An AI agent that performs comprehensive financial analysis using the Claude Agent SDK.
The agent follows a decision flow:

1. Fetch Market Data
2. Run DCF Analysis (baseline valuation)
3. Evaluate Results:
   - If FCF > 0 AND undervalued → Run LBO Model (buyout candidate)
   - If FCF < 0 OR high growth → Run Driver-Based Model (growth trajectory)
4. Synthesize findings into investment recommendation
"""

import os
from typing import AsyncIterator

from claude_agent_sdk import (
    query,
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
)

from .mcp_server import create_financial_modeling_server, ALL_TOOL_NAMES


# System prompt that instructs the agent on the analysis workflow
FINANCIAL_ANALYST_SYSTEM_PROMPT = """You are an expert financial analyst specializing in valuation and modeling.

## Your Analysis Process

Follow this structured workflow when analyzing a company:

### Step 1: Data Collection
First, gather comprehensive financial data:
- Use `fetch_company_profile` to get company overview, sector, and beta
- Use `fetch_financial_statements` or individual statement tools for detailed financials
- Use `fetch_key_metrics` for valuation multiples

### Step 2: Initial Valuation (DCF Analysis)
Run a DCF analysis to establish baseline intrinsic value:
- Use `run_dcf_model` to calculate intrinsic value per share
- Note the key outputs: intrinsic value, current price, upside %, and FCF trend

### Step 3: Model Selection Decision
Based on DCF results, choose the appropriate deep-dive model:

**Choose LBO Model when ALL of these apply:**
- Free cash flow is consistently positive (FCF > 0)
- Business has stable, predictable cash flows
- Intrinsic value suggests undervaluation (upside > 20%)
- Low capital intensity allows for debt paydown
- Industry has precedent for PE/LBO transactions

**Choose Driver-Based Model when ANY of these apply:**
- Free cash flow is negative or volatile
- Company is in high-growth phase (revenue growth > 20%)
- Business model is scaling (tech, biotech, SaaS, etc.)
- Unit economics are improving
- Industry consensus expects significant future growth

### Step 4: Deep Analysis
Execute the chosen model with appropriate assumptions.

NOTE: LBO and Driver-Based models are being developed. For now, provide a qualitative
assessment of which model would be appropriate and why, based on your DCF findings.

### Step 5: Synthesis & Recommendation
Combine all insights into a comprehensive investment recommendation:
- Executive summary (2-3 sentences)
- Key valuation metrics and what they imply
- Risk factors and upside catalysts
- Clear BUY/HOLD/SELL recommendation with price targets

## Important Guidelines

1. Always show your reasoning for model selection based on DCF results
2. Be specific and quantitative - reference actual numbers
3. Acknowledge limitations and areas needing further analysis
4. Use professional financial language but remain accessible

## Available Tools

You have access to market data and DCF modeling tools:
- Market data: company profile, financial statements, ratios, metrics, quotes
- DCF model: WACC calculation, FCF projection, terminal value, intrinsic value
"""


# System prompt for refinement based on reviewer feedback
REFINEMENT_SYSTEM_PROMPT = """You are an expert financial analyst refining a previous analysis based on reviewer feedback.

## Your Task
You have received feedback from a senior reviewer on your previous analysis. Your job is to:
1. Carefully read and understand each piece of feedback
2. Address each point using the tools available to you
3. If you lack a tool to address specific feedback, clearly state this in your refined report

## Available Tools
You have access to market data and DCF modeling tools:
- Market data: company profile, financial statements, ratios, metrics, quotes, analyst estimates
- DCF model: WACC calculation, FCF projection, terminal value, intrinsic value

## Important Guidelines
1. Address EVERY piece of feedback from the reviewer
2. Use tools to fetch additional data when the feedback requests deeper analysis
3. If feedback requests data/analysis you cannot perform with available tools, write:
   "TOOL LIMITATION: [describe what was requested and why it cannot be fulfilled]"
4. Maintain the same professional format as the original analysis
5. Clearly mark sections that have been revised with "[REVISED]" prefix
"""


class FinancialModelingAgent:
    """
    AI-powered financial modeling agent using Claude Agent SDK.

    This agent orchestrates financial analysis by:
    1. Fetching market data via FMP tools
    2. Running DCF valuation
    3. Deciding on LBO vs Driver-Based model based on results
    4. Synthesizing findings into recommendations

    Example:
        >>> agent = FinancialModelingAgent()
        >>> result = await agent.analyze("AAPL")
        >>> print(result["recommendation"])
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 20,
        permission_mode: str = "bypassPermissions",
    ):
        """
        Initialize the financial modeling agent.

        Args:
            model: Claude model to use (default: claude-sonnet-4)
            max_turns: Maximum number of agent turns (default: 20)
            permission_mode: Permission mode for tool execution
        """
        self.model = model
        self.max_turns = max_turns
        self.permission_mode = permission_mode
        self._server = None

    def _get_options(self) -> ClaudeAgentOptions:
        """Create ClaudeAgentOptions with MCP server and tools."""
        if self._server is None:
            self._server = create_financial_modeling_server()

        return ClaudeAgentOptions(
            system_prompt=FINANCIAL_ANALYST_SYSTEM_PROMPT,
            mcp_servers={"finance": self._server},
            allowed_tools=ALL_TOOL_NAMES,
            model=self.model,
            max_turns=self.max_turns,
            permission_mode=self.permission_mode,
        )

    def _get_refinement_options(self) -> ClaudeAgentOptions:
        """Create ClaudeAgentOptions for refinement with MCP tools."""
        if self._server is None:
            self._server = create_financial_modeling_server()

        return ClaudeAgentOptions(
            system_prompt=REFINEMENT_SYSTEM_PROMPT,
            mcp_servers={"finance": self._server},
            allowed_tools=ALL_TOOL_NAMES,
            model=self.model,
            max_turns=self.max_turns,
            permission_mode=self.permission_mode,
        )

    async def analyze(self, ticker: str) -> dict:
        """
        Run comprehensive financial analysis for a company.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")

        Returns:
            dict with:
                - ticker: Stock ticker
                - analysis: Full analysis text from the agent
                - messages: List of all messages from the conversation
        """
        prompt = f"""Analyze {ticker.upper()} following the structured workflow:

1. First, fetch the company profile and key financial data
2. Run a DCF analysis to calculate intrinsic value
3. Based on DCF results (FCF trend, valuation), determine if this is:
   - A potential LBO candidate (positive FCF, undervalued, stable cash flows)
   - A growth company requiring Driver-Based analysis (negative FCF, high growth)
4. Provide your deep analysis based on the appropriate model
5. Synthesize your findings into a clear investment recommendation

Be thorough and quantitative in your analysis."""

        options = self._get_options()
        messages = []
        analysis_text = []

        async for message in query(prompt=prompt, options=options):
            messages.append(message)

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        analysis_text.append(block.text)

            if isinstance(message, ResultMessage):
                # Conversation complete
                break

        return {
            "ticker": ticker.upper(),
            "analysis": "\n".join(analysis_text),
            "messages": messages,
        }

    async def refine(
        self,
        ticker: str,
        feedback: str,
        prior_analysis: str,
    ) -> dict:
        """
        Refine a previous analysis based on reviewer feedback.

        The agent will use available MCP tools to address the feedback.
        If feedback requires tools not available, the agent will note this
        in the refined report.

        Args:
            ticker: Stock ticker symbol
            feedback: Feedback from the boss agent's review
            prior_analysis: The original analysis that was reviewed

        Returns:
            dict with:
                - ticker: Stock ticker
                - analysis: Refined analysis text
                - messages: List of all messages from the conversation
                - is_refinement: True to indicate this is a refined analysis
        """
        prompt = f"""You previously analyzed {ticker.upper()} and received the following feedback:

--- REVIEWER FEEDBACK ---
{feedback}
--- END FEEDBACK ---

--- YOUR PREVIOUS ANALYSIS ---
{prior_analysis}
--- END PREVIOUS ANALYSIS ---

Please refine your analysis by:
1. Addressing each point in the feedback
2. Using available tools to fetch any additional data requested
3. Noting any feedback that cannot be addressed due to tool limitations
4. Producing a complete, refined analysis

Start by identifying which feedback points you can address with your available tools."""

        options = self._get_refinement_options()
        messages = []
        analysis_text = []

        async for message in query(prompt=prompt, options=options):
            messages.append(message)

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        analysis_text.append(block.text)

            if isinstance(message, ResultMessage):
                break

        return {
            "ticker": ticker.upper(),
            "analysis": "\n".join(analysis_text),
            "messages": messages,
            "is_refinement": True,
        }

    async def analyze_streaming(self, ticker: str) -> AsyncIterator[str]:
        """
        Run analysis with streaming output.

        Args:
            ticker: Stock ticker symbol

        Yields:
            Text chunks as they're generated
        """
        prompt = f"""Analyze {ticker.upper()} following the structured workflow:

1. First, fetch the company profile and key financial data
2. Run a DCF analysis to calculate intrinsic value
3. Based on DCF results, determine the appropriate valuation model
4. Provide your deep analysis
5. Synthesize your findings into a clear investment recommendation"""

        options = self._get_options()

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text"):
                        yield block.text

    async def interactive_session(self) -> None:
        """
        Start an interactive session for multi-turn conversations.

        Use this when you want to have a back-and-forth conversation
        with the agent about financial analysis.
        """
        options = self._get_options()

        async with ClaudeSDKClient(options) as client:
            print("Financial Modeling Agent ready. Type 'quit' to exit.")
            print("Example: 'Analyze AAPL' or 'Compare MSFT and GOOGL'\n")

            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    break

                await client.query(user_input)

                async for message in client.receive_messages():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if hasattr(block, "text"):
                                print(f"\nAgent: {block.text}")

                    if isinstance(message, ResultMessage):
                        break


# Convenience function for simple analysis
async def analyze_company(ticker: str, **kwargs) -> dict:
    """
    Convenience function to analyze a company.

    Args:
        ticker: Stock ticker symbol
        **kwargs: Additional arguments passed to FinancialModelingAgent

    Returns:
        Analysis result dict
    """
    agent = FinancialModelingAgent(**kwargs)
    return await agent.analyze(ticker)


# Legacy function for backward compatibility with dcf_analyst_agent
def analyze_dcf(dcf_result, company_context=None, api_key=None):
    """
    Legacy function for backward compatibility.

    This wraps the old DCF analysis functionality. For new code,
    use FinancialModelingAgent.analyze() instead.
    """
    # Import the old implementation
    from .dcf_analyst_agent_old import analyze_dcf as _analyze_dcf_legacy
    return _analyze_dcf_legacy(dcf_result, company_context, api_key)
