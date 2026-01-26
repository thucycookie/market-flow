"""
Financial Modeling Agent

An AI agent that performs comprehensive financial analysis using the Anthropic API
with native tool use. The agent follows a decision flow:

1. Fetch Market Data
2. Run DCF Analysis (baseline valuation)
3. Evaluate Results:
   - If FCF > 0 AND undervalued → Run LBO Model (buyout candidate)
   - If FCF < 0 OR high growth → Run Driver-Based Model (growth trajectory)
4. Synthesize findings into investment recommendation
"""

from anthropic import Anthropic

from .financial_tools import (
    get_anthropic_tool_schemas,
    execute_tool,
)


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
Based on DCF results and company characteristics, choose the appropriate valuation model:

**Choose DCF Model when:**
- Free cash flow is consistently positive (FCF > 0)
- Business is mature with stable, predictable cash flows
- Traditional industrial, retail, or established tech companies

**Choose CBCV (Customer-Based Corporate Valuation) Model when ANY of these apply:**
- Company is customer/subscriber-centric (NFLX, SOFI, HOOD, SPOT, etc.)
- Free cash flow is negative due to customer acquisition investments
- Company is in high-growth phase focused on customer acquisition
- Subscription or recurring revenue business model
- Unit economics (LTV/CAC ratio) is key to investment thesis
- DCF produces negative or nonsensical intrinsic value

For CBCV, you will need customer metrics:
- Total customers/subscribers (REQUIRED - from 10-K, earnings)
- ARPU can be calculated from revenue/customers
- Churn rate uses industry benchmarks if not disclosed

**Choose LBO Model when ALL of these apply:**
- Free cash flow is consistently positive (FCF > 0)
- Business has stable, predictable cash flows
- Intrinsic value suggests undervaluation (upside > 20%)
- Low capital intensity allows for debt paydown
- Industry has precedent for PE/LBO transactions

### Step 4: Deep Analysis
Execute the chosen model with appropriate assumptions.

For CBCV analysis:
- Use `run_cbcv_model` with ticker and total_customers
- Key outputs: CLV, LTV/CAC ratio, existing customer equity, future customer equity
- A healthy LTV/CAC ratio is > 3x

NOTE: LBO model is being developed. For LBO candidates, provide a qualitative
assessment of why the company would be attractive for a buyout.

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

You have access to market data and valuation modeling tools:
- Market data: company profile, financial statements, ratios, metrics, quotes
- DCF model: WACC calculation, FCF projection, terminal value, intrinsic value
- CBCV model: Customer Lifetime Value (CLV), customer equity valuation, industry churn benchmarks

## Reasoning Documentation (CRITICAL)

Your analysis will be reviewed by senior analysts. Document your reasoning clearly:

### Tool Usage Rationale
For each tool you call, briefly explain:
- **Why** you're calling this tool at this point
- **What** you expect to learn from it
- **How** it connects to your analysis workflow

Example:
"I'm fetching the income statement to examine revenue growth trends over 5 years.
This will help me determine if the company is in a growth or mature phase,
which affects my choice of valuation model."

### Assumption Documentation
Whenever you make an assumption, state it explicitly:
- Growth rate assumptions: "Assuming 8% revenue growth based on 5-year historical CAGR of 7.2%"
- Discount rate choices: "Using 10% WACC because beta of 1.2 and current risk-free rate of 4.5%"
- Terminal value assumptions: "Terminal growth of 2.5% aligned with long-term GDP growth"
"""


# System prompt for refinement based on reviewer feedback
REFINEMENT_SYSTEM_PROMPT = """You are an expert financial analyst refining a previous analysis based on reviewer feedback.

## Your Task
You have received feedback from a senior reviewer on your previous analysis. Your job is to:
1. Carefully read and understand each piece of feedback
2. Address each point using the tools available to you
3. If you lack a tool to address specific feedback, clearly state this in your refined report

## Available Tools
You have access to market data and valuation modeling tools:
- Market data: company profile, financial statements, ratios, metrics, quotes, analyst estimates
- DCF model: WACC calculation, FCF projection, terminal value, intrinsic value
- CBCV model: Customer Lifetime Value (CLV), customer equity valuation, industry churn benchmarks

## Important Guidelines
1. Address EVERY piece of feedback from the reviewer
2. Use tools to fetch additional data when the feedback requests deeper analysis
3. If feedback requests data/analysis you cannot perform with available tools, write:
   "TOOL LIMITATION: [describe what was requested and why it cannot be fulfilled]"
