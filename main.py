from core.debate_engine import run_debate
from core.debate_engine import MAX_ROUNDS, MIN_ROUNDS


def main():
    topic = input("Enter debate topic: ").strip()
    if not topic:
        print("A debate topic is required.")
        return

    while True:
        try:
            rounds = int(input(f"Select number of rounds ({MIN_ROUNDS}-{MAX_ROUNDS}): "))
            if MIN_ROUNDS <= rounds <= MAX_ROUNDS:
                break
        except ValueError:
            pass
        print(f"Enter a whole number from {MIN_ROUNDS} to {MAX_ROUNDS}.")

    print("\nStarting debate...\n")

    try:
        for step, data in run_debate(topic, rounds):
            if step == "judge":
                print("\nFinal Structured Output:\n")
                print(data)
                return
    except RuntimeError as exc:
        print(f"Debate could not be completed: {exc}")

    print("No final judge output was produced.")


if __name__ == "__main__":
    main()