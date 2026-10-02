from utils.llm_model.argument_response import format_debate_history, generate_argument
from utils.prompts.against_prompt import AGAINST_AGENT_PROMPT, AGAINST_REBUTTAL_PROMPT

# opening arguments
def against_agent(topic, evidence):
    prompt = AGAINST_AGENT_PROMPT.format(topic=topic)

    return generate_argument(prompt, max_sentences=2, evidence=evidence)

# rebuttal arguments
def against_rebuttal(topic, opponent_argument, debate_history, evidence):
    prompt = AGAINST_REBUTTAL_PROMPT.format(
        topic=topic,
        opponent_argument=opponent_argument,
        debate_history=format_debate_history(debate_history),
    )

    return generate_argument(prompt, max_sentences=3, evidence=evidence)