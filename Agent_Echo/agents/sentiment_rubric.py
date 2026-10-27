"""Versioned sentiment definitions shared by classification and semantic review."""

SENTIMENT_LABELS = ("positive", "negative", "neutral", "mixed", "indeterminate")
SENTIMENT_RUBRIC_VERSION = "survey-sentiment-v3"
SENTIMENT_RUBRICS = {
    "survey-sentiment-v1": """positive: clearly favorable; negative: clearly critical;
neutral: descriptive without expressed favorable/critical evaluation;
mixed: both favorable and critical evaluations;
indeterminate: empty, unclear, irrelevant or insufficient text. Do not guess.""",
    "survey-sentiment-v2": """Classify the complete response, including qualifications and negation.
positive: favorable evaluation without an explicit current criticism;
negative: critical evaluation without an explicit favorable evaluation;
neutral: descriptive without expressed favorable or critical evaluation;
mixed: both favorable and explicitly critical evaluations, even when the overall verdict
is positive or negative. An explicit remaining problem counts as criticism; an aspiration
to continue a good practice, a future suggestion, a resolved past problem or initial doubt
does not by itself establish current criticism. Judge their meaning in the full response.
indeterminate: empty, unclear, irrelevant or insufficient text. Do not guess.
Mixed is not a midpoint or a category close to neutral. Full classification means every
eligible comment has a label, including indeterminate when warranted; it does not imply
zero indeterminate comments. Report category counts from the actual assigned labels.
Examples: 'Helpful overall, but access still fails.' -> mixed;
'I feel appreciated; please keep this practice going.' -> positive;
'We meet on Mondays.' -> neutral; 'N/A' -> indeterminate.
Labels remain provisional until human validation.""",
    SENTIMENT_RUBRIC_VERSION: """positive: favorable sentiment;
negative: unfavorable sentiment;
neutral: descriptive without a clear favorable or unfavorable evaluation;
mixed: contrasting favorable and unfavorable evaluations;
indeterminate: insufficient, unclear or irrelevant text for a meaningful classification.
Use the complete response and its context to choose the best-fitting category. These
definitions guide semantic judgment; isolated words or a closing phrase do not determine
the label. Briefly justify the interpretation, acknowledging material ambiguity when
present. Labels remain provisional until human validation.""",
}
