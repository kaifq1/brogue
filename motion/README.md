# Brogue film

A single-take film of one recorded benchmark task, made with [Remotion](https://www.remotion.dev). One sheet, one camera, no cuts: the request, the unaided answer with its made-up details struck through, the Brogue answer, the benchmark, the install line.

Every text and number comes from `src/data.json`, which `evals/build_motion.py` writes from a result file. Fonts ship in `public/fonts` (SIL Open Font License), so rendering needs no network.

```bash
npm install
python ../evals/build_motion.py ../evals/results/agent-final.json
npx remotion studio                                 # preview
npx remotion render Brogue ../assets/brogue-film.mp4
```

Remotion is free for individuals and small teams; see its license for company use.
