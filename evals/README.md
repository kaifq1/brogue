# Evaluation

Everything Brogue claims is measured here, and everything measured here can be rerun with the scripts in this folder. They need no API key when the `claude` CLI is installed.

## The question

A writing skill can fail in two ways a reader cannot see. It can make things up: a feature nobody listed, a cause nobody confirmed, a promise nobody made. Or it can leave out something it was given. A third failure the reader can see: the text reads worse. The benchmark measures all three, on the same texts.

| Measure | Question | How |
|---|---|---|
| Made-up details | What does the text state as fact that the request never gave? | A second model reads the text beside the request and lists every such specific. `fidelity.py` |
| Left out | Which facts from the request are missing or changed? | The same auditor, the other way round, on texts written from a brief. `fidelity.py --omissions` |
| Reader preference | Which text would the intended reader pick? | A model plays the reader, told only who they are, and picks between Brogue's text and another skill's, blind, with the order alternating. `agent_arena.py` |

## How the skills are run

`agent_arena.py` runs each skill the way people use skills: inside a real agent session. For every task and every skill, a fresh headless Claude Code session starts with

- a clean configuration directory, so no skill or plugin installed on the machine leaks in;
- only the skill under test, loaded from its full published folder (SKILL.md, references and scripts);
- the same tools for every arm: Bash, Read, Write, Edit, Glob, Grep and Skill;
- the same message, which names the reader and asks for only the finished text, prefixed with "Use the <name> skill." for every skill arm.

