# Reader panel

A panel answers one question: do the people this text is for prefer the new version to the old one? Run it when a rewrite is going to many readers, when the user asks for proof, or when you changed the skill and want to know whether it got worse.

## Why not judge it yourself

You wrote the rewrite, so you know which version is which and what it was trying to do. A reader knows neither. The panel recreates that: fresh readers, no labels, and the order swapped so a reader who always picks the first version cancels out.

## Running one with subagents

Use this when you can start subagents and no API key is configured.

1. Pick three to five readers that match the real audience. Use presets from `personas.md` or briefs the user gives you.
2. For each reader start two subagents with fresh context. Give each one only this:

   ```
   You are one specific reader: <persona brief>.
   Situation: <what the message is and why they received it>.

   VERSION A: <text>
   VERSION B: <text>

   Both say the same thing. Reply with one JSON object only:
   {"choice": "A" or "B", "human": {"A": 1-10, "B": 1-10},
    "fit": {"A": 1-10, "B": 1-10}, "why": "one sentence quoting the phrase that decided it"}
   ```

   In the first subagent the rewrite is A. In the second it is B. Do not say which is the rewrite, that either is AI-written, or what you hope to hear.
3. Count. The rewrite wins a ballot when the reader chose its label.

## Reading the result

| Result | Meaning | Do |
|---|---|---|
| Rewrite wins 60% or more, no reader below half | It landed | Ship it |
| Wins overall, one reader below half | Wrong register for that reader | Read their "why", adjust for them, rerun that reader |
| 40% to 60% | No real difference | Keep whichever is shorter |
| Below 40% | The rewrite is worse | Read every "why". The usual cause is lost warmth or a lost specific |
| A chosen far more than half the time | Readers picked by position | Rerun; the result means nothing |

Six ballots is a smoke test. Do not report percentages from it as findings; report the count and the reasons.

## With the package

```bash
brogue panel original.md rewrite.md --jurors corporate-in,casual-us --context "Launch email to existing customers"
```

Add `--mirofish http://localhost:5001` to run the same comparison inside a [MiroFish](https://github.com/666ghj/MiroFish) simulation, where readers are agents with memory who see each other's reactions before answering. That needs a running MiroFish server with its own LLM and Zep keys and takes minutes per run.

## What a panel cannot tell you

Simulated readers share the model's own taste. A model asked to play a 55-year-old executive produces a plausible reaction, and nobody has shown it matches what such executives prefer. Use panels to catch regressions and to hear objections you had not thought of. For a claim about real audiences, send both versions to real people.
