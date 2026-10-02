# - Takes topic
# - Creates prompt
# - Calls LLM
# - Returns result

from utils.llm_model.argument_response import format_debate_history, generate_argument
from utils.prompts.pro_prompt import PRO_AGENT_PROMPT, PRO_REBUTTAL_PROMPT

# opening arguments
def pro_agent(topic, evidence):
    prompt = PRO_AGENT_PROMPT.format(topic=topic)

    return generate_argument(prompt, max_sentences=2, evidence=evidence)

# rebuttal arguments
def pro_rebuttal(topic, opponent_argument, debate_history, evidence):
    prompt = PRO_REBUTTAL_PROMPT.format(
        topic=topic,
        opponent_argument=opponent_argument,
        debate_history=format_debate_history(debate_history),
    )

    return generate_argument(prompt, max_sentences=2, evidence=evidence)

