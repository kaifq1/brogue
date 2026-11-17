---
name: brogue
description: Use when writing or editing prose that a person will read (emails, posts, replies, support messages, articles, copy, reports) and when asked to humanize text, make it sound natural or less robotic, remove AI patterns, match a tone, or fit a specific audience, region or reader. Also use when asked whether a draft sounds AI-written or to test how a draft lands with different readers. Not for code, commit messages, config, or legal text where formula is the point.
license: MIT
---

# Brogue

Write what one particular person needs to read, the way someone who knows them would write it.

Machine prose fails in two directions. The familiar one is padding: the run-up, the balanced triple, the closing moral. The less familiar one comes from fixing the first too hard: clipped, tidy, noun-heavy text that reads like product copy. Both come from writing for nobody in particular. So start with the reader, and let the cutting follow from that.

## The workflow

1. List what the request supplied, and answer the four reader questions below.
2. Write the draft.
3. **Ground it.** If you have a shell, this step is not optional: write the request to `request.txt` and your draft to `draft.txt` in a scratch folder, then run `python <this skill's base directory>/scripts/ground.py request.txt draft.txt`. Use what it prints as your text. Without a shell, do the check by hand as described under "Check before delivering".
4. Read it once as the reader, then deliver the text.

A draft always reads fine to its writer; the made-up parts sound as natural as the true ones. Step 3 is the only reliable way to find them, so do not skip it because the draft looks clean.

## Three rules that outrank style

1. **The request is everything you know about the writer's world.** Split what you know into two piles. *World knowledge* is true for anyone: how a bucket policy works, what a design doc is for. Use it freely. *Situation facts* are about this writer, their product, their team and what happened: only the user or the source text can supply those, and whatever they did not supply does not exist. That rules out, however natural it would sound:
   - product features, materials, benefits and instructions for use that nobody listed ("connect it in settings");
   - backstory, causes and reasons ("we found it in testing", "users kept asking for this");
   - the state of things ("the analysis is complete", "it's live for everyone");
   - commitments on the writer's behalf: a specific thing they will do, or a time they will do it by ("I'll send the report by Friday"). An open invitation to respond is not a commitment and is usually welcome: "if this doesn't work for you, tell me". Nor is a conditional offer of something the request says exists: "I can send the pilot results ahead of time if that helps";
   - what the rest of a document goes on to say ("this proposal sets out the costs");
   - names, numbers, dates, durations, quotes, and the gender of a person you were not told;
   - a scene told as if it happened ("a customer booked a slot and it never showed up").

   **Length comes from what was supplied, not from the format.** A complete text carries every supplied fact, the conclusion they add up to, the reason behind the ask, and the next step with its deadline. That is often more than the facts alone and seldom more than a screen. Past that point, the length the request did not pay for is exactly where invention goes: do not pad toward the usual length of a post or an email. If the result still feels thin, ask the user for more, never supply it.

   When a sentence wants a detail you lack, write the sentence without it. Use a bracketed placeholder only where the text cannot be sent without the missing piece, such as a name in a greeting. When the piece explains or argues, world knowledge carries it: state it as general ("usually", "in most teams"), without a made-up figure, and mark an illustration as one ("say two developers disagree"). Give a cause as a condition unless it was confirmed: "if the policy no longer allows the role, the write fails."
   **What follows from the facts is yours to say, and the reader usually needs it most.** Arithmetic on supplied numbers (the net of a gain and a loss, a change in percent, a weekday of a given date), a consequence that follows by plain logic, and what a supplied fact means in general terms are not invention. They are the reason the reader asked for a writer and not a list. Work them out, show how in a few words ("at 12.5%, Irish tax falls by about $163K, so the net cost is about $110K a year"), and lead with the conclusion the reader's decision turns on. The line is between deriving and supplying: derive freely from what you were given, never supply a new fact about the situation.
2. **Keep everything you were given, and what is checkable verbatim.** Numbers, URLs, quotations, code, proper nouns. Every supplied fact goes in, as specific as it was given: "a UK fintech" stays "a UK fintech", never "[Company]". When the request tells you to say, offer or ask something, that is supplied content too, and it goes in. Change how a thing is said and leave what is said alone.
3. **Match the reader's register, never perform their identity.** Adapting to a reader in Mumbai or Manchester means their spelling, their date format, their expected formality. It does not mean local phrases, slang or an accent. That reads as caricature to the people it imitates.

## Before writing, answer four questions

First list, for yourself, what the request supplied: each fact, number and name, and each thing it asks the text to say or do. That list is the whole content. The questions below decide its form.

Answer them from what the user said, a sample of the reader's or author's own writing if there is one, and the channel. A sample is the best evidence: mirror its sentence length, contractions, spelling and formality. Read `references/personas.md` when the reader is in another region or setting, or the user names a persona.

1. **Who is reading, and what is their relationship to the writer?** A peer, a boss, a client, a stranger, someone upset. This sets everything else. If nobody said, write for an intelligent stranger in plain standard English and do not guess a persona.
2. **What will they do after reading?** Decide, reply, run a command, feel reassured, buy, nothing. Whatever the user supplied that serves it must be on the page and easy to find: the ask, the time, the next step, the command. Cutting those is not concision.
3. **How do they expect to be addressed?** This decides directness and courtesy together.
   - Someone senior, formal, or owed something (a client, an official, an elder): ask, do not announce. "I am writing to ask whether we could move the review" is the correct sentence, where "We need to move the review" reads as a decision made over their head. A greeting, a proper sign-off and one apology are part of the register.
   - A busy colleague or manager: the result or the ask in the first line, then the reason.
   - A peer or a friend: how you would say it out loud.
   - Someone upset: name their problem once in their own terms, then what happens next and when.
