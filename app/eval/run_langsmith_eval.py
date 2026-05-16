from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langsmith import Client, evaluate

from app.agents.baseline_agent import run_baseline
from app.agents.crew_agent import run_crew


load_dotenv(override=True)


BASE_DIR = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = BASE_DIR / "app" / "eval" / "golden_set.json"

DATASET_NAME = "lesson-11-personal-finance-crew-golden-set"


def load_golden_set() -> list[dict[str, Any]]:
    with GOLDEN_SET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_or_create_dataset(client: Client, golden_set: list[dict[str, Any]]):
    """
    Створює LangSmith dataset, якщо його ще немає.
    Якщо dataset уже існує — використовує його повторно.
    """
    try:
        return client.read_dataset(dataset_name=DATASET_NAME)
    except Exception:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Golden set for Lesson 11 Personal Finance Crew",
        )

        examples = [
            {
                "inputs": {
                    "question": case["question"],
                },
                "outputs": {
                    "case_id": case["id"],
                    "expected_intent": case["expected_intent"],
                    "expected_tool": case["expected_tool"],
                    "must_include": case.get("must_include", []),
                    "forbidden_phrases": case.get("forbidden_phrases", []),
                },
            }
            for case in golden_set
        ]

        client.create_examples(
            dataset_id=dataset.id,
            examples=examples,
        )

        return dataset


def trace_to_tool_names(trace: list[Any]) -> list[str]:
    tool_names = []

    for step in trace:
        name = getattr(step, "name", None)
        if name:
            tool_names.append(name)

        output = getattr(step, "output", None)
        if isinstance(output, dict) and output.get("tool_name"):
            tool_names.append(output["tool_name"])

    return tool_names


def trace_to_intent(trace: list[Any]) -> str | None:
    for step in trace:
        output = getattr(step, "output", None)
        if isinstance(output, dict) and output.get("intent"):
            return output["intent"]

    return None


def baseline_target(inputs: dict[str, Any]) -> dict[str, Any]:
    response = run_baseline(
        question=inputs["question"],
        session_id="langsmith-eval",
    )

    return {
        "architecture": "baseline",
        "answer": response.answer,
        "tools": trace_to_tool_names(response.trace),
        "intent": trace_to_intent(response.trace),
        "trace_steps": len(response.trace),
    }


def crew_target(inputs: dict[str, Any]) -> dict[str, Any]:
    response = run_crew(
        question=inputs["question"],
        session_id="langsmith-eval",
    )

    return {
        "architecture": "crew",
        "answer": response.answer,
        "tools": trace_to_tool_names(response.trace),
        "intent": trace_to_intent(response.trace),
        "trace_steps": len(response.trace),
    }


def tool_selection_accuracy(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> bool:
    expected_tool = reference_outputs["expected_tool"]

    if expected_tool == "none":
        tools = outputs.get("tools", [])
        answer = outputs.get("answer", "").lower()

        return (
            tools == []
            or "none" in tools
            or ("поза" in answer and "скоуп" in answer)
            or "out_of_scope" in answer
        )

    return expected_tool in outputs.get("tools", [])


def groundedness_proxy(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> bool:
    answer = outputs.get("answer", "").lower()

    return all(
        str(value).lower() in answer
        for value in reference_outputs.get("must_include", [])
    )


def no_forbidden_phrases(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> bool:
    answer = outputs.get("answer", "").lower()

    return not any(
        str(value).lower() in answer
        for value in reference_outputs.get("forbidden_phrases", [])
    )


def run_experiment(architecture: str, dataset_name: str):
    if architecture == "baseline":
        target = baseline_target
    elif architecture == "crew":
        target = crew_target
    else:
        raise ValueError("architecture must be baseline or crew")

    return evaluate(
        target,
        data=dataset_name,
        evaluators=[
            tool_selection_accuracy,
            groundedness_proxy,
            no_forbidden_phrases,
        ],
        experiment_prefix=f"lesson-11-{architecture}",
        description=f"Lesson 11 Personal Finance Coach eval for {architecture}",
        max_concurrency=1,
        metadata={
            "architecture": architecture,
            "course": "robot_dreams AI Engineering",
            "lesson": "11",
            "type": "personal-finance-agent-eval",
        },
    )


def main() -> None:
    client = Client()
    golden_set = load_golden_set()

    dataset = get_or_create_dataset(client, golden_set)

    print(f"LangSmith dataset: {dataset.name}")

    print("Running baseline experiment...")
    run_experiment("baseline", dataset.name)

    print("Running crew experiment...")
    run_experiment("crew", dataset.name)

    print("Done. Check LangSmith project:")
    print("lesson-11-personal-finance-crew")


if __name__ == "__main__":
    main()