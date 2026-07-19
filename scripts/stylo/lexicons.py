"""Word lists used by the stylometry engine.

Everything here is a plain frozenset or tuple so the engine stays
dependency-free. Lists are deliberately conservative: it is better to
undercount a category than to inflate it with ambiguous words.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Function words
# ---------------------------------------------------------------------------
# The classic stylometric feature set: high frequency, low topic-dependence.

ARTICLES = frozenset({"a", "an", "the"})

FIRST_PERSON = frozenset(
    {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"}
)
SECOND_PERSON = frozenset({"you", "your", "yours", "yourself", "yourselves", "thou", "thee", "thy", "thine"})
THIRD_PERSON = frozenset(
    {
        "he", "him", "his", "himself",
        "she", "her", "hers", "herself",
        "it", "its", "itself",
        "they", "them", "their", "theirs", "themselves",
        "one", "oneself",
    }
)
MASCULINE_PRONOUNS = frozenset({"he", "him", "his", "himself"})
FEMININE_PRONOUNS = frozenset({"she", "her", "hers", "herself"})
PLURAL_THIRD_PRONOUNS = frozenset({"they", "them", "their", "theirs", "themselves"})
NEUTER_PRONOUNS = frozenset({"it", "its", "itself"})

ALL_PRONOUNS = FIRST_PERSON | SECOND_PERSON | THIRD_PERSON

DEMONSTRATIVES = frozenset({"this", "that", "these", "those"})

COORDINATORS = frozenset({"and", "but", "or", "nor", "yet", "so", "for"})

SUBORDINATORS = frozenset(
    {
        "after", "although", "as", "because", "before", "how", "if", "once",
        "since", "than", "that", "though", "till", "unless", "until", "when",
        "whenever", "where", "whereas", "wherever", "whether", "while", "whilst",
        "lest", "provided", "supposing",
    }
)

# Subordinators that are safe to trust in sentence-initial position.
# ("that", "as", "than", "how" open too many non-subordinate sentences.)
SUBORDINATE_OPENERS = frozenset(
    {
        "after", "although", "as", "because", "before", "if", "once", "since",
        "though", "unless", "until", "when", "whenever", "where", "wherever",
        "whether", "while", "whilst", "lest",
    }
)

RELATIVIZERS = frozenset({"who", "whom", "whose", "which", "that", "where", "when"})

PREPOSITIONS = frozenset(
    {
        "about", "above", "across", "after", "against", "along", "amid", "among",
        "amongst", "around", "at", "before", "behind", "below", "beneath",
        "beside", "besides", "between", "beyond", "by", "down", "during",
        "except", "for", "from", "in", "inside", "into", "like", "near", "of",
        "off", "on", "onto", "opposite", "out", "outside", "over", "past",
        "round", "since", "through", "throughout", "till", "to", "toward",
        "towards", "under", "underneath", "until", "up", "upon", "with",
        "within", "without",
    }
)

MODALS = frozenset(
    {
        "can", "could", "may", "might", "must", "shall", "should", "will",
        "would", "ought", "cannot", "shan't", "won't", "wouldn't", "couldn't",
        "shouldn't", "mustn't", "can't", "mightn't",
    }
)

NEGATIONS = frozenset(
    {
        "no", "not", "none", "nobody", "nothing", "nowhere", "never", "neither",
        "nor", "n't", "cannot", "without",
    }
)

QUANTIFIERS = frozenset(
    {
        "all", "any", "both", "each", "either", "enough", "every", "few",
        "fewer", "less", "little", "many", "more", "most", "much", "several",
        "some", "such",
    }
)

BE_FORMS = frozenset({"am", "is", "are", "was", "were", "be", "been", "being"})
HAVE_FORMS = frozenset({"have", "has", "had", "having"})
DO_FORMS = frozenset({"do", "does", "did", "doing", "done"})
AUXILIARIES = BE_FORMS | HAVE_FORMS | DO_FORMS | MODALS

FUNCTION_WORDS = (
    ARTICLES
    | ALL_PRONOUNS
    | DEMONSTRATIVES
    | COORDINATORS
    | SUBORDINATORS
    | RELATIVIZERS
    | PREPOSITIONS
    | MODALS
    | NEGATIONS
    | QUANTIFIERS
    | AUXILIARIES
    | frozenset({"there", "here", "then", "now", "also", "very", "too", "just",
                 "only", "even", "still", "again", "well", "so", "quite",
                 "rather", "almost", "always", "sometimes", "often", "yes"})
)

# Named groups reported in the function-word profile section.
FUNCTION_WORD_GROUPS = (
    ("articles", ARTICLES),
    ("first_person_pronouns", FIRST_PERSON),
    ("second_person_pronouns", SECOND_PERSON),
    ("third_person_pronouns", THIRD_PERSON),
    ("demonstratives", DEMONSTRATIVES),
    ("coordinating_conjunctions", COORDINATORS),
    ("subordinating_conjunctions", SUBORDINATORS),
    ("prepositions", PREPOSITIONS),
    ("modals", MODALS),
    ("negation", NEGATIONS),
    ("quantifiers", QUANTIFIERS),
    ("be_forms", BE_FORMS),
    ("have_forms", HAVE_FORMS),
    ("do_forms", DO_FORMS),
)

# ---------------------------------------------------------------------------
# Dialogue mechanics
# ---------------------------------------------------------------------------

# "said"/"asked"/"replied" are the plain workhorses; everything else in
# SPEECH_VERBS counts as a marked alternative.
NEUTRAL_TAGS = frozenset({"said", "says", "say"})

SPEECH_VERBS = frozenset(
    {
        "said", "says", "say", "asked", "asks", "ask", "replied", "replies",
        "reply", "answered", "answers", "answer", "cried", "cries", "cry",
        "exclaimed", "exclaims", "shouted", "shouts", "called", "calls",
        "whispered", "whispers", "murmured", "murmurs", "muttered", "mutters",
        "retorted", "retorts", "declared", "declares", "remarked", "remarks",
        "observed", "observes", "added", "adds", "continued", "continues",
        "began", "begins", "responded", "responds", "returned", "returns",
        "demanded", "demands", "inquired", "inquires", "queried", "queries",
        "protested", "protests", "insisted", "insists", "agreed", "agrees",
        "admitted", "admits", "confessed", "confesses", "explained", "explains",
        "repeated", "repeats", "suggested", "suggests", "put", "went",
        "gasped", "gasps", "laughed", "laughs", "sighed", "sighs", "groaned",
        "groans", "growled", "growls", "snapped", "snaps", "stammered",
        "stammers", "faltered", "falters", "interrupted", "interrupts",
        "broke", "breaks", "echoed", "echoes", "assented", "assented",
        "acknowledged", "acknowledges", "announced", "announces", "urged",
        "urges", "warned", "warns", "ordered", "orders", "commanded",
        "commands", "pleaded", "pleads", "begged", "begs", "wondered",
        "wonders", "mused", "muses", "reflected", "reflects", "grumbled",
        "grumbles", "chuckled", "chuckles", "screamed", "screams", "yelled",
        "yells", "hissed", "hisses", "drawled", "drawls", "ventured",
        "ventures", "objected", "objects", "concluded", "concludes",
        "queried", "resumed", "resumes", "persisted", "persists",
    }
)

# Verbs that are speech verbs but carry visible attitude/volume/manner.
MARKED_TAGS = SPEECH_VERBS - NEUTRAL_TAGS - frozenset(
    {"asked", "asks", "ask", "replied", "replies", "reply",
     "answered", "answers", "answer"}
)

# ---------------------------------------------------------------------------
# Verb / tense heuristics
# ---------------------------------------------------------------------------

IRREGULAR_PAST = frozenset(
    {
        "was", "were", "had", "did", "said", "went", "came", "saw", "took",
        "got", "made", "knew", "thought", "found", "gave", "told", "became",
        "left", "felt", "put", "brought", "began", "kept", "held", "wrote",
        "stood", "heard", "let", "meant", "met", "ran", "paid", "sat", "spoke",
        "lay", "led", "grew", "lost", "fell", "sent", "built", "understood",
        "drew", "broke", "spent", "cut", "rose", "drove", "bought", "wore",
        "chose", "read", "set", "shut", "spread", "taught", "threw", "caught",
        "fought", "flew", "hid", "hit", "hurt", "knelt", "lit", "rode", "rang",
        "sang", "sank", "shook", "shone", "shot", "slept", "slid", "spun",
        "sprang", "stole", "stuck", "struck", "swept", "swore", "swam", "swung",
        "tore", "woke", "wound", "won", "withdrew", "bent", "bound", "bled",
        "blew", "bore", "burst", "clung", "crept", "dealt", "dug", "drank",
        "fed", "fled", "flung", "forgot", "froze", "ground", "hung", "laid",
        "leapt", "lent", "made", "rode", "sought", "sold", "shed", "sped",
        "split", "spoilt", "sprung", "stung", "strode", "strove", "swelled",
        "wept", "wrung",
    }
)

PRESENT_MARKERS = frozenset({"am", "is", "are", "have", "has", "do", "does", "says"})

PAST_PARTICIPLES = frozenset(
    {
        "been", "done", "gone", "seen", "taken", "made", "known", "thought",
        "found", "given", "told", "become", "left", "felt", "put", "brought",
        "begun", "kept", "held", "written", "stood", "heard", "let", "meant",
        "met", "run", "paid", "sat", "spoken", "lain", "led", "grown", "lost",
        "fallen", "sent", "built", "understood", "drawn", "broken", "spent",
        "cut", "risen", "driven", "bought", "worn", "chosen", "read", "set",
        "shut", "spread", "taught", "thrown", "caught", "fought", "flown",
        "hidden", "hit", "hurt", "knelt", "lit", "ridden", "rung", "sung",
        "sunk", "shaken", "shone", "shot", "slept", "slid", "spun", "sprung",
        "stolen", "stuck", "struck", "swept", "sworn", "swum", "swung", "torn",
        "woken", "wound", "won", "withdrawn", "bent", "bound", "bled", "blown",
        "borne", "burst", "clung", "crept", "dealt", "dug", "drunk", "fed",
        "fled", "flung", "forgotten", "frozen", "ground", "hung", "laid",
        "leapt", "lent", "sought", "sold", "shed", "sped", "split", "stung",
        "stridden", "striven", "wept", "wrung", "had", "said", "come",
    }
)

MOTION_VERBS = frozenset(
    {
        "walked", "ran", "went", "came", "stepped", "moved", "turned", "rose",
        "sat", "stood", "fell", "climbed", "crossed", "entered", "left",
        "returned", "hurried", "rushed", "strode", "wandered", "drove", "rode",
        "flew", "leaned", "leapt", "jumped", "slipped", "swung", "pushed",
        "pulled", "dropped", "lifted", "carried", "threw", "caught", "reached",
        "opened", "closed", "shut", "knelt", "crept", "crawled", "darted",
        "paused", "halted", "followed", "passed", "approached", "retreated",
    }
)

PERCEPTION_VERBS = frozenset(
    {
        "saw", "watched", "looked", "glanced", "stared", "observed", "noticed",
        "heard", "listened", "felt", "touched", "smelled", "tasted", "sensed",
        "perceived", "regarded", "eyed", "beheld", "gazed", "peered",
    }
)

COGNITION_VERBS = frozenset(
    {
        "thought", "knew", "believed", "wondered", "realized", "realised",
        "understood", "remembered", "forgot", "considered", "decided",
        "supposed", "imagined", "guessed", "doubted", "recognized",
        "recognised", "reflected", "recalled", "concluded", "reasoned",
        "expected", "assumed", "suspected",
    }
)

EMOTION_VERBS = frozenset(
    {
        "loved", "hated", "feared", "hoped", "wished", "longed", "dreaded",
        "worried", "rejoiced", "grieved", "resented", "envied", "admired",
        "despised", "pitied", "enjoyed", "regretted", "trusted",
    }
)

# ---------------------------------------------------------------------------
# Filter phrases and crutch phrases
# ---------------------------------------------------------------------------
# Regex source strings; compiled in features.py. \b boundaries added there.

FILTER_PHRASES = (
    r"(?:he|she|they|i|it) (?:saw|sees)",
    r"(?:he|she|they|i) (?:watched|watches)",
    r"(?:he|she|they|i) (?:heard|hears)",
    r"(?:he|she|they|i) (?:felt|feels)",
    r"(?:he|she|they|i) (?:noticed|notices)",
    r"(?:he|she|they|i) (?:realized|realised|realizes|realises)",
    r"(?:he|she|they|i) (?:observed|observes)",
    r"(?:he|she|they|i) (?:thought|thinks)",
    r"(?:he|she|they|i) (?:knew|knows)",
    r"(?:he|she|they|i) (?:wondered|wonders)",
    r"(?:he|she|they|i) could (?:see|hear|feel|smell|taste)",
    r"(?:he|she|they|i) (?:seemed|seems) to",
    r"(?:he|she|they|i) (?:began|begins|started|starts) to",
    r"(?:he|she|they|i) found (?:himself|herself|themselves|myself)",
    r"(?:he|she|they|i) (?:was|were|am|is) able to",
)

# Phrases that mark generic modern model prose. Reference-corpus rates for
# these are near zero by construction; that is the point - they are a
# one-directional alarm for drafts, not an author feature.
CRUTCH_PHRASES = (
    r"a mixture of",
    r"a mix of",
    r"a sense of",
    r"a wave of",
    r"a pang of",
    r"a flicker of",
    r"a ghost of a smile",
    r"the weight of",
    r"in that moment",
    r"for a long moment",
    r"something (?:shifted|flickered|softened|tightened)",
    r"couldn't help but",
    r"could not help but",
    r"a testament to",
    r"let out a breath",
    r"didn't (?:realize|realise) (?:he|she|they) (?:was|were) holding",
    r"a beat of silence",
    r"the air (?:was|felt|hung) (?:thick|heavy|electric)",
    r"barely (?:above )?a whisper",
    r"eyes (?:narrowed|widened|softened)",
    r"jaw (?:tightened|clenched)",
    r"heart (?:hammered|pounded|thudded) (?:in|against)",
    r"it was (?:not|n't) lost on",
    r"(?:he|she|they) said nothing(?:\.|,) (?:he|she|they) (?:did|didn't)",
)

# ---------------------------------------------------------------------------
# Sensory / concreteness / emotion lexicons
# ---------------------------------------------------------------------------

SENSORY = {
    "sight": frozenset(
        {
            "saw", "see", "seeing", "seen", "look", "looked", "looking",
            "glance", "glanced", "stare", "stared", "gaze", "gazed", "watch",
            "watched", "peer", "peered", "glimpse", "glimpsed", "bright",
            "dark", "darkness", "light", "shadow", "shadows", "shone",
            "shining", "gleam", "gleamed", "glitter", "glittered", "glow",
            "glowed", "pale", "colour", "color", "coloured", "colored",
            "white", "black", "red", "green", "blue", "yellow", "grey",
            "gray", "brown", "golden", "scarlet", "crimson", "dim", "blaze",
            "blazing", "flash", "flashed", "visible", "sight", "eyes", "eye",
            "gloom", "dusk", "twilight", "sunlight", "moonlight", "flicker",
        }
    ),
    "sound": frozenset(
        {
            "heard", "hear", "hearing", "sound", "sounds", "sounded", "noise",
            "silence", "silent", "quiet", "loud", "listen", "listened",
            "voice", "voices", "whisper", "whispered", "shout", "shouted",
            "cry", "cried", "scream", "screamed", "murmur", "murmured",
            "rustle", "rustled", "creak", "creaked", "click", "clicked",
            "clatter", "clattered", "rattle", "rattled", "bang", "banged",
            "thud", "thudded", "hum", "hummed", "buzz", "buzzed", "ring",
            "rang", "echo", "echoed", "music", "song", "sang", "roar",
            "roared", "hiss", "hissed", "footsteps", "hush", "still",
        }
    ),
    "touch": frozenset(
        {
            "touch", "touched", "feel", "felt", "hand", "hands", "finger",
            "fingers", "grip", "gripped", "grasp", "grasped", "clutch",
            "clutched", "press", "pressed", "smooth", "rough", "soft", "hard",
            "sharp", "damp", "wet", "dry", "sticky", "silk", "velvet", "cloth",
            "skin", "brush", "brushed", "stroke", "stroked", "weight",
            "heavy", "light", "texture", "prickle", "prickled",
        }
    ),
    "smell": frozenset(
        {
            "smell", "smelled", "smelt", "scent", "scented", "odour", "odor",
            "fragrance", "fragrant", "perfume", "stench", "stink", "reek",
            "reeked", "aroma", "musty", "smoke", "smoky", "sniff", "sniffed",
            "nostrils",
        }
    ),
    "taste": frozenset(
        {
            "taste", "tasted", "tasting", "sweet", "bitter", "sour", "salt",
            "salty", "flavour", "flavor", "tongue", "swallow", "swallowed",
            "sip", "sipped", "drank", "ate", "eat", "mouthful", "bite", "bit",
            "chew", "chewed", "tang",
        }
    ),
    "temperature": frozenset(
        {
            "cold", "colder", "coldness", "chill", "chilled", "chilly", "cool",
            "warm", "warmth", "warmer", "hot", "heat", "heated", "burning",
            "burned", "burnt", "freezing", "frozen", "frost", "icy", "ice",
            "fever", "feverish", "sweltering", "tepid", "lukewarm",
        }
    ),
    "body": frozenset(
        {
            "breath", "breathed", "breathing", "heart", "pulse", "throat",
            "stomach", "shiver", "shivered", "shudder", "shuddered", "trembled",
            "trembling", "flush", "flushed", "blush", "blushed", "ache",
            "ached", "pain", "sore", "dizzy", "faint", "fainted", "tears",
            "wept", "sweat", "gasp", "gasped", "nerves", "flinch", "flinched",
            "stiffen", "stiffened", "tense", "tensed", "swallowed", "nausea",
            "weary", "weariness", "exhausted",
        }
    ),
}

EMOTION_LABELS = frozenset(
    {
        "anger", "angry", "angrily", "afraid", "fear", "fearful", "frightened",
        "terror", "terrified", "happy", "happiness", "joy", "joyful", "glad",
        "sad", "sadness", "sorrow", "sorrowful", "grief", "miserable",
        "misery", "delight", "delighted", "pleased", "pleasure", "excited",
        "excitement", "anxious", "anxiety", "nervous", "worried", "worry",
        "ashamed", "shame", "embarrassed", "guilt", "guilty", "proud",
        "pride", "jealous", "jealousy", "envy", "lonely", "loneliness",
        "hopeful", "hope", "despair", "desperate", "disgust", "disgusted",
        "contempt", "furious", "rage", "annoyed", "irritated", "surprised",
        "surprise", "astonished", "astonishment", "amazed", "curious",
        "curiosity", "relief", "relieved", "content", "calm", "uneasy",
        "uneasiness", "bitter", "bitterness", "resentment", "affection",
        "love", "hate", "hatred", "longing", "regret", "remorse",
    }
)

SPATIAL_TERMS = frozenset(
    {
        "above", "below", "behind", "beside", "beyond", "under", "over",
        "across", "along", "around", "between", "near", "far", "beneath",
        "inside", "outside", "opposite", "corner", "edge", "middle", "centre",
        "center", "left", "right", "front", "back", "top", "bottom", "door",
        "doorway", "window", "wall", "floor", "ceiling", "stairs", "staircase",
        "room", "hall", "garden", "street", "road", "path", "gate", "threshold",
        "distance", "height", "depth", "width",
    }
)

# Suffixes that reliably mark abstract nominalisations.
ABSTRACT_SUFFIXES = (
    "ness", "ment", "tion", "sion", "ity", "ance", "ence", "ism", "ship",
    "hood", "tude", "ency", "ancy", "acy",
)

# ---------------------------------------------------------------------------
# Sentence segmentation support
# ---------------------------------------------------------------------------

ABBREVIATIONS = frozenset(
    {
        "mr", "mrs", "ms", "dr", "st", "sgt", "capt", "col", "gen", "lt",
        "maj", "prof", "rev", "hon", "messrs", "mme", "mlle", "jr", "sr",
        "no", "vs", "etc", "inc", "ltd", "co", "vol", "fig", "ch", "pp",
        "esq", "viz", "ca", "cf", "ibid", "op", "al", "ave", "blvd",
        "mt", "ft", "sq", "dept", "univ", "assn", "bros", "phd", "md",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
        "oct", "nov", "dec", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
        "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    }
)

# Words that frequently begin a sentence and are capitalised for that reason
# only. Used to avoid mistaking them for proper names.
COMMON_SENTENCE_STARTERS = frozenset(
    {
        "the", "a", "an", "he", "she", "it", "they", "we", "i", "you", "there",
        "this", "that", "these", "those", "but", "and", "or", "so", "yet",
        "for", "nor", "in", "on", "at", "by", "with", "from", "to", "of",
        "as", "if", "when", "while", "after", "before", "then", "now", "here",
        "what", "who", "why", "how", "where", "which", "his", "her", "their",
        "its", "my", "our", "your", "no", "not", "yes", "well", "oh", "ah",
        "all", "some", "any", "every", "each", "one", "two", "three", "still",
        "even", "only", "just", "once", "again", "up", "down", "out", "over",
        "under", "through", "perhaps", "presently", "suddenly", "meanwhile",
        "nevertheless", "however", "indeed", "certainly", "of course",
        "was", "were", "is", "are", "had", "has", "have", "did", "do", "does",
        "would", "could", "should", "will", "shall", "may", "might", "must",
        "let", "come", "go", "look", "see", "take", "put", "get", "make",
        "nothing", "nobody", "something", "someone", "anything", "anyone",
        "everything", "everyone", "many", "much", "more", "most", "both",
        "neither", "either", "several", "few", "little", "last", "next",
        "first", "second", "third", "another", "such", "very", "quite",
        "almost", "always", "never", "sometimes", "often", "usually",
        "presently", "afterward", "afterwards", "besides", "meantime",
        "yesterday", "today", "tomorrow", "tonight",
    }
)
