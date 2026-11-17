"""Held-out tasks. The skill was never revised against these; they are only run to report."""

HELDOUT = [
    ("cover-note", "corporate-uk", "A short note at the top of a job application you are screening.",
     "Write a short cover note for a job application: 6 years as a backend engineer, mostly payments, "
     "applying for a staff engineer role at a UK fintech."),
    ("price-rise", "neutral", "An email from a software product you pay for.",
     "Write an email telling customers the monthly price goes from $12 to $15 on 1 March. "
     "Annual plans keep their price until renewal."),
    ("apology-outage", "support-empathetic", "A message from a service you rely on, after it went down.",
     "Write a message to users after a 3-hour outage on Tuesday caused by an expired certificate. "
     "No data was lost. Certificate renewal is now automated."),
    ("investor-update", "corporate-us", "A monthly update from a startup you invested in.",
     "Write the opening of a monthly investor update: revenue $84,000, up from $71,000; "
     "2 enterprise deals slipped to next quarter; runway 14 months."),
    ("decline-invite", "corporate-in", "A reply to a speaking invitation you sent.",
     "Write a reply declining an invitation to speak at a conference in Bengaluru in March, "
     "because of a prior commitment. Offer to join next year."),
    ("pr-description", "technical-terse", "A pull request description you have been asked to review.",
     "Write a pull request description: replaces the hand-rolled retry loop with exponential backoff, "
     "max 5 attempts, and adds a test for the 429 path."),
    ("neighbour-note", "casual-in", "A message in your apartment building's group chat.",
     "Write a message to the building group chat: the water will be off on Saturday from 10am to 1pm "
     "for tank cleaning, so fill buckets beforehand."),
    ("feedback-junior", "casual-us", "Feedback from your manager on a document you wrote.",
     "Write feedback to a junior colleague on their first design doc: the problem statement is clear, "
     "the alternatives section is missing, and the rollout plan needs dates."),
]
