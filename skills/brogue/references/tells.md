# Tells

Each entry gives the linter rule id, what it looks like, and a fix that adds no facts. People use all of these. Fix them where several appear together.

## Contents

- Staging: `not-x-but-y`, `faux-insight`, `colon-reveal`, `filler`, `staccato`
- Inflation: `ai-vocab`, `soft-vocab`, `trailing-ing`, `copula-dodge`, `weasel-source`, `hedge-stack`
- Rhythm: `metronome`, `triad`, `em-dash`
- Endings and residue: `summary-closer`, `chatbot-residue`
- Formatting: `emoji-heading`, `bold-label-bullet`
- Not caught by the linter

## Staging

**`not-x-but-y`** Corrects a claim nobody made.
Before: Onboarding isn't just a process. It's a journey.
After: Onboarding takes most new users two sessions.
If you have no fact to put there, delete the sentence.

**`faux-insight`** Casts the writer as the one person who noticed.
Before: Here's what nobody tells you: distribution matters more than product.
After: Distribution matters more than product.

**`colon-reveal`** A noun phrase, a colon, a small drumroll.
Before: The best part: activation rose 22%.
After: Activation rose 22%.

**`filler`** Run-up before the point.
Before: It's worth noting that, when it comes to pricing, we changed two tiers.
After: We changed two pricing tiers.

**`staccato`** Fragments stacked for drama.
Before: Not just a number. A milestone. A turning point.
After: Delete it. The number in the previous sentence already made the point.

## Inflation

**`ai-vocab`** Words models reach for far more often than people do: delve, leverage, robust, seamless, pivotal, testament, tapestry, foster, streamline, empower, holistic, underscore, showcase.
Before: We leveraged robust tooling to streamline deployment.
After: We used Terraform to shorten deployment.
Use only tool names the source gives you. Without one: "We changed our tooling and deployment got shorter."

**`soft-vocab`** Words that are fine alone and literal: landscape, crucial, journey, navigate, enhance. Three in a paragraph is the tell. Replace the abstract ones with what they stand for.

**`trailing-ing`** A participle clause that tells the reader what the fact means.
Before: Setup time fell from 14 minutes to 6, highlighting the team's attention to detail.
After: Setup time fell from 14 minutes to 6.

**`copula-dodge`** A fancier verb where "is" or "has" belongs.
Before: The dashboard serves as a central hub and boasts twelve widgets.
After: The dashboard is where teams track orders. It has twelve widgets.

**`weasel-source`** Authority with no name attached.
Before: Studies show faster onboarding improves retention.
After, with a source: Our March cohort retained 8 points better after the redesign.
After, without one: I expect faster onboarding to help retention; we have not measured it.

**`hedge-stack`** Two hedges where one is honest.
Before: This could potentially reduce churn.
After: This may reduce churn.

## Rhythm

**`metronome`** Six or more sentences of nearly equal length. Combine two that belong together and let one stand short. Do not alternate long and short by rule; that is a second metronome.

**`triad`** Three items by reflex.
Before: fast, reliable, and scalable
After: Keep the one the paragraph goes on to support. If all three are real, give each a clause with its evidence.

**`em-dash`** More than one per three hundred words. Use a comma, a period or parentheses. Formal registers: none.

## Endings and residue

**`summary-closer`** A final paragraph that restates the piece. Delete it and end on the last concrete point or the next action.

**`chatbot-residue`** The assistant talking to its user inside the deliverable: "Great question!", "I hope this helps", "Let me know if you'd like me to", "As an AI". Delete on sight. This is the one rule with no exceptions.

## Formatting

**`emoji-heading`** Remove the emoji. If the document is under four hundred words, consider removing the headings too.

**`bold-label-bullet`** `- **Speed:** It is fast.` repeated down the page. Two sentences of prose usually carry it better. Keep the list when the items are separate, parallel things a reader will scan.

## Not caught by the linter

These need judgment and are the difference between clean text and good text.

- **Portable sentences.** If a sentence could move unchanged into a piece about another company or another person, it says nothing. Cut it or replace it with something true only here.
- **Synonym cycling.** "The tool", "the platform", "the solution" for one thing. Pick the name and repeat it.
- **Even paragraphs.** Every paragraph three sentences long, each opening with a topic sentence. Let one be a single line.
- **False balance.** "While X has benefits, it also has challenges" when the writer has a view. State the view.
- **Wrong reader.** Explaining what this reader knows, or skipping what they do not. No lint score fixes this; reread as them.
- **Over-correction.** Stripping every hedge, every adverb and every list produces a second recognisable style: clipped, flat, all short declaratives. If the result reads like a telegram, put some connective tissue back.
