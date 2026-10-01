"""Validate multi-step agent traces with AgentFlowCheck.

python examples/agent_pipeline_check.py
"""

import json

from privacyprobe import AgentFlowCheck, Suite

# Allowed state machine for a retrieval-augmented support agent.
TRANSITIONS = {
    "plan": ["retrieve", "answer"],
    "retrieve": ["retrieve", "rerank", "answer"],
    "rerank": ["answer"],
    "answer": ["review"],
    "review": ["answer", "done"],
}

check = AgentFlowCheck(
    TRANSITIONS,
    start="plan",
    terminal={"done"},
    required=["review"],  # every answer must be reviewed
    max_steps=10,
)

cases = [
    {
        "prompt": "Refund policy for damaged items?",
        "trace": ["plan", "retrieve", "rerank", "answer", "review", "done"],
    },
    {
        # Skips review: the agent jumped straight from answer to done.
        "prompt": "Shipping time to Pune?",
        "trace": [{"state": "plan"}, {"state": "retrieve"}, {"state": "answer"}, {"state": "done"}],
    },
    {
        # Trace returned by the agent itself as JSON in the response.
        "prompt": "Cancel my order",
        "response": json.dumps(
            {"steps": [{"tool": "plan"}, {"tool": "answer"}, {"tool": "review"}]}
        ),
    },
]

result = (
    Suite().add(check).run([{**c, "response": c.get("response", "<agent output>")} for c in cases])
)
print(result.summary())
for r in result.results:
    print(f"{'PASS' if r.passed else 'FAIL'}  {r.prompt:<35} {r.details}")
