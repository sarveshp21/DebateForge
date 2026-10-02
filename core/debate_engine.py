from agents.pro_agent import pro_agent, pro_rebuttal
from agents.against_agent import against_agent, against_rebuttal
from agents.judge_agent import judge_agent
from core.memory_manager import DebateMemory
from utils.evidence.wikipedia import fetch_topic_evidence

MIN_ROUNDS = 1
MAX_ROUNDS = 10


def run_debate(topic, rounds):
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("Debate topic must not be empty.")
    if not isinstance(rounds, int) or isinstance(rounds, bool) or not MIN_ROUNDS <= rounds <= MAX_ROUNDS:
        raise ValueError(f"Number of rounds must be between {MIN_ROUNDS} and {MAX_ROUNDS}.")

    evidence = fetch_topic_evidence(topic)
    yield "evidence", evidence

    memory = DebateMemory()

    # ------------------ ROUND 1 ------------------
    pro_output = pro_agent(topic, evidence)
    against_output = against_agent(topic, evidence)

    pro_text = pro_output["text"]
    against_text = against_output["text"]

    memory.store("round_1", {
        "pro": pro_text,
        "against": against_text
    })

    yield "round_1", {
        "pro": pro_text,
        "against": against_text
    }

    prev_pro = pro_text
    prev_against = against_text

    # ------------------ NEXT ROUNDS ------------------
    for r in range(2, rounds + 1):

        debate_history = [memory.get(f"round_{round_number}") for round_number in range(1, r)]
        pro_rebut_output = pro_rebuttal(topic, prev_against, debate_history, evidence)
        against_rebut_output = against_rebuttal(topic, prev_pro, debate_history, evidence)

        pro_text = pro_rebut_output["text"]
        against_text = against_rebut_output["text"]

        memory.store(f"round_{r}", {
            "pro": pro_text,
            "against": against_text
        })

        yield f"round_{r}", {
            "pro": pro_text,
            "against": against_text
        }

        prev_pro = pro_text
        prev_against = against_text

    # ------------------ JUDGE ------------------
    debate_rounds = [
        memory.get(f"round_{round_number}")
        for round_number in range(1, rounds + 1)
    ]
    judge_result = judge_agent(topic, debate_rounds, evidence)

    memory.store("judge", judge_result)

    yield "judge", judge_result