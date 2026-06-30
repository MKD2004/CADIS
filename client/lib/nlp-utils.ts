export interface PipelineResult {
  document: string
  preprocessing: {
    tokens: string[]
    sentences: string[]
    wordCount: number
    uniqueWords: number
    charCount: number
  }
  ner: {
    entities: { type: string; text: string; score: number }[]
    relations: { subject: string; verb: string; object: string; sentence: string }[]
  }
  ambiguity: {
    items: {
      type: string
      trigger: string
      sentence: string
      candidates: string[]
      resolved: string
      confidence: number
    }[]
  }
  qa: {
    results: { question: string; answer: string; confidence: number }[]
  }
  summary: {
    executive: string
    keyPoints: string[]
    timeline: { time: string; event: string }[]
  }
}

export function tokenize(text: string): string[] {
  try {
    const matches = text.match(/\b[\w'-]+\b/g)
    return matches ?? []
  } catch {
    return []
  }
}

export function getSentences(text: string): string[] {
  try {
    const raw = text.split(/(?<=[.!?])\s+(?=[A-Z])/)
    return raw.map((s) => s.trim()).filter((s) => s.length > 5)
  } catch {
    return [text]
  }
}

export function getPOS(token: string): string {
  try {
    if (/^(the|a|an|this|that|these|those)$/i.test(token)) return "DT"
    if (/^(in|on|at|by|for|with|about|from|to|of|into|through|during|before|after)$/i.test(token)) return "IN"
    if (/^(is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|could|should|may|might|shall|can|need|dare|ought|used)$/i.test(token)) return "VB"
    if (/^(very|quite|rather|somewhat|too|so|just|almost|nearly|already|yet|still|soon|here|there|now|then|always|never|sometimes|often)$/i.test(token)) return "RB"
    if (/^[A-Z][a-z]+$/.test(token)) return "NNP"
    if (/^[A-Z]{2,}$/.test(token)) return "NNP"
    if (/ing$/.test(token)) return "VBG"
    if (/ed$/.test(token)) return "VBD"
    if (/ly$/.test(token)) return "RB"
    if (/^(big|small|fast|slow|good|bad|new|old|high|low|long|short|great|little|own|right|left|early|late|young|important|large|major|national|local|public|private|real|best|free|next|last|hard|open|sure|clear|strong|true|simple|complex)$/i.test(token)) return "JJ"
    if (/s$/.test(token)) return "NNS"
    return "NN"
  } catch {
    return "NN"
  }
}

const MONTHS = /\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b/
const YEAR = /\b(19|20)\d{2}\b/
const DATE_PATTERNS = [
  MONTHS,
  YEAR,
  /\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/,
  /\b\d{1,2}\/\d{1,2}(\/\d{2,4})?\b/,
  /\b(today|yesterday|tomorrow|last week|next week|last month|next month|last year|next year)\b/i,
]

export function extractEntities(text: string): {
  PERSON: string[]
  ORGANIZATION: string[]
  LOCATION: string[]
  DATE: string[]
  MONEY: string[]
  MISC: string[]
} {
  const result = { PERSON: [] as string[], ORGANIZATION: [] as string[], LOCATION: [] as string[], DATE: [] as string[], MONEY: [] as string[], MISC: [] as string[] }

  try {
    // PERSON: two capitalized words
    const personMatches = text.match(/\b[A-Z][a-z]+ [A-Z][a-z]+\b/g) ?? []
    result.PERSON = [...new Set(personMatches)]

    // ORG: capitalized sequence ending in Inc/Corp/etc, or all-caps acronyms
    const orgPattern = /\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Co|Foundation|University|Association|Institute|Group|Agency|Bureau|Department|Ministry|Council|Commission)\.?\b/g
    const orgMatches = text.match(orgPattern) ?? []
    const acronyms = text.match(/\b[A-Z]{2,}\b/g) ?? []
    result.ORGANIZATION = [...new Set([...orgMatches, ...acronyms.filter((a) => a.length >= 2 && a.length <= 6)])]

    // MONEY
    const moneyMatches = text.match(/\$[\d,.]+(?:\s*(?:billion|million|thousand))?/gi) ?? []
    result.MONEY = [...new Set(moneyMatches)]

    // DATE
    const dateFound: string[] = []
    for (const pat of DATE_PATTERNS) {
      const m = text.match(new RegExp(pat.source, "gi")) ?? []
      dateFound.push(...m)
    }
    result.DATE = [...new Set(dateFound)]

    // LOCATION: after "in", "at", "from" + capital word, or known cities/countries
    const locPattern = /(?:in|at|from|to|near|across|throughout)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/g
    const locMatches: string[] = []
    let m: RegExpExecArray | null
    while ((m = locPattern.exec(text)) !== null) {
      locMatches.push(m[1])
    }
    const knownLocs = ["New York", "London", "Paris", "Tokyo", "Beijing", "Washington", "Brussels", "Berlin", "Moscow", "Dubai", "San Francisco", "Los Angeles", "Chicago", "Boston", "Seattle", "Austin", "Miami", "Atlanta", "Denver", "Phoenix", "Kyiv", "Ukraine", "Russia", "China", "India", "Europe", "Asia", "Africa", "America", "United States", "United Kingdom", "France", "Germany", "Japan", "Korea", "Canada", "Australia"]
    const knownFound = knownLocs.filter((l) => text.includes(l))
    result.LOCATION = [...new Set([...locMatches, ...knownFound])]

    // Remove persons from locations and orgs
    result.LOCATION = result.LOCATION.filter((l) => !result.PERSON.includes(l))
    result.ORGANIZATION = result.ORGANIZATION.filter((o) => !result.PERSON.some((p) => o.includes(p)))

  } catch {
    // return empty
  }

  return result
}

const COMMON_VERBS = /^(said|announced|confirmed|stated|noted|warned|told|showed|found|reported|declared|revealed|claimed|explained|added|suggested|argued|agreed|denied|proposed|described|indicated|mentioned|expressed|concluded|decided|determined|established|created|made|took|gave|got|went|came|saw|knew|thought|believed|felt|wanted|needed|used|helped|tried|asked|started|worked|played|moved|turned|put|set|kept|left|called|seemed|looked|appeared|remained|become|happened|included|continued|followed|provided|required|received|expected|reached|led|allowed|developed|considered|showed|opened|closed|increased|decreased|improved|reduced|changed|launched|released|published|presented|organized|managed|controlled|operated|supported|offered|created|built|designed|implemented|introduced|entered|joined|left|returned|won|lost|completed|finished|ended|began|started|initiated|continued|stopped|paused|resumed|increased|decreased|grew|fell|rose|dropped|gained|lost|acquired|merged|partnered|collaborated|cooperated|competed|invested|funded|backed|supported|opposed|rejected|accepted|approved|denied|awarded|nominated|elected|appointed|hired|fired|resigned|retired|graduated|studied|researched|discovered|invented|developed|tested|analyzed|examined|investigated|explored|reviewed|assessed|evaluated|measured|calculated|estimated|predicted|forecasted)\b/i

export function extractRelations(sentences: string[]): { subject: string; verb: string; object: string; sentence: string }[] {
  const relations: { subject: string; verb: string; object: string; sentence: string }[] = []

  try {
    for (const sent of sentences) {
      const words = sent.match(/\b[\w'-]+\b/g) ?? []
      // find a verb
      for (let i = 1; i < words.length - 1; i++) {
        if (COMMON_VERBS.test(words[i])) {
          // subject = last capitalized noun before verb
          let subject = ""
          for (let j = i - 1; j >= 0; j--) {
            if (/^[A-Z]/.test(words[j]) || /^(it|he|she|they|we|I)$/i.test(words[j])) {
              // try two-word subject
              if (j > 0 && /^[A-Z]/.test(words[j - 1])) {
                subject = words[j - 1] + " " + words[j]
              } else {
                subject = words[j]
              }
              break
            }
          }
          // object = first noun/phrase after verb
          let object = ""
          for (let j = i + 1; j < words.length; j++) {
            if (/^[A-Z]/.test(words[j]) || /^(the|a|an|its|their|his|her|our|this|that)\s*/i.test(words[j])) {
              object = words[j]
              if (j + 1 < words.length && /^[A-Z]/.test(words[j + 1])) {
                object += " " + words[j + 1]
              }
              break
            }
            if (/^[a-z]/.test(words[j]) && !/^(the|a|an|to|for|with|by|at|in|on|of|and|or|but|that|which|who|whom|whose|when|where|how|why|if|as|than|then|so|yet|nor)$/i.test(words[j])) {
              object = words[j]
              break
            }
          }
          if (subject && object && subject !== object) {
            relations.push({
              subject,
              verb: words[i],
              object,
              sentence: sent.length > 90 ? sent.slice(0, 90) + "…" : sent,
            })
            break
          }
        }
      }
    }
  } catch {
    // return what we have
  }

  return relations.slice(0, 8)
}

const PREPOSITIONS = ["in", "on", "at", "by", "for", "with", "about", "from", "to", "of", "into", "through", "during", "before", "after", "near", "between", "among", "around", "along", "across", "behind", "beside", "beyond", "under", "over", "above", "below", "beneath", "within", "without", "against", "toward", "towards", "upon", "onto", "off", "out", "up", "down", "since", "until", "despite", "except", "including", "regarding", "concerning"]
const PRONOUNS = ["he", "she", "it", "they", "his", "her", "their", "its", "him", "them", "this", "that", "these", "those"]

export function detectAmbiguities(text: string, sentences: string[]): {
  type: "PP Attachment" | "Anaphoric"
  trigger: string
  sentence: string
  candidates: string[]
  resolved: string
  confidence: number
}[] {
  const items: ReturnType<typeof detectAmbiguities> = []

  try {
    for (const sent of sentences.slice(0, 10)) {
      const words = sent.match(/\b[\w'-]+\b/g) ?? []

      // PP Attachment: preposition where 2+ nouns/verbs nearby
      for (let i = 1; i < words.length - 1; i++) {
        if (PREPOSITIONS.includes(words[i].toLowerCase())) {
          const prev = words[i - 1]
          const next = words[i + 1]
          // look for another candidate noun before prev
          const earlier = words.slice(Math.max(0, i - 4), i - 1).filter((w) => /^[A-Z]/.test(w) || getPOS(w) === "NN" || getPOS(w) === "NNS")
          if (earlier.length > 0 && /^[A-Z]/.test(prev)) {
            const candidate1 = prev
            const candidate2 = earlier[earlier.length - 1]
            const conf = 0.65 + Math.random() * 0.2
            items.push({
              type: "PP Attachment",
              trigger: words[i],
              sentence: sent,
              candidates: [candidate1, candidate2],
              resolved: conf > 0.75 ? candidate1 : candidate2,
              confidence: parseFloat(conf.toFixed(3)),
            })
            break
          }
        }
      }

      // Anaphoric: pronoun with 2+ preceding nouns
      for (let i = 2; i < words.length; i++) {
        if (PRONOUNS.includes(words[i].toLowerCase())) {
          const preceding = words.slice(0, i).filter((w) => /^[A-Z][a-z]/.test(w))
          if (preceding.length >= 2) {
            const c1 = preceding[preceding.length - 1]
            const c2 = preceding[preceding.length - 2]
            const conf = 0.6 + Math.random() * 0.25
            items.push({
              type: "Anaphoric",
              trigger: words[i],
              sentence: sent,
              candidates: [c1, c2],
              resolved: c1,
              confidence: parseFloat(conf.toFixed(3)),
            })
            break
          }
        }
      }

      if (items.length >= 5) break
    }
  } catch {
    // return what we have
  }

  return items
}

function findAnswerInText(text: string, keywords: string[]): { answer: string; confidence: number } {
  try {
    const lc = text.toLowerCase()
    for (const kw of keywords) {
      const idx = lc.indexOf(kw.toLowerCase())
      if (idx !== -1) {
        // extract surrounding phrase
        const start = Math.max(0, idx)
        const chunk = text.slice(start, start + 80)
        // grab until punctuation
        const m = chunk.match(/^[^.!?,;]+/)
        if (m && m[0].trim().length > 2) {
          return { answer: m[0].trim(), confidence: parseFloat((0.6 + Math.random() * 0.3).toFixed(3)) }
        }
      }
    }
    // fallback: find first sentence containing any keyword
    const sents = getSentences(text)
    for (const s of sents) {
      if (keywords.some((k) => s.toLowerCase().includes(k.toLowerCase()))) {
        const snippet = s.length > 80 ? s.slice(0, 80) + "…" : s
        return { answer: snippet, confidence: parseFloat((0.4 + Math.random() * 0.2).toFixed(3)) }
      }
    }
  } catch {
    // ignore
  }
  return { answer: "", confidence: 0 }
}

export function generateQA(text: string, entities: ReturnType<typeof extractEntities>): {
  question: string
  answer: string
  start: number
  end: number
  confidence: number
}[] {
  const questions = [
    { q: "Who is the main person mentioned?", keywords: entities.PERSON.length ? entities.PERSON : ["person", "he", "she"] },
    { q: "What organization is involved?", keywords: entities.ORGANIZATION.length ? entities.ORGANIZATION : ["company", "organization", "firm"] },
    { q: "Where did the event take place?", keywords: entities.LOCATION.length ? entities.LOCATION : ["in", "at", "location"] },
    { q: "When did this happen?", keywords: entities.DATE.length ? entities.DATE : ["when", "date", "year", "month"] },
    { q: "What was the amount of money involved?", keywords: entities.MONEY.length ? entities.MONEY : ["$", "million", "billion", "cost", "price"] },
    { q: "Who made the announcement?", keywords: ["announced", "said", "stated", "confirmed", "declared"] },
    { q: "What was the outcome?", keywords: ["result", "outcome", "concluded", "ended", "finally", "therefore", "thus", "consequently"] },
  ]

  const results: ReturnType<typeof generateQA> = []

  try {
    for (const { q, keywords } of questions) {
      const { answer, confidence } = findAnswerInText(text, keywords)
      const start = answer ? text.indexOf(answer) : -1
      results.push({ question: q, answer, start: Math.max(0, start), end: start + answer.length, confidence })
    }
  } catch {
    // return partial
  }

  return results
}

export function summarize(
  text: string,
  sentences: string[],
  entities: ReturnType<typeof extractEntities>
): { executive: string; keyPoints: string[]; timeline: { time: string; event: string }[] } {
  try {
    const allEntities = Object.values(entities).flat()

    // Score sentences
    const scored = sentences.map((s) => {
      const entScore = allEntities.filter((e) => s.includes(e)).length * 2
      const verbScore = (s.match(COMMON_VERBS) ?? []).length
      const lenPenalty = s.length < 20 ? -2 : 0
      return { s, score: entScore + verbScore + lenPenalty }
    })
    scored.sort((a, b) => b.score - a.score)

    const top = scored.slice(0, 4).map((x) => x.s)
    const executive = top.slice(0, 2).join(" ")

    // Timeline: sentences with date patterns
    const timeline: { time: string; event: string }[] = []
    for (const sent of sentences) {
      for (const pat of DATE_PATTERNS) {
        const m = sent.match(new RegExp(pat.source, "i"))
        if (m) {
          timeline.push({ time: m[0], event: sent.length > 100 ? sent.slice(0, 100) + "…" : sent })
          break
        }
      }
    }

    return { executive, keyPoints: top, timeline: timeline.slice(0, 6) }
  } catch {
    return { executive: sentences[0] ?? "", keyPoints: sentences.slice(0, 4), timeline: [] }
  }
}

export function processDocument(text: string): PipelineResult {
  try {
    const tokens = tokenize(text)
    const sentences = getSentences(text)
    const uniqueWords = new Set(tokens.map((t) => t.toLowerCase())).size

    const entitiesMap = extractEntities(text)
    const flatEntities: { type: string; text: string; score: number }[] = []
    for (const [type, items] of Object.entries(entitiesMap)) {
      for (const item of items) {
        flatEntities.push({ type, text: item, score: parseFloat((0.7 + Math.random() * 0.28).toFixed(3)) })
      }
    }

    const relations = extractRelations(sentences)
    const ambiguityItems = detectAmbiguities(text, sentences)
    const qaResults = generateQA(text, entitiesMap)
    const summaryData = summarize(text, sentences, entitiesMap)

    return {
      document: text,
      preprocessing: { tokens, sentences, wordCount: tokens.length, uniqueWords, charCount: text.length },
      ner: { entities: flatEntities, relations },
      ambiguity: { items: ambiguityItems },
      qa: { results: qaResults },
      summary: summaryData,
    }
  } catch {
    return {
      document: text,
      preprocessing: { tokens: [], sentences: [], wordCount: 0, uniqueWords: 0, charCount: text.length },
      ner: { entities: [], relations: [] },
      ambiguity: { items: [] },
      qa: { results: [] },
      summary: { executive: "", keyPoints: [], timeline: [] },
    }
  }
}
