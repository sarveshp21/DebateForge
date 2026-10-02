import json
import re

from utils.llm_model.llm import call_llm
from utils.prompts.judge_prompt import JUDGE_AGENT_PROMPT

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {"type": "string", "enum": ["Pro", "Against"]},
        "scores": {
            "type": "object",
            "properties": {
                side: {
                    "type": "object",
                    "properties": {criterion: {"type": "integer", "minimum": 0, "maximum": 10}
                                   for criterion in ("logic", "clarity", "examples")},
                    "required": ["logic", "clarity", "examples"],
                    "additionalProperties": False,
                }
                for side in ("pro", "against")
            },
            "required": ["pro", "against"],
            "additionalProperties": False,
        },
        "supporting_quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "side": {"type": "string", "enum": ["Pro", "Against"]},
                    "quote": {"type": "string"},
                },
                "required": ["side", "quote"],
                "additionalProperties": False,
            },
            "minItems": 2,
            "maxItems": 2,
        },
    },
    "required": ["winner", "scores", "supporting_quotes"],
    "additionalProperties": False,
}


def _validate_judge_result(result, debate_rounds, evidence):
    if not isinstance(result, dict) or set(result) != {"winner", "scores", "supporting_quotes"}:
        raise ValueError("result must contain only winner, scores, and supporting_quotes")

    if not isinstance(result.get("winner"), str) or result["winner"] not in {"Pro", "Against"}:
        raise ValueError("winner must be exactly 'Pro' or 'Against'")

    scores = result.get("scores")
    if not isinstance(scores, dict) or set(scores) != {"pro", "against"}:
        raise ValueError("scores must be an object")

    for side in ("pro", "against"):
        side_scores = scores.get(side)
        if not isinstance(side_scores, dict) or set(side_scores) != {"logic", "clarity", "examples"}:
            raise ValueError(f"scores.{side} must be an object")
        for criterion in ("logic", "clarity", "examples"):
            score = side_scores.get(criterion)
            if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 10:
                raise ValueError(f"scores.{side}.{criterion} must be an integer from 0 to 10")

    criteria = ("logic", "clarity", "examples")
    pro_total = sum(scores["pro"][criterion] for criterion in criteria)
    against_total = sum(scores["against"][criterion] for criterion in criteria)
    if pro_total == against_total:
        raise ValueError("scores must show a clear winner")
    expected_winner = "Pro" if pro_total > against_total else "Against"
    if result["winner"] != expected_winner:
        raise ValueError("winner must match the higher total score")

    quotes = result.get("supporting_quotes")
    if not isinstance(quotes, list) or len(quotes) != 2:
        raise ValueError("supporting_quotes must contain one quote from each side")

    valid_source_ids = {source["id"] for source in evidence}
    quoted_sides = set()
    for item in quotes:
        if not isinstance(item, dict) or set(item) != {"side", "quote"}:
            raise ValueError("each supporting quote must contain only side and quote")
        side = item["side"]
        quote = item["quote"]
        if (
            not isinstance(side, str)
            or side not in {"Pro", "Against"}
            or not isinstance(quote, str)
            or not quote.strip()
        ):
            raise ValueError("each supporting quote must identify a side and non-empty quote")
        side_key = side.lower()
        if side_key in quoted_sides:
            raise ValueError("supporting quotes must include one quote from each side")
        if not any(quote in round_data[side_key] for round_data in debate_rounds):
            raise ValueError(f"supporting quote for {side} does not appear verbatim in the debate")
        for cited_id in re.findall(r"\[(S\d+)\]", quote):
            if cited_id not in valid_source_ids:
                raise ValueError(f"supporting quote references unknown source {cited_id}")
        quoted_sides.add(side_key)

    if quoted_sides != {"pro", "against"}:
        raise ValueError("supporting quotes must include one quote from each side")

    result["reason"] = (
        f"{result['winner']} won by the rubric total ({pro_total} to {against_total}). "
        + " ".join(f"{item['side']} said: \"{item['quote']}\"" for item in quotes)
    )

    return result

def judge_agent(topic, debate_rounds, evidence):
    debate_history = "\n\n".join(
        f"Round {round_number}:\nPro: {round_data['pro']}\nAgainst: {round_data['against']}"
        for round_number, round_data in enumerate(debate_rounds, start=1)
    )
    evidence_context = "\n\n".join(
        f"[{source['id']}] {source['title']} ({source['url']}): {source['excerpt']}"
        for source in evidence
    )
    prompt = JUDGE_AGENT_PROMPT.format(
        topic=topic,
        debate_history=debate_history,
        evidence=evidence_context,
    )

    response = call_llm(prompt, response_schema=JUDGE_SCHEMA)
    for attempt in range(2):
        try:
            return _validate_judge_result(json.loads(response), debate_rounds, evidence)
        except (ValueError, json.JSONDecodeError) as error:
            if attempt == 1:
                raise RuntimeError(f"The judge returned invalid output after retry: {error}") from error
            response = call_llm(
                f"{prompt}\n\nYour previous response was invalid: {error}. "
                "Return only JSON matching the required schema. Include exactly one supporting "
                "quote from each side, copied verbatim from the transcript. Ensure the winner "
                f"matches the higher score total. Previous response: {response}"
                , response_schema=JUDGE_SCHEMA
            )