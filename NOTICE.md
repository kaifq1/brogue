# Prior work

Brogue was written after reading the projects below. No text or code was copied from them; the pattern catalog was rewritten and the linter is new. They are credited because the ideas are theirs.

| Project | License | What Brogue learned from it |
|---|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | MIT | The breadth of the pattern catalog, grouped by cause |
| [shir-danishyar/humanize](https://github.com/shir-danishyar/humanize) | MIT | Density over existence, register detection, a bundled linter, the no-invented-facts rule |
| [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) | MIT | Preserving the author's voice, minimum effective edit, the portability test |
| [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) | MIT | A short core skill with references loaded on demand |
| [asavvin-pixel/unslop](https://github.com/asavvin-pixel/unslop) | MIT | Calibrating to an author's style profile |
| [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 | Skill structure, progressive disclosure, the eval format in `evals/` |
| [obra/superpowers](https://github.com/obra/superpowers) | MIT | Trigger-only descriptions, positive recipes over prohibition lists |

## MiroFish

[666ghj/MiroFish](https://github.com/666ghj/MiroFish) is licensed AGPL-3.0. Brogue contains none of its code. `src/brogue/mirofish.py` is an HTTP client for a MiroFish server that you install and run separately. If you modify MiroFish or offer it as a network service, its license applies to that work.

## Benchmark tools and data

| Project | License | How Brogue uses it |
|---|---|---|
| [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | MIT | `evals/make_tasks.py` reads its role files to generate benchmark tasks; the generated tasks are in `evals/data/`. No role file is included. |
| [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | MIT | `evals/promptfoo/` runs the comparison as a promptfoo eval. promptfoo is installed separately. |
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | Remotion License | `motion/` renders the film. Remotion is installed separately and is free for individuals and small teams. |
| Newsreader, Hanken Grotesk, IBM Plex Mono | SIL Open Font License 1.1 | Font files in `motion/public/fonts` for rendering the film. |
