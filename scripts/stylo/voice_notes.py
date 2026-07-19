"""Curated craft notes: the part Python cannot measure.

Section 5 of the guide draws a hard line at "interpretive literary judgements"
- whether dialogue has subtext, whether irony works, whether restraint feels
earned. A counter cannot decide those, so they are written here by hand and
merged into the style cards alongside the measured numbers.

Keeping them in code rather than in the generated Markdown means regenerating
a style card never destroys the human half of it.

Each entry:

``lane``      the one-line style lane the card opens with.
``craft``     prose instructions - what the author *does*, not what they count.
``avoid``     habits that break the imitation.
``scenes``    narrative jobs this author is a good model for.
"""

from __future__ import annotations

VOICE_NOTES: dict[str, dict] = {
    "edith-wharton": {
        "lane": "Close third-person social observation, ironic and syntactically layered",
        "craft": [
            "Judgement is delivered through syntax, not adjectives. A qualification "
            "arrives inside the sentence that made the claim, usually behind a "
            "semicolon or a subordinate clause, and quietly undoes it.",
            "The narration knows more than the point-of-view character and lets the "
            "reader see the gap without ever announcing it.",
            "Money, furniture, clothes and rooms carry moral weight. Describe the "
            "object; let the reader infer the verdict.",
            "Characters say the socially permissible thing. The real subject of a "
            "scene is what nobody is allowed to say aloud.",
            "Emotion peaks are handled with contraction, not expansion: the biggest "
            "feeling gets the plainest sentence.",
        ],
        "avoid": [
            "Naming the emotion the syntax has already implied.",
            "Letting a character state their own motive accurately.",
            "Modern breeziness — no contractions in narration.",
        ],
        "scenes": [
            "Drawing-room conversation", "Social confrontation", "Private reflection",
            "Setting arrival", "Discovery or revelation",
        ],
    },
    "agatha-christie": {
        "lane": "Fast first-person detective narration built on dialogue and withheld information",
        "craft": [
            "Scenes move on speech. Narration exists to stage the talk, then get out "
            "of the way.",
            "The narrator reports what he sees accurately and interprets it wrongly. "
            "The clue is on the page, sitting in plain sight, phrased as an "
            "unimportant detail.",
            "Character is established in one physical or verbal tic, then reused as "
            "shorthand rather than re-described.",
            "Chapter and scene ends land on a line of dialogue or a single-sentence "
            "reversal.",
            "Description is functional and brief: rooms are inventoried for evidence, "
            "not atmosphere.",
        ],
        "avoid": [
            "Interiority that slows the interrogation.",
            "Concealing information by refusing to narrate it — Christie hides in "
            "plain sight instead.",
            "Lyrical setting description.",
        ],
        "scenes": [
            "Interrogation", "Discovery of a body or clue", "Ensemble conversation",
            "Revelation", "Comic misdirection",
        ],
    },
    "f-scott-fitzgerald": {
        "lane": "First-person retrospective lyricism over Jazz Age social comedy",
        "craft": [
            "The narrator is remembering, not reporting. Past-perfect and summary "
            "compress months, then the prose drops into a scene rendered at full length.",
            "Lists and catalogues do the social work: names, cars, dresses, parties, "
            "accumulated until the accumulation itself is the judgement.",
            "One extended lyrical sentence per passage, usually at the end, reaching "
            "for something the scene cannot deliver.",
            "Dialogue is clipped and evasive; people talk past each other while the "
            "narration supplies the meaning they miss.",
            "Colour and weather carry emotional freight without being explained.",
        ],
        "avoid": [
            "Sustained lyricism — it only works against flat, gossipy talk.",
            "Explaining the symbol after presenting it.",
        ],
        "scenes": [
            "Party or ensemble set piece", "Romantic intimacy", "Private reflection",
            "Confrontation", "Retrospective summary",
        ],
    },
    "h-g-wells": {
        "lane": "First-person scientific romance: plain reportage of impossible events",
        "craft": [
            "The narrator is a credible, slightly pedantic witness. Extraordinary "
            "events are reported in the register of a newspaper account or a "
            "scientific paper.",
            "Wonder is produced by precision — measurements, distances, times, "
            "mechanisms — not by adjectives.",
            "Exposition is delivered as the narrator reasoning aloud toward a "
            "conclusion, so explanation reads as suspense.",
            "The ordinary English landscape is inventoried carefully so the "
            "intrusion into it lands.",
            "Terror is registered physically and belatedly: the narrator acts first "
            "and understands afterwards.",
        ],
        "avoid": [
            "Emotional commentary on the marvel while it is happening.",
            "Modern action-scene rhythm — Wells narrates panic in long, orderly "
            "sentences.",
        ],
        "scenes": [
            "Discovery or revelation", "Danger and flight", "Exposition of a mechanism",
            "Setting arrival", "Private reflection",
        ],
    },
    "l-m-montgomery": {
        "lane": "Warm third-person community comedy with a rhapsodic nature register",
        "craft": [
            "Two registers alternate: brisk, gossipy village comedy, and a heightened "
            "lyric mode reserved for landscape and for Anne's imagination.",
            "Comedy comes from the gap between what a character says and how "
            "seriously they mean it. The narrator is fond of everyone and forgives "
            "them in advance.",
            "Speeches are allowed to run long when a character is enthusing — that "
            "runaway quality is the characterisation.",
            "Nature is named specifically: species, seasons, times of day, local "
            "place names invented and reused.",
            "Sentiment is undercut by a practical remark from an unsentimental "
            "character before it can cloy.",
        ],
        "avoid": [
            "Irony at a character's expense.",
            "Generic scenery — Montgomery names the tree.",
        ],
        "scenes": [
            "Comic ensemble scene", "Private reflection", "Nature description",
            "Domestic conversation", "Emotional reconciliation",
        ],
    },
    "e-nesbit": {
        "lane": "Children's adventure told by a conspiratorial narrator who addresses the reader",
        "craft": [
            "The narrator talks to the reader directly — asides, admissions, mock "
            "apologies, refusals to explain. That voice is the book.",
            "Children are treated as competent and their logic is followed seriously, "
            "however disastrous the result.",
            "Magic is administrative: it has rules, loopholes and irritating "
            "conditions, and the comedy comes from the negotiation.",
            "Adults are rendered from a child's vantage — bafflingly arbitrary, seen "
            "from below.",
            "Sentences run on cheerfully with 'and', imitating a child recounting "
            "events at speed.",
        ],
        "avoid": [
            "A morally instructive narrator. Nesbit's narrator is complicit.",
            "Wonder without practical complications.",
        ],
        "scenes": [
            "Comic ensemble scene", "Discovery", "Scheme and its collapse",
            "Adult confrontation", "Direct address to the reader",
        ],
    },
    "edgar-allan-poe": {
        "lane": "First-person Gothic monologue: an over-articulate narrator arguing his own sanity",
        "craft": [
            "The voice is a performance of reason under pressure. The more the "
            "narrator insists on his lucidity, the further gone he is.",
            "Sentences accumulate by apposition and dash, doubling back to qualify, "
            "intensify and restate.",
            "Sensation is narrowed to one channel — a sound, a heartbeat, a single "
            "eye — and then magnified past bearing.",
            "Architecture and enclosure carry the dread: rooms, vaults, walls, and "
            "how they are shaped.",
            "The ratiocinative tales use the same voice for the opposite purpose: "
            "analysis presented as a bravura performance for an admiring companion.",
        ],
        "avoid": [
            "A stable, reliable narrator.",
            "Restraint in the closing paragraphs — Poe accelerates.",
            "Modern short-sentence horror rhythm.",
        ],
        "scenes": [
            "Confession", "Descent into obsession", "Ratiocination",
            "Enclosure and dread", "Revelation of the corpse or crime",
        ],
    },
    "carolyn-keene": {
        "lane": "Syndicate juvenile mystery: capable heroine, brisk plot, clean surfaces",
        "craft": [
            "Nancy is competent and unruffled; the prose never questions her "
            "judgement. Confidence is the house tone.",
            "Every scene advances the case. Description exists to plant a clue or "
            "establish a location, then stops.",
            "Chapters end on a small hook — a noise, a threat, an unanswered "
            "question — roughly every 1,500 words.",
            "Adults are either allies who defer to her or obstacles who "
            "underestimate her.",
            "Emotion is stated briefly and moved past. Nobody dwells.",
        ],
        "avoid": [
            "Interiority, ambiguity, or an unresolved beat.",
            "Treating this as one writer's voice — it is a formula, and it is "
            "meant to be reproducible.",
        ],
        "scenes": [
            "Investigation", "Chapter-end hook", "Confrontation with a suspect",
            "Ally conversation", "Physical peril",
        ],
    },
    "franklin-w-dixon": {
        "lane": "Syndicate juvenile adventure: two brothers, constant motion, dialogue-driven plot",
        "craft": [
            "Plot is delivered almost entirely through talk. The boys narrate the "
            "case to each other so the reader is never lost.",
            "Action is continuous — vehicles, chases, weather, physical mishap — and "
            "always described in concrete, unfussy terms.",
            "Chums are differentiated by one running gag apiece and nothing else.",
            "Exclamation and enthusiasm are the baseline register, not a peak.",
            "Chapters end mid-jeopardy, on the cliff-hanger, every time.",
        ],
        "avoid": [
            "Reflection, atmosphere, or moral complication.",
            "Treating this as one writer's voice — it is a syndicate formula.",
        ],
        "scenes": [
            "Chase or pursuit", "Chapter-end cliff-hanger", "Clue conference",
            "Physical peril", "Comic interlude",
        ],
    },
    "jane-austen": {
        "lane": "Close third-person comedy of manners: free indirect wit over a courtship plot",
        "craft": [
            "The narration slips in and out of a character's head without warning. A "
            "sentence can begin as the narrator's report and end as the heroine's own "
            "indignation, all in the third person.",
            "Irony is structural, not decorative: the narrator states a social truism "
            "with a straight face and lets the plot quietly disprove it.",
            "Character is delivered through how a person talks — pomposity, brevity, "
            "over-qualification — far more than through description of the person.",
            "Feeling is conveyed by what a character will not say and by how the scene "
            "is composed, never by naming the emotion outright.",
            "Money, rank and property sit openly in every room and shape every "
            "courtship; the prose discusses them without embarrassment.",
        ],
        "avoid": [
            "Modern breeziness or anachronism in the narration.",
            "Naming the emotion the free indirect style has already delivered.",
            "Letting a foolish character understand that they are foolish.",
        ],
        "scenes": [
            "Courtship conversation", "Social comedy of manners", "A letter and its reading",
            "Dawning private realization", "A ball or gathering",
        ],
    },
    "elizabeth-gaskell": {
        "lane": "Warm small-town chronicle: gentle narration among a community of women",
        "craft": [
            "The town itself is the protagonist. Small domestic economies — a shared "
            "cake, a turned gown, an unreturned call — carry the real drama.",
            "The comedy is affectionate and never cruel; the narrator plainly loves the "
            "people she gently laughs at.",
            "Gossip is the plot's circulatory system. Information travels through the "
            "community rather than through any single investigator.",
            "Kindness and social embarrassment are the twin stakes; a breach of "
            "etiquette lands as heavily here as a catastrophe would elsewhere.",
            "Sentences are companionable and unhurried, digressive the way a "
            "neighbour's story is.",
        ],
        "avoid": [
            "Cynicism, or a narrator who stands above the community instead of inside it.",
            "Melodrama that overwhelms the small domestic scale.",
        ],
        "scenes": [
            "A social call or tea", "Village news circulating", "A small domestic crisis",
            "A gentle courtship", "The community closing ranks around one of its own",
        ],
    },
    "kenneth-grahame": {
        "lane": "Pastoral idyll: rhapsodic nature writing wrapped around small domestic comforts",
        "craft": [
            "The natural world is rendered with sensuous, almost devotional detail — "
            "river, wind, hearth — and given a mood entirely its own.",
            "Home, food and firelight are treated as moral goods; the prose actively "
            "celebrates comfort rather than merely describing it.",
            "Adventure is gentle and always returns to safety. Even peril stays cozy, "
            "resolved by loyalty and friendship.",
            "The register slides between the mock-heroic — a small creature's enormous "
            "feelings — and the genuinely lyrical, often inside one paragraph.",
            "Character is temperament made audible: the loyal, the boastful, the "
            "restless wanderer, each voiced by how they speak.",
        ],
        "avoid": [
            "Real menace or unresolved threat; the world must stay safe.",
            "Irony that punctures the wonder instead of warming it.",
        ],
        "scenes": [
            "Seasonal nature description", "A cozy domestic interior", "A gentle adventure and homecoming",
            "The small rituals of friendship", "A moment of quiet enchantment",
        ],
    },
    "g-k-chesterton": {
        "lane": "Paradoxical detective fable: a mild priest who solves crime by understanding sin",
        "craft": [
            "The detection is moral, not forensic. Father Brown reads the criminal "
            "because he understands the human heart, not the footprints.",
            "Every case turns on a paradox or an inversion: the obvious thing is the "
            "disguise, the man nobody counts is the man who did it.",
            "Setting is painted in vivid, near-heraldic colour and light; the "
            "atmosphere is symbolic, doing argumentative work, not just scenic.",
            "The prose delights in the epigram — a plain observation sharpened into a "
            "memorable reversal that lands the point.",
            "The detective is deliberately unremarkable, and that is the method: being "
            "under-estimated is how he sees what others miss.",
        ],
        "avoid": [
            "Procedural or forensic realism; the solution is spiritual, not material.",
            "A cynical or hard-boiled register — the warmth and the wonder are the genre.",
        ],
        "scenes": [
            "A crime revealed as a paradox", "A quiet moral confrontation", "Atmospheric scene-setting",
            "The detective under-estimated", "A solution delivered as an epigram",
        ],
    },
    "arthur-conan-doyle": {
        "lane": "First-person Watson chronicle: dazzling deduction staged for an admiring narrator",
        "craft": [
            "Watson narrates, and his ordinariness is the lens that makes Holmes "
            "legible. The reader stands beside Watson, always a step behind.",
            "The deduction is theatrical: Holmes withholds the reasoning, produces the "
            "astonishing conclusion, then walks it back step by step.",
            "Scene-setting is atmospheric but economical — fog, gaslight, a client at "
            "the door — and then the case takes over.",
            "Character is fixed by a few strong tics (the pipe, the violin, the cold "
            "logic) and reused as shorthand rather than re-drawn.",
            "Dialogue drives the investigation; a client's account or an interrogation "
            "carries most of the exposition.",
        ],
        "avoid": [
            "Letting the narrator grasp the solution before Holmes explains it.",
            "Interiority that slows the reveal — Watson reports, he does not ruminate.",
        ],
        "scenes": [
            "A client's account", "A deduction and its explanation", "Atmospheric arrival at a scene",
            "Interrogation of a witness", "The reveal",
        ],
    },
    "bram-stoker": {
        "lane": "Epistolary gothic dread: ordinary modern people documenting an ancient horror",
        "craft": [
            "The horror is assembled from documents — diaries, letters, telegrams, news "
            "clippings — so the reader pieces the threat together before the cast does.",
            "Dread accrues through mundane, modern detail; the terror is credible "
            "precisely because everything around it is meticulously ordinary.",
            "Multiple narrators each hold one fragment, and the suspense lives in the "
            "gap between what one knows and another does not.",
            "Rationalists resist the supernatural until the evidence is overwhelming; "
            "the struggle to believe is itself the drama.",
            "Physical sensation — cold, blood, breath, the body's revulsion — grounds "
            "the metaphysical menace and keeps it from floating off.",
        ],
        "avoid": [
            "Explaining the horror too early; the withholding is the engine.",
            "Collapsing into one omniscient narrator — the fragmented documentary form is the effect.",
        ],
        "scenes": [
            "A diary or letter entry", "Mounting unease in an ordinary setting",
            "A rationalist confronting the inexplicable", "Physical horror",
            "Assembling the scattered evidence",
        ],
    },
    "charlotte-bronte": {
        "lane": "First-person gothic romance: an intense, morally serious narrator telling her own life",
        "craft": [
            "The narrator owns the telling and addresses the reader directly. This is "
            "a life recounted from inside it, not a story observed from outside.",
            "Passion is real but governed. The strongest feeling is held under "
            "principle and self-command, and the tension between the two is the engine.",
            "Interiority is dense and analytic — the narrator interrogates her own "
            "heart and conscience at length, and the reader lives inside that argument.",
            "Setting is charged and gothic: weather, houses and rooms carry mood and "
            "moral weight, and often turn frankly symbolic.",
            "The love interest is a match of mind and will, not merely of circumstance; "
            "the romance is argued and earned, never simply arranged.",
        ],
        "avoid": [
            "Breezy or ironic detachment — the register is earnest and interior.",
            "Letting desire override the narrator's moral self-government without cost.",
        ],
        "scenes": [
            "First-person confession or reflection", "A charged romantic confrontation",
            "Gothic setting and atmosphere", "A crisis of conscience", "A hard-won declaration",
        ],
    },
    "louisa-may-alcott": {
        "lane": "Warm domestic family chronicle: moral growth among a close, lively household",
        "craft": [
            "The family is the whole world. Small domestic events — a home play, a lost "
            "glove, a sacrifice of pocket-money — carry the real emotional stakes.",
            "Each character is a distinct temperament with a besetting fault to grow "
            "past; the arc is gentle moral improvement, never punishment.",
            "The narration is warm and lightly didactic, fond of its characters and "
            "openly on their side.",
            "Comedy and sentiment sit together; a scene can be funny and tender in the "
            "same breath without irony puncturing either.",
            "Domestic labour, thrift and small kindnesses are treated as genuine "
            "virtues and given real narrative weight.",
        ],
        "avoid": [
            "Cynicism, or a narrator who mocks the characters' earnestness.",
            "Melodrama that overwhelms the everyday domestic scale.",
        ],
        "scenes": [
            "A lively family scene", "A small moral test and its lesson",
            "A tender or sentimental beat", "Domestic comedy", "A coming-of-age turn",
        ],
    },
}


def notes_for(slug: str) -> dict:
    return VOICE_NOTES.get(
        slug,
        {"lane": "", "craft": [], "avoid": [], "scenes": []},
    )
