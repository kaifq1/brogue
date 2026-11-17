<div align="center">

# Brogue

**The writing skill that says only what you told it.**

AI drafts sound alive because the model fills the gaps: a feature you never shipped, a reason you never gave, a promise you never made.<br>Brogue writes for your reader, then checks every sentence against your request.

<br>

<table>
<tr>
<td align="center" width="25%"><h2>{B}</h2><sub>made-up details per text<br><b>with Brogue</b></sub></td>
<td align="center" width="25%"><h2>{RM}</h2><sub>with the next best skill<br>({R})</sub></td>
<td align="center" width="25%"><h2>{P}</h2><sub>with no skill</sub></td>
<td align="center" width="25%"><h2>{RATIO}×</h2><sub>fewer than the next best,<br>p {PR}</sub></td>
</tr>
</table>

<img src="assets/brogue-film.gif" alt="A 30-second single-take film: the request, the unaided answer with its made-up details struck through, the Brogue answer, and the benchmark" width="100%">

**[Live demo](https://{OWNER}.github.io/brogue/)** · **[Benchmark](evals/README.md)** · **[The skill](skills/brogue/SKILL.md)** · [Film (MP4)](assets/brogue-film.mp4)

</div>

## Install

```bash
npx skills add {REPO}
```

Works in Claude Code, Codex, Cursor and any agent that reads `SKILL.md`. As a Claude Code plugin:

```text
/plugin marketplace add {REPO}
/plugin install brogue@brogue
```

Then ask in plain words:

```text
write the investor update: revenue $84k, up from $71k; two deals slipped; 14 months of runway
clean this up before I send it, it sounds like ChatGPT wrote it
write this for our India country head, he is very formal
```

## One request, two answers

The request: *"{REQUEST}"*

Both answers are recorded outputs from the same model in the same kind of agent session. Struck through: what an auditor found that the request never said.

<table>
<tr><th width="50%">No skill · {PLAIN_N} made up</th><th width="50%">Brogue · 0 made up</th></tr>
<tr>
<td valign="top">

{PLAIN_TEXT}

</td>
<td valign="top">

{BROGUE_TEXT}

</td>
</tr>
</table>

## How it works

| | Step | What it prevents |
|---|---|---|
| **1** | **Find the reader.** Who reads it, what they do next, how they expect to be addressed, how they will use the page. | A blunt note to a senior client. Prose where an engineer wanted commands. |
| **2** | **Write from what you gave.** Every supplied fact goes in, plus what follows from them: the net of two figures, the decision they point to. Nothing about your situation that you did not supply. | The time-zone war story, the grateful customers, the "both are still active". |
| **3** | **Strike what you didn't say.** Each sentence is checked against the request. With a shell, the agent runs `scripts/ground.py`: a second model call that cuts unsupported statements and refuses any edit that adds or drops a number, link or quote. | Everything step 2 missed. A made-up detail reads as well as a true one, so no style rule catches it. |

Brogue also removes the machine patterns (the run-up, the staged contrast, the closing moral) and leaves a good human draft nearly untouched.

## Benchmark

Seven arms (no skill, Brogue and five open-source writing skills) wrote the same {TASKS} workplace tasks in real Claude Code sessions, each with only its own skill installed, all on Claude Haiku. Tasks were generated from job roles in [agency-agents](https://github.com/msitarzewski/agency-agents), not written by hand, and this set was run once, after the skill was frozen. Claude Sonnet audited every text against its request.

<img src="assets/arena.svg" alt="Made-up details per text by skill, with 95% intervals" width="100%">

| | Made-up details per text | 95% interval | Texts with none | Supplied facts left out |
|---|---|---|---|---|
{TABLE}

**Paired by task, Brogue made up less than every other skill**, by {MINGAP} to {MAXGAP} details per text, p ≤ {PMAX} in each comparison (sign-flip permutation test, tasks resampled).

**Readers do not pay for it.** A model played each task's reader and chose blind between Brogue's text and another skill's. Brogue was chosen in {PREF} of {PREFN} ballots ({PREFPCT}, 95% interval {PREFLO} to {PREFHI}). A reader cannot see which details are invented, so cutting them costs nothing a reader notices.

**Measured honestly.** The auditor is a model and is noisy, so the texts of Brogue and the runner-up were audited a second time, independently: {NOISE} per text, so the gap held. Brogue ran its grounding script in {GROUND} of {TEXTS} sessions; the rest it checked by hand. Readers and auditor are simulated. Every output, script and limit is in [`evals/`](evals/README.md), including the tuning rounds where Brogue lost.

## Compared with other writing skills

| | Brogue | Typical humanizer skill |
|---|---|---|
| Removes machine-writing patterns | ✓ | ✓ |
| Checks every sentence against the request | ✓ | – |
| Second-pass script that strikes unsupported statements | ✓ | – |
| Mechanical check on numbers, links and quotes | ✓ | – |
| Fits register to a named reader or region | ✓ | sometimes |
| Linter you can run in CI | ✓ | in one |
| Public benchmark against competing skills, with intervals | ✓ | – |

## The toolkit

The skill needs nothing but an agent. The Python package exposes the same steps for people who build with models. No dependencies.

```bash
pip install git+https://github.com/{REPO}
```

```bash
brogue write brief.md --persona corporate-uk   # write for a reader, then ground the result
brogue ground brief.md draft.md                # strike what the brief never said
brogue guard source.md rewrite.md              # did the rewrite keep every number, link and quote?
brogue lint draft.md --fail-at 30              # fail a CI job on dense machine patterns
brogue steer --persona corporate-uk            # a system-prompt fragment for any model
brogue profile my_writing.txt                  # a reader profile from a writing sample
brogue panel a.md b.md --jurors corporate-in,casual-us --deliberate
```

Commands that call a model use the `claude` CLI if it is installed, or any OpenAI-compatible endpoint through `BROGUE_BASE_URL`, `BROGUE_API_KEY` and `BROGUE_MODEL`.

```python
from brogue import ground, steer, load_persona

draft = my_model(steer(load_persona("support-empathetic")), request)
result = ground(request, draft, my_model)   # my_model: any function (system, user) -> text
print(result.text)      # the draft with unsupported statements removed
print(result.removed)   # what was struck
```

Eight reader presets ship as short TOML files: `neutral`, `corporate-us`, `corporate-uk`, `corporate-in`, `casual-us`, `casual-in`, `support-empathetic` and `technical-terse`. A persona sets register and conventions, never dialect: imitating a reader's speech reads as caricature to that reader.

## Limits

- English only, tested on workplace messages.
- {B} is low, not zero. Read anything that makes a claim about your product before you publish it.
- One writer model in the benchmark. Simulated readers. For a claim about real audiences, ask real people.
- No claim about AI detectors.

## Credits

Built after studying blader/humanizer, shir-danishyar/humanize, petergyang/no-ai-slop, hardikpandya/stop-slop, asavvin-pixel/unslop, anthropics/skills and obra/superpowers. Benchmark tasks are generated from msitarzewski/agency-agents; the comparison also runs in promptfoo. Details in [NOTICE.md](NOTICE.md). MIT licensed.