4. **How will they use the page?** Someone who will run it gets commands in code blocks and steps as numbered steps. Someone who will skim gets the answer first and short paragraphs. Someone who will read gets prose.

## Then write it

**Answer first, in the words you would say it in.** If the reader has a decision to make, the first line is the answer in its plainest form: "Don't ship yet." is better than "We recommend not shipping at this time." Then the reason, then what happens next.

**Say it the way you would say it to them.** Read each sentence as speech. "Two people editing the same booking broke it in ways we only saw once real customers used it" is a person talking. "Conflicting edits surfaced in production" is the same fact compressed into nouns, and it sounds like a press release. Prefer the event to the abstraction and the verb to the noun.

**Use every fact you were given.** Supplied facts are what make text specific, so none should go missing or get blurred into a general statement. "No data was lost" stays in, in those words. If the cause of something was not given, do not supply one; say what is known. Stating a likely cause as a confirmed one is a common way to sound confident and be wrong.

**Cut what serves nobody.** The run-up ("It's worth noting", "In today's world"). Anything addressed to the conversation and not the reader ("Great question", "I hope this helps"). The sentence that would be equally true of another company. The claim that tells the reader what a fact means ("highlighting our commitment"). The summary of what they just read. The last line built to be quoted.

**State claims directly.** "It isn't X, it's Y" corrects a view nobody held. Write Y. Name a source or own the claim; "studies show" names nobody.

**Use plain verbs and the same noun twice.** "Is" and "has" over "serves as" and "boasts". A dashboard in one sentence is still a dashboard in the next.

**Let length follow content.** A short sentence after a long one is how people write. Three clipped fragments in a row is staging, and so is a list of three adjectives where one carries the weight. Hedge once, where you are unsure.

**Format for use.** Prose for reading, code blocks for anything to be run, steps for procedures, a list when items are parallel and separate. A reader acting under time pressure (on a call in five minutes, triaging a queue) is best served by short labelled lists: what you can say, what you can't. No emoji in headings, no bold scattered for emphasis, and em dashes at most once in three hundred words.

The catalog of patterns with before and after pairs is in `references/tells.md`. Read it when a draft still reads wrong and you cannot say why.

## Editing someone's draft

Their voice is the asset. Keep opinions, bluntness, humor, digressions that carry character, and honest doubt. Fix the machine patterns around them and leave good sentences exactly as they are. A rough draft with a real voice should sound like the same person afterward.

To decide how much to change, run `python scripts/lint.py <file>` when you can run commands (text on stdin also works). Below 10, leave it alone unless it is wrong for the reader. From 10 to 29, fix the flagged lines. From 30, rebuild the sentences and keep the content and order. Without the script, apply the same judgment: count the patterns from the section above and rewrite only where they cluster.

## Check before delivering

**Ground it before delivering.** A draft always carries more than the request did, so check it as a separate pass. With a shell, run `scripts/ground.py` as step 3 of the workflow says. It sends the request and the draft to a second model call, prints the draft with unsupported statements removed and lists what it removed; deliver what it prints. It refuses any correction that adds a number, link or quote, or drops one the request supplied. When you cannot run it, do the same pass yourself:

1. Go through the draft one sentence at a time. For each statement about the writer's situation, point to the words in the request that say so. If you cannot, delete the statement or cut it back to what was said. A sentence about what happened, what will happen, how the product works or why something occurred needs a source like any number does. So does an offer or a follow-up the writer never proposed ("would any time that week work?", "I'll send the result"), and so does a weekday you worked out from a date.
2. Go through your list from before writing. Each supplied fact and each requested element is in the text, unchanged.
3. Mend any sentence a deletion broke, with the fewest words. Add nothing new.

Expect the text to get shorter. If you can think before answering, run this on a draft in your head and deliver only the result. If someone asks you to review or check a draft, this is the review.

Then read it once as the reader and confirm:

- they can do what they need to do next from this text alone;
- the tone matches the relationship, neither stiffer nor blunter than they would expect;
- every number, name, link and quote from the source is present and unchanged;
- it does not read like a telegram. If every sentence is short and declarative, restore the connecting words.

Deliver the text first, with no preamble and no list of changes. After it, add a "Check before sending" note only when the source left something the user has to decide, one line each:

- a claim with no source that you kept, softened or dropped;
- a number whose meaning is unclear (22% of what, compared with when);
- a specific the text needs and you were not given, or one that would make it stronger and only the user knows. Ask for it; never fill it in.

If none of these apply, the text is the whole reply. When the user asks for the text alone ("reply with only the text", "just the email"), the reply is the text and nothing else: no note, no comment on what you changed, even when something is missing. Do not end with a signature placeholder such as "[Your name]"; end with the sign-off, or the writer's name if you know it. When the user asks only whether a draft sounds machine-written, report the patterns you find with the lines quoted, and do not guess at authorship.

## When to leave it alone

- The user asked for the element: bullets, a formal template, a specific phrase. Their instruction wins.
- A flagged word is the accurate one. "Robust" is correct for a statistical estimator.
- Quoted third-party text. Never edit a quotation.
- One pattern on its own. People use every pattern in the catalog; the tell is several in one passage.
- Perfect grammar, formal vocabulary and plain blandness are not tells.

## Testing how it lands

When the user asks whether a rewrite is better for an audience, or the text will go to many people, read `references/panel.md` and run a blind reader panel instead of judging it yourself. The writer of a text is a poor judge of it.
