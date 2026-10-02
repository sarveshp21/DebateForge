import json
import re

from utils.llm_model.llm import call_llm

ARGUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    },
    "required": ["text", "source_ids"],
    "additionalProperties": False,
}


def _format_evidence(evidence):
    return "\n\n".join(
        f"[{source['id']}] {source['title']}\nURL: {source['url']}\nExcerpt: {source['excerpt']}"
        for source in evidence
    )


def format_debate_history(debate_history):
    return "\n\n".join(
        f"Round {round_number}:\nPro: {round_data['pro']}\nAgainst: {round_data['against']}"
        for round_number, round_data in enumerate(debate_history, start=1)
    ) or "No previous rounds."


def _validate_argument(response, max_sentences, valid_source_ids):
    try:
        result = json.loads(response)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("response is not valid JSON") from error

    if not isinstance(result, dict) or set(result) != {"text", "source_ids"}:
        raise ValueError("response must contain only text and source_ids")

    text = result["text"]
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is empty")

    source_ids = result["source_ids"]
    if (
        not isinstance(source_ids, list)
        or not source_ids
        or any(not isinstance(source_id, str) for source_id in source_ids)
    ):
        raise ValueError("source_ids must contain at least one cited source")
    if any(source_id not in valid_source_ids for source_id in source_ids):
        raise ValueError("response cites a source ID that was not retrieved")

    cleaned = text.strip()
    has_label = re.match(r"(?i)^(?:pro|against|reference|citation|scholarly reference)\s*:", cleaned)
    if has_label or "\n" in cleaned or re.search(r"```|\*\*|^\s*(?:#{1,6}\s|[-*]\s)", cleaned):
        raise ValueError("response contains headings, markup, or multiple lines")

    sentence_count = len(re.findall(r"[^.!?]+(?:[.!?]+|$)", cleaned))
    if sentence_count > max_sentences:
        raise ValueError(f"response has {sentence_count} sentences; maximum is {max_sentences}")

    return {"text": cleaned, "source_ids": list(dict.fromkeys(source_ids))}


def generate_argument(prompt, max_sentences, evidence):
    valid_source_ids = {source["id"] for source in evidence}
    full_prompt = (
        f"{prompt}\n\nRetrieved evidence (use only these sources for factual claims):\n"
        f"{_format_evidence(evidence)}\n\n"
        "Return JSON with exactly two keys: text and source_ids. The text is the argument. "
        "source_ids must list one or more IDs from the retrieved evidence that support the text. "
        "Do not invent sources, IDs, facts, statistics, or citations."
    )
    response = call_llm(full_prompt, response_schema=ARGUMENT_SCHEMA)
    try:
        result = _validate_argument(response, max_sentences, valid_source_ids)
    except ValueError as first_error:
        retry_prompt = (
            f"{full_prompt}\n\nYour previous response violated the required JSON format: {first_error}. "
            "Return corrected JSON with only text and source_ids, valid IDs from the evidence, "
            f"and text with no labels, markup, line breaks, or more than {max_sentences} sentences. "
            f"Previous response: {response}"
        )
        response = call_llm(retry_prompt, response_schema=ARGUMENT_SCHEMA)
        try:
            result = _validate_argument(response, max_sentences, valid_source_ids)
        except ValueError as second_error:
            raise RuntimeError(f"The debate agent returned invalid output after retry: {second_error}") from second_error

    references = " ".join(f"[{source_id}]" for source_id in result["source_ids"])
    result["text"] = f"{result['text']} {references}"
    return result