4. Maintain the same professional format as the original analysis
5. Clearly mark sections that have been revised with "[REVISED]" prefix

### Reasoning Documentation
Continue to document:
- **Tool Usage Rationale**: Explain why you're calling each tool to address the feedback
- **Assumption Changes**: If you're revising assumptions, state the old value, new value, and why
"""


class FinancialModelingAgent:
    """
    AI-powered financial modeling agent using Anthropic API with tool use.

    This agent orchestrates financial analysis by:
    1. Fetching market data via FMP tools
    2. Running DCF valuation
    3. Deciding on LBO vs Driver-Based model based on results
    4. Synthesizing findings into recommendations

    Example:
        >>> agent = FinancialModelingAgent()
        >>> result = await agent.analyze("AAPL")
        >>> print(result["analysis"])
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        max_tool_iterations: int = 20,
    ):
        """
        Initialize the financial modeling agent.

        Args:
            model: Claude model to use (default: claude-sonnet-4)
            max_tokens: Maximum tokens per response (default: 8192)
            max_tool_iterations: Maximum tool use iterations (default: 20)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.max_tool_iterations = max_tool_iterations
        self.client = Anthropic()
        self.tools = get_anthropic_tool_schemas()

    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool and return serialized result."""
        return execute_tool(name, args)

    def _process_tool_calls(self, response) -> list[dict]:
        """
        Process tool use blocks from response and execute tools.

        Args:
            response: Anthropic API response

        Returns:
            List of tool_result content blocks
        """
        tool_results = []

        for block in response.content:
            if block.type == "tool_use":
                result = self._execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        return tool_results

    def _extract_text(self, response) -> str:
        """Extract text content from response."""
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def _run_with_tools(
        self,
        system_prompt: str,
        user_message: str,
    ) -> tuple[str, list[dict]]:
        """
        Run a conversation with tool use loop.

        Args:
            system_prompt: System prompt for the conversation
            user_message: Initial user message

        Returns:
            Tuple of (final_text, all_messages)
        """
        messages = [{"role": "user", "content": user_message}]

        # Initial API call
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            tools=self.tools,
            messages=messages,
        )

        iteration = 0

        # Tool use loop
        while response.stop_reason == "tool_use" and iteration < self.max_tool_iterations:
            iteration += 1

            # Execute tools and get results
            tool_results = self._process_tool_calls(response)

            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Continue conversation
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                tools=self.tools,
                messages=messages,
            )

        # Extract final text
        final_text = self._extract_text(response)

        # Add final response to messages
        messages.append({"role": "assistant", "content": response.content})

        return final_text, messages

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

        analysis_text, messages = self._run_with_tools(
            FINANCIAL_ANALYST_SYSTEM_PROMPT,
            prompt,
        )

        return {
            "ticker": ticker.upper(),
            "analysis": analysis_text,
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

        The agent will use available tools to address the feedback.
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

        analysis_text, messages = self._run_with_tools(
            REFINEMENT_SYSTEM_PROMPT,
            prompt,
        )

        return {
            "ticker": ticker.upper(),
            "analysis": analysis_text,
            "messages": messages,
            "is_refinement": True,
        }

    async def analyze_streaming(self, ticker: str):
        """
        Run analysis with streaming output.

        Note: Streaming with tool use requires handling tool calls between streams.
        This is a simplified implementation that yields the final result.

        Args:
            ticker: Stock ticker symbol

        Yields:
            Text chunks as they're generated
        """
        # For tool use, we need to handle the full loop first
        result = await self.analyze(ticker)
        yield result["analysis"]

    async def interactive_session(self) -> None:
        """
        Start an interactive session for multi-turn conversations.

        Use this when you want to have a back-and-forth conversation
        with the agent about financial analysis.
        """
        print("Financial Modeling Agent ready. Type 'quit' to exit.")
        print("Example: 'Analyze AAPL' or 'Compare MSFT and GOOGL'\n")

        messages = []

        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break

            messages.append({"role": "user", "content": user_input})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=FINANCIAL_ANALYST_SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages,
            )

            # Handle tool use loop
            while response.stop_reason == "tool_use":
                tool_results = self._process_tool_calls(response)
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=FINANCIAL_ANALYST_SYSTEM_PROMPT,
                    tools=self.tools,
                    messages=messages,
                )

            # Print and save final response
            final_text = self._extract_text(response)
            print(f"\nAgent: {final_text}\n")
            messages.append({"role": "assistant", "content": response.content})


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
