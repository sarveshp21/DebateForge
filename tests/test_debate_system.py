import json
import io
import unittest
from unittest.mock import patch

from core.debate_engine import run_debate
from agents.judge_agent import judge_agent
from utils.llm_model.argument_response import generate_argument
from utils.evidence.wikipedia import fetch_topic_evidence


TEST_EVIDENCE = [{
    "id": "S1",
    "title": "Test evidence",
    "url": "https://en.wikipedia.org/wiki/Test",
    "excerpt": "Retrieved evidence excerpt.",
}]


class DebateSystemTests(unittest.TestCase):
    def test_wikipedia_evidence_extracts_and_identifies_sources(self):
        payload = {
            "query": {
                "pages": [
                    {
                        "title": "Digital textbook",
                        "fullurl": "https://en.wikipedia.org/wiki/Digital_textbook",
                        "extract": "A digital textbook is a digital book intended for educational use.",
                    }
                ]
            }
        }
        with patch(
            "utils.evidence.wikipedia.urlopen",
            return_value=io.BytesIO(json.dumps(payload).encode("utf-8")),
        ):
            evidence = fetch_topic_evidence("digital textbooks")

        self.assertEqual(evidence[0]["id"], "S1")
        self.assertEqual(evidence[0]["title"], "Digital textbook")
        self.assertIn("https://en.wikipedia.org/", evidence[0]["url"])

    def test_wikipedia_evidence_fails_when_no_articles_match(self):
        with patch(
            "utils.evidence.wikipedia.urlopen",
            return_value=io.BytesIO(b'{"query": {"pages": []}}'),
        ):
            with self.assertRaisesRegex(RuntimeError, "No relevant Wikipedia evidence"):
                fetch_topic_evidence("unfindable topic")

    def test_argument_generation_retries_invalid_format(self):
        with patch(
            "utils.llm_model.argument_response.call_llm",
            side_effect=[
                json.dumps({"text": "First sentence. Second sentence. Third sentence.", "source_ids": ["S1"]}),
                json.dumps({"text": "Corrected argument.", "source_ids": ["S1"]}),
            ],
        ) as llm_call:
            result = generate_argument("Debate prompt", max_sentences=2, evidence=TEST_EVIDENCE)

        self.assertEqual(result["text"], "Corrected argument. [S1]")
        self.assertEqual(llm_call.call_count, 2)

    def test_argument_generation_fails_after_invalid_retry(self):
        with patch(
            "utils.llm_model.argument_response.call_llm",
            return_value=json.dumps({"text": "First sentence. Second sentence. Third sentence.", "source_ids": ["S1"]}),
        ):
            with self.assertRaisesRegex(RuntimeError, "invalid output after retry"):
                generate_argument("Debate prompt", max_sentences=2, evidence=TEST_EVIDENCE)

    def test_argument_generation_retries_labeled_output(self):
        with patch(
            "utils.llm_model.argument_response.call_llm",
            side_effect=[
                json.dumps({"text": "Against: The response has a label.", "source_ids": ["S1"]}),
                json.dumps({"text": "The corrected response has no label.", "source_ids": ["S1"]}),
            ],
        ) as llm_call:
            result = generate_argument("Debate prompt", max_sentences=2, evidence=TEST_EVIDENCE)

        self.assertEqual(result["text"], "The corrected response has no label. [S1]")
        self.assertEqual(llm_call.call_count, 2)

    def test_argument_generation_rejects_unknown_source_id(self):
        response = json.dumps({"text": "An unsupported factual claim.", "source_ids": ["S9"]})
        with patch("utils.llm_model.argument_response.call_llm", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "source ID that was not retrieved"):
                generate_argument("Debate prompt", max_sentences=2, evidence=TEST_EVIDENCE)

    def test_judge_retries_invalid_output(self):
        valid_result = {
            "winner": "Against",
            "scores": {
                "pro": {"logic": 5, "clarity": 5, "examples": 5},
                "against": {"logic": 6, "clarity": 6, "examples": 6},
            },
            "supporting_quotes": [
                {"side": "Pro", "quote": "Pro claim"},
                {"side": "Against", "quote": "Against claim"},
            ],
        }
        with patch(
            "agents.judge_agent.call_llm",
            side_effect=["not json", json.dumps(valid_result)],
        ) as llm_call:
            result = judge_agent(
                "A proposition",
                [{"pro": "Pro claim", "against": "Against claim"}],
                TEST_EVIDENCE,
            )

        self.assertEqual(result["supporting_quotes"], valid_result["supporting_quotes"])
        self.assertIn('Against said: "Against claim"', result["reason"])
        self.assertEqual(llm_call.call_count, 2)

    def test_judge_rejects_scores_that_contradict_winner(self):
        invalid_result = {
            "winner": "Against",
            "scores": {
                "pro": {"logic": 8, "clarity": 8, "examples": 8},
                "against": {"logic": 6, "clarity": 6, "examples": 6},
            },
            "supporting_quotes": [
                {"side": "Pro", "quote": "Pro claim"},
                {"side": "Against", "quote": "Against claim"},
            ],
        }
        with patch("agents.judge_agent.call_llm", return_value=json.dumps(invalid_result)):
            with self.assertRaisesRegex(RuntimeError, "winner must match"):
                judge_agent("A proposition", [{"pro": "Pro claim", "against": "Against claim"}], TEST_EVIDENCE)

    def test_judge_rejects_quote_not_in_transcript(self):
        invalid_result = {
            "winner": "Pro",
            "scores": {
                "pro": {"logic": 8, "clarity": 8, "examples": 8},
                "against": {"logic": 6, "clarity": 6, "examples": 6},
            },
            "supporting_quotes": [
                {"side": "Pro", "quote": "Pro claim"},
                {"side": "Against", "quote": "Invented example"},
            ],
        }
        with patch("agents.judge_agent.call_llm", return_value=json.dumps(invalid_result)):
            with self.assertRaisesRegex(RuntimeError, "does not appear verbatim"):
                judge_agent("A proposition", [{"pro": "Pro claim", "against": "Against claim"}], TEST_EVIDENCE)

    def test_judge_retries_when_winner_has_wrong_type(self):
        valid_result = {
            "winner": "Pro",
            "scores": {
                "pro": {"logic": 8, "clarity": 8, "examples": 8},
                "against": {"logic": 6, "clarity": 6, "examples": 6},
            },
            "supporting_quotes": [
                {"side": "Pro", "quote": "Pro claim"},
                {"side": "Against", "quote": "Against claim"},
            ],
        }
        invalid_result = dict(valid_result, winner=[])
        with patch(
            "agents.judge_agent.call_llm",
            side_effect=[json.dumps(invalid_result), json.dumps(valid_result)],
        ) as llm_call:
            result = judge_agent(
                "A proposition",
                [{"pro": "Pro claim", "against": "Against claim"}],
                TEST_EVIDENCE,
            )

        self.assertEqual(result["winner"], "Pro")
        self.assertEqual(llm_call.call_count, 2)

    def test_run_debate_rejects_empty_topic_and_out_of_range_rounds(self):
        with self.assertRaises(ValueError):
            list(run_debate("  ", 1))

        with self.assertRaises(ValueError):
            list(run_debate("A user-provided topic", 0))

    def test_run_debate_returns_judge_result(self):
        rounds = 3
        judge_response = json.dumps({
            "winner": "Pro",
            "scores": {
                "pro": {"logic": 8, "clarity": 8, "examples": 8},
                "against": {"logic": 7, "clarity": 7, "examples": 7},
            },
            "supporting_quotes": [
                {"side": "Pro", "quote": "Pro opening."},
                {"side": "Against", "quote": "Against opening."},
            ],
        })
        with (
            patch("core.debate_engine.fetch_topic_evidence", return_value=TEST_EVIDENCE),
            patch("core.debate_engine.pro_agent", return_value={"text": "Pro opening."}),
            patch("core.debate_engine.against_agent", return_value={"text": "Against opening."}),
            patch("core.debate_engine.pro_rebuttal", side_effect=[
                {"text": "Pro round 2."},
                {"text": "Pro round 3."},
            ]) as pro_rebuttal_call,
            patch("core.debate_engine.against_rebuttal", side_effect=[
                {"text": "Against round 2."},
                {"text": "Against round 3."},
            ]),
            patch("agents.judge_agent.call_llm", return_value=judge_response) as judge_call,
        ):
            events = list(run_debate("AI will improve education", rounds))

        judge_event = next((event for event in events if event[0] == "judge"), None)
        self.assertIsNotNone(judge_event, "Judge event was not produced")

        judge_result = judge_event[1]
        self.assertIn("winner", judge_result)
        self.assertIn("scores", judge_result)
        self.assertIn("reason", judge_result)
        self.assertIn(judge_result["winner"], ["Pro", "Against"])

        self.assertIn("pro", judge_result["scores"])
        self.assertIn("against", judge_result["scores"])

        judge_prompt = judge_call.call_args.args[0]
        self.assertEqual(events[0][0], "evidence")
        self.assertIn("Retrieved evidence excerpt.", judge_prompt)
        self.assertIn("supporting_quotes", judge_call.call_args.kwargs["response_schema"]["properties"])
        self.assertIn("Round 1:\nPro: Pro opening.", judge_prompt)
        self.assertIn("Round 2:\nPro: Pro round 2.\nAgainst: Against round 2.", judge_prompt)
        self.assertIn("Round 3:\nPro: Pro round 3.\nAgainst: Against round 3.", judge_prompt)
        self.assertEqual(len(pro_rebuttal_call.call_args_list[0].args[2]), 1)
        self.assertEqual(len(pro_rebuttal_call.call_args_list[1].args[2]), 2)
        self.assertEqual(pro_rebuttal_call.call_args_list[1].args[3], TEST_EVIDENCE)


if __name__ == "__main__":
    unittest.main()
