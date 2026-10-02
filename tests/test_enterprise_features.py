import unittest

from core.reporting import build_debate_report
from utils.llm_model.llm import call_llm, get_active_backend, set_active_backend


class EnterpriseFeatureTests(unittest.TestCase):
    def test_backend_switching_supports_mock_mode(self):
        set_active_backend("mock")
        self.assertEqual(get_active_backend(), "mock")
        response = call_llm("Evaluate which side is stronger.")
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 10)

    def test_debate_report_builds_exportable_payload(self):
        report = build_debate_report(
            topic="AI in healthcare",
            rounds=2,
            evidence=[{"id": "S1", "title": "Healthcare AI", "url": "https://example.com", "excerpt": "Example excerpt."}],
            result={
                "winner": "Pro",
                "scores": {
                    "pro": {"logic": 8, "clarity": 9, "examples": 8},
                    "against": {"logic": 7, "clarity": 7, "examples": 7},
                },
                "reason": "The Pro side was more persuasive.",
            },
            transcript=[{"round": 1, "pro": "Pro opening.", "against": "Against opening."}],
        )

        self.assertEqual(report["topic"], "AI in healthcare")
        self.assertEqual(report["winner"], "Pro")
        self.assertEqual(report["rounds"], 2)
        self.assertIn("evidence", report)
        self.assertIn("scores", report)
        self.assertIn("transcript", report)


if __name__ == "__main__":
    unittest.main()
