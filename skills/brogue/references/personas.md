# Readers

A persona is a set of writing decisions for one kind of reader. It is evidence about expectations, not a costume.

## The dimensions

| Dimension | Range | What changes on the page |
|---|---|---|
| Spelling | american, british | colour or color, organise or organize. British spelling covers the UK, India, Australia and most of the Commonwealth. |
| Register | formal, neutral, casual | Formal: full sentences, no contractions, salutation and sign-off. Casual: contractions, short paragraphs, fragments allowed. |
| Warmth | 0 to 3 | 0 gives information only. 3 acknowledges the person before the content. |
| Directness | 0 to 3 | 0 puts context before the request and softens it. 3 puts the ask in the first line. |
| Contractions | use, sparingly, avoid | |
| Sentence length | mean words | A target for the average. Variation around it matters more than hitting it. |
| Conventions | free text | Date format, currency and number style, how to open and close. |

## Order of evidence

1. What the user tells you about the reader.
2. A sample of writing by the reader or the author. Count contractions, measure sentence length, note the spelling and how they open and close. Mirror that. `brogue profile sample.txt` does the counting if the package is installed.
3. The channel and the content.
4. A preset below, as a starting point.

Age, country and job title predict how a person writes less well than three paragraphs they wrote. Use a preset when you have nothing better, and drop it when the evidence disagrees.

## Presets

| Name | Reader | Register | Direct | Notes |
|---|---|---|---|---|
| `neutral` | General adult | neutral | 2 | Default. |
| `corporate-us` | US manager or executive, 40s to 50s, at work | neutral | 3 | Decision or ask first, then the reason. `March 4, 2026`. |
| `corporate-uk` | UK professional at work | neutral | 1 | Understate. No sales energy. `4 March 2026`. |
| `corporate-in` | Senior professional in India, 45 to 60 | formal | 1 | Courteous open and close, context before the request, no contractions. Keep lakh and crore if the source has them. |
| `casual-us` | US adult, 20s to 30s, from a peer | casual | 3 | Short paragraphs, spoken rhythm. |
| `casual-in` | Urban India, 20s to 30s, from a peer | casual | 2 | Friendly and direct, British spelling. |
| `support-empathetic` | Someone stressed who needs help | casual | 2 | Name their problem once in their words, then one step per sentence. |
| `technical-terse` | Working engineer | neutral | 3 | Answer first, exact names and versions. |

These presets were written by the project's authors and have not been validated with members of the audiences they describe. Treat them as defaults to correct.

## What a persona must not do

- Add slang, regional words, code-switching or dialect markers that the source does not contain. A message to an Indian executive is formal standard English; it is not improved by "do the needful".
- Assume beliefs, humor or references from a demographic.
- Change the content. Different readers get the same facts in a different register. If the facts would have to change to suit the reader, stop and ask the user.

## Adding a persona

Copy any file in `src/brogue/personas/`, change the fields and pass the path: `brogue humanize draft.md --persona ./my-reader.toml`. When working without the package, write the same fields as a short brief and follow it.