The writer is Claude Haiku in every arm. Claude Sonnet is the auditor and the reader. The other skills are [blader/humanizer](https://github.com/blader/humanizer), [shir-danishyar/humanize](https://github.com/shir-danishyar/humanize) (humanize-writing), [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop), [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) and [asavvin-pixel/unslop](https://github.com/asavvin-pixel/unslop), at their main branches in November 2026. They are not redistributed here.

`arena.py` is the older harness: each SKILL.md pasted into a system prompt and one reply, the way a skill behaves in a plain API call. Its results are in `results/archive/`.

## Where the tasks come from

Tasks written by the skill's author can favour the skill without anyone meaning to. `make_tasks.py` has a model write them instead, from job roles in [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT), picked at random with a fixed seed: a tax strategist asking a CFO to approve a royalty change, an incident responder briefing a VP before a customer call, a level designer telling an artist about cut enemies. Each task has a reader, a brief with three to five facts, and a padded first draft for the rewrite form. The prompt that writes them says nothing about Brogue or about invented details.

Every task is run in two forms: written from the brief, and rewriting the draft.

## How the result was kept honest

The skill was revised five times against tuning sets. The final numbers come from a set of 24 tasks that was generated after the last revision and run once.

| Set | Tasks | Used for |
|---|---|---|
| `tasks-agency.json`, hand-written held-out set | 12 + 8 | tuning, round 1 |
| `tasks-agency-2.json`, `tasks-agency-3.json` | 24 | tuning, rounds 2 to 5 |
| `tasks-final.json` | 24 | the reported result, run once |

## Final result

<!-- final:start -->
Set `tasks-final.json`, run once with the frozen skill. Raw result: `results/agent-final.json`; summary: `results/summary.json`. Brogue ran its grounding script in 25 of 48 sessions.

48 texts per skill from 24 tasks (tasks-final). 95% intervals from 10,000 bootstrap resamples of tasks.

#### Made-up details per text

| Skill | Mean | 95% interval | Texts with none |
|---|---|---|---|
| **Brogue** | **0.94** | 0.60 to 1.31 | 24 of 48 |
| no-ai-slop | 1.44 | 1.08 to 1.81 | 13 of 48 |
| humanize-writing | 1.80 | 1.37 to 2.26 | 11 of 46 |
| stop-slop | 2.15 | 1.79 to 2.50 | 8 of 48 |
| humanizer | 2.19 | 1.65 to 2.73 | 16 of 48 |
| unslop | 2.29 | 1.77 to 2.85 | 7 of 48 |
| no skill | 2.31 | 1.75 to 2.85 | 10 of 48 |

#### Brogue minus each other skill, paired by task (negative means Brogue made up less)

| Against | Difference | 95% interval | p | Tasks where Brogue made up less / same / more |
|---|---|---|---|---|
| no skill | -1.38 | -1.92 to -0.83 | 0.0002 | 20 / 1 / 3 |
| humanize-writing | -0.83 | -1.28 to -0.39 | 0.0023 | 15 / 6 / 3 |
| humanizer | -1.25 | -1.67 to -0.83 | 0.0001 | 20 / 1 / 3 |
| no-ai-slop | -0.50 | -0.81 to -0.19 | 0.0097 | 15 / 4 / 5 |
| stop-slop | -1.21 | -1.52 to -0.90 | 0.0001 | 21 / 3 / 0 |
| unslop | -1.35 | -1.85 to -0.88 | 0.0001 | 19 / 2 / 3 |

#### Supplied facts left out per text (texts written from a brief)

| Skill | Mean | 95% interval | Texts missing something |
|---|---|---|---|
| humanizer | 0.04 | 0.00 to 0.12 | 1 of 24 |
| no skill | 0.04 | 0.00 to 0.13 | 1 of 23 |
| humanize-writing | 0.05 | 0.00 to 0.14 | 1 of 22 |
| stop-slop | 0.05 | 0.00 to 0.14 | 1 of 22 |
| no-ai-slop | 0.12 | 0.00 to 0.33 | 2 of 24 |
| unslop | 0.17 | 0.00 to 0.39 | 3 of 23 |
| Brogue | 0.18 | 0.05 to 0.36 | 4 of 22 |

#### The auditor's own noise

96 texts audited a second time, independently. The two counts differ by 0.25 per text on average; they agree on whether a text has any made-up detail in 90 of 96 (94%).
- Brogue: first audit 0.94, second audit 0.83 per text
- no-ai-slop: first audit 1.44, second audit 1.62 per text

#### Blind reader preference, Brogue against each

| Against | Brogue won | Share | 95% interval | p against a coin flip |
|---|---|---|---|---|
| no skill | 21 of 48 | 44% | 31% to 58% | 0.471 |
| humanize-writing | 19 of 48 | 40% | 27% to 54% | 0.193 |
| humanizer | 17 of 48 | 35% | 23% to 50% | 0.059 |
| no-ai-slop | 17 of 48 | 35% | 23% to 50% | 0.059 |
| stop-slop | 13 of 48 | 27% | 17% to 41% | 0.002 |
| unslop | 5 of 47 | 11% | 5% to 23% | 0.000 |
| all skills together | 92 of 287 | 32% | 27% to 38% | 0.000 |

#### Reading it

- **Made-up details:** Brogue is first, and the gap to every other skill is statistically clear. The second, independent audit moved both Brogue and the runner-up, and widened the gap between them.
- **Left out:** all skills are close, and Brogue is at the high end. Four of its 22 audited brief-written texts dropped something the request supplied.
- **Reader preference:** Brogue is not first. It is level with no skill and behind the other skills, clearly so against stop-slop and unslop. The reader model chose the longer text in most ballots, but length does not explain it all: when the two texts were within 20 words of each other, Brogue still won only about a third of the time. Readers' reasons, in the result file, mostly cite a fuller explanation, a stated reason or a friendlier offer. The open problem is to give readers that without supplying facts the writer never gave.
<!-- final:end -->

## What the tuning rounds found

Every round's raw results are in `results/tuning/`.

| Round | Change to the skill | Brogue made up | Best other skill | Readers picked Brogue over no-ai-slop |
|---|---|---|---|---|
| 1 | Version 4, as published before this round | 0.83 and 0.62 | 1.71 and 0.94 | not run |
| 2 | Supplied facts must all appear; a written workflow with grounding as step 3 | 0.67 and 0.50 | 1.62 and 1.38 | 5 of 24, 5 of 24 |
| 3 | Deriving from the facts (a net figure, a weekday) is allowed and encouraged | 0.61 | 1.92 | 7 of 24 |
| 4 | No drafting notes or signature placeholders when only the text was asked for; answer first; invitations to reply are not promises | 0.67 | 1.92 | 7 of 24 |
| 5 | Length comes from what was supplied plus what follows from it; conditional offers of things the request says exist are allowed | 0.83 | 1.92 | 10 of 24 |

Round 2 is the instructive one. Brogue made up the least of any skill, and readers chose it in only one ballot in five. Their reasons were consistent: the other texts did the arithmetic ("the net cost is about $110K a year"), gave the reason for the ask, offered a next step, and Brogue's had cut all three. The auditor of that round counted the net figure as made up, because the request gave the two numbers and not their difference. Tuning against that auditor had taught the skill to withhold the conclusion a reader needs.

Two things changed in response. The skill now separates deriving (allowed, and shown) from supplying (not allowed). And the auditor prompt now leaves out correct arithmetic and general explanations; the earlier prompt is kept as `SYSTEM_V1` in `fidelity.py`. Rounds 1 and 2 used the old auditor, so their numbers do not compare directly with later rounds.

## Limits

- One writer model. Other models may rank the skills differently.
- The auditor and the readers are models from the same family as the writer. They are a screen, not people.
- The auditor is noisy. The same texts audited twice can differ by a few tenths per text; the final result section reports a second, independent audit.
- In agent sessions Brogue does not always run its grounding script; the final result section says how often it did.
- The tasks are workplace messages in English. Fiction, long-form essays and other languages are not tested.
- Ballots are one per pair per task form. With 48 ballots per rival, a preference closer to half than about 15 points is not distinguishable from a coin flip.

## Rerun it

```bash
pip install -e .
git clone --depth 1 https://github.com/msitarzewski/agency-agents /tmp/agency-agents
git clone https://github.com/blader/humanizer rivals/humanizer   # and the others, one folder each

python evals/make_tasks.py /tmp/agency-agents --n 24 --seed 29 --out evals/data/my-tasks.json
python evals/agent_arena.py --skills-dir rivals --tasks evals/data/my-tasks.json --no-duels --out run.json
python evals/fidelity.py run.json
python evals/fidelity.py run.json --omissions
python evals/agent_arena.py --skills-dir rivals --tasks evals/data/my-tasks.json --out run.json   # reader duels
python evals/stats.py run.json
python evals/build_site.py run.json && python evals/build_motion.py run.json
```

To run the comparison in [promptfoo](https://github.com/promptfoo/promptfoo) instead, see `promptfoo/promptfooconfig.yaml`: the same auditor scores each output as a promptfoo assertion.

```bash
cd evals/promptfoo && npx promptfoo@latest eval && npx promptfoo@latest view
```
