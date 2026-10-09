"""Who is who: the app whose creators we watch (Astra AI) and our app the scripts are written for (Memo AI).

Every prompt, check and message takes the names from here, so nothing about the apps is spread over the code.
"""
import re

# The app whose creators we watch (their viral videos are the source of our formats).
SOURCE = 'Astra AI'
SOURCE_DESC = 'Astra AI (the AI tutor / homework helper app from Slovenia: snap a photo of a task and get the solution)'
# Spoken and written forms, including speech-to-text mishearings ("Astra", "astraai", "astra.ai", "Astra A.I.").
# Serbo-Croatian and Slovenian decline the name: "na Astri AI", "uz Astru", "s Astrom", "z Astro", "od Astre".
SOURCE_RE = re.compile(r'\bastr(?:a|e|i|u|o|om|oj)(?:\s*-?\s*\.?\s*a\.?\s*i\b|ai\b|\b)', re.I)
SOURCE_TAGS = '#astraai, #astra_ai, #astra'

# Our app: every script says this name where the original says the source app.
OURS = 'Memo AI'
OURS_RE = re.compile(r'\bmemo\s*-?\s*a\.?\s*i\b', re.I)  # "Memo AI", "MemoAI", "memoai.eu" - each counts once
OURS_SITE = 'memoai.eu'  # what creators say / show as the website
OURS_TAGS = '#memoai, #memo_ai'
CUE = 'memo'                        # script cue: the moment the app is on screen
CUE_LABEL = 'Memo AI · memoai.eu/creator'  # label of the cue link (opens the app's filming version)
CATEGORY = 'AI study app'           # what both apps are, in a few words
TOPIC = 'school, studying and exams'  # what the videos are about ("same topic alone is not the same format")

# Checked against the Memo AI code on 8 Oct 2026 (repo M-AI). Scripts, reviews and directions may only use these.
FACTS = """What Memo AI (memoai.eu, web app on any phone or laptop) can do (only show/mention these): turn a recorded
or uploaded lecture, a PDF, Word or PowerPoint file, a web link, or up to 10 photos (taken with the in-app Scan camera
or from the gallery) of notes, textbook pages, worksheets or the board into: notes (formulas shown properly),
transcript, flashcards, a quiz with explanations, a graded practice test (percentage + feedback per answer), a mind
map, a podcast, read-aloud, a voice tutor that explains the material out loud topic by topic (you can interrupt it),
and an AI chat about the note. From a photo of a worksheet/exercises it writes notes that explain the method step by
step with worked examples. Making a note takes a few minutes (cut the waiting). The app speaks Slovenian, Croatian,
Bosnian and Serbian. Free start: one free note, then a 3-day free trial.
It does NOT have: an instant answer to a single photographed task ("snap and solve"), checking/grading the user's own
homework, photos in the chat, PDF export, pasting text, an Android app from the store. If the original shows an Astra
AI feature Memo AI does not have, replace that sentence with an equivalent step that exists (e.g. snap and solve ->
scan the worksheet, Memo AI explains how to solve it step by step), keeping the sentence count."""


def says_source(text):
    return bool(SOURCE_RE.search(text or ''))


def count_source(text):
    return len(SOURCE_RE.findall(text or ''))


def count_ours(text):
    return len(OURS_RE.findall(text or ''))
