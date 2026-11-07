export type LanguageCode = 'EN' | 'DE' | 'FR'
export type Level = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'
export type Category = 'general' | 'legal' | 'financial' | 'phrasal-verbs'
export type FileSelection = 'latest' | 'all' | 'current' | Category | `${Category}:${'latest' | 'current'}` | `${'legal' | 'financial' | 'phrasal-verbs'}:${number}` | number
export type ExerciseKind = 'quiz' | 'typed' | 'writing' | 'prepositions' | 'articles' | 'mixed-recognize' | 'mixed-produce'
export type Outcome = 'correct' | 'partial' | 'wrong' | 'skipped'
export type Verdict = 'correct' | 'wrong_form' | 'wrong_word'
export type Direction = 'forward' | 'reverse'
export type Grade = 'again' | 'hard' | 'good' | 'easy'

export interface FileInfo {
  number: number | `${'legal' | 'financial' | 'phrasal-verbs'}:${number}`
  name: string
  terms: number
}

export interface LanguageInfo {
  code: LanguageCode
  name: string
  supportLanguage: string
  files: FileInfo[]
  latest: number[]
}

export interface Defaults {
  language: LanguageCode
  level: Level
  questions: number
  sentences: number
  revise: number
  secondsPerQuestion: number
  latestFiles: number
  maxCount: number
  maxTermsPerFile: number
}

export interface Models {
  default: string
  models: string[]
}

export interface ApiKeyStatus {
  configured: boolean
  hint: string | null
  source: 'environment' | 'file' | null
}

export interface Meta {
  blank: string
  levels: Level[]
  topics: string[]
  languages: LanguageInfo[]
  defaults: Defaults
}

export interface ExerciseRequest {
  language: LanguageCode
  level: Level
  count: number
  files: FileSelection
  includePhrasal?: boolean
  pairLanguage?: LanguageCode
}

export interface QuizQuestion {
  term: string
  question: string
  choices: string[]
  choicesTranslations: string[]
  correctChoice: number
  completeSentence: string
  englishTranslation: string
}

export interface QuizSet {
  source: string
  questions: QuizQuestion[]
}

export interface TypedQuestion {
  term: string
  question: string
  hint: string
  correctAnswer: string
  completeSentence: string
  englishTranslation: string
}

export interface TypedSet {
  source: string
  questions: TypedQuestion[]
}

export interface Correction {
  original: string
  corrected: string
  explanation: string
}

export interface TypedCorrection {
  verdict: Verdict
  correctedAnswer: string
  errors: Correction[]
  comment: string
  suggestions: string[]
  notice: string | null
}

export interface WritingTerm {
  term: string
  fileName: string
  hint: string
}

export interface WritingSet {
  source: string
  rounds: WritingTerm[][]
}

export interface TermCheck {
  term: string
  used: boolean
  usedCorrectly: boolean
  comment: string
}

export interface WritingCorrection {
  isCorrect: boolean
  minimalCorrection: string
  naturalVersion: string
  naturalExplanation: string
  translation: string
  terms: TermCheck[]
  corrections: Correction[]
  feedback: string
  targetLevel: Level
  level: Level | ''
  levelComment: string
}

export interface DefinedEntry {
  term: string
  markdown: string
  gloss: string
}

export interface Translation {
  sourceLanguage: string
  targetLanguage: string
  translation: string
  notes: string[]
}

export interface AskTurn {
  question: string
  answer: string
}

export interface Answer {
  onTopic: boolean
  answer: string
}

export interface Article {
  publishedAt?: string
  retrievedAt?: string
  topic: string
  title: string
  publication: string
  url: string
  summary: string
  words: string[]
  addedWords?: string[]
}

export interface SavedEntry {
  term: string
  fileName: string
  termsInFile: number
}

export interface SaveResult {
  saved: SavedEntry[]
  fileName: string
  termsInFile: number
  fileFull: boolean
}

export interface CardSection {
  label: string
  text: string
}

export interface CardState {
  ease: number
  intervalDays: number
  repetitions: number
  lapses: number
  dueAt: string | null
  reviewedAt: string | null
}

export interface Flashcard {
  term: string
  fileName: string
  sections: CardSection[]
  state: CardState
  isNew: boolean
  isDue: boolean
  intervals: Record<Grade, string>
}

export interface FlashcardSet {
  source: string
  cards: Flashcard[]
}

export interface FlashcardsRequest {
  language: LanguageCode
  files: FileSelection
  direction: Direction
}

export interface Review {
  state: CardState
  intervals: Record<Grade, string>
}

export interface MixedQuestion {
  sourceLanguage: LanguageCode
  targetLanguage: LanguageCode
  sourceSentence: string
  segments: string[]
  answers: string[]
  hint: string
  choices: string[][]
  correctChoice: number
  terms: string[]
}
export interface MixedSet { source: string; questions: MixedQuestion[] }
export interface MixedCorrection { verdict: 'correct' | 'wrong_form' | 'wrong_word'; correctedAnswers: string[]; comment: string }

export type BookCategory = string
export interface BookCategoryInfo { id: string; name: string; group: 'main' | 'nonfiction' }
export interface BookInput {
  title: string
  author: string
  isbn: string
  language: string
  progress: number
  status: 'current' | 'done'
  category: BookCategory
  rating: number | null
  personalCategory: ToReadCategory
}
export interface Book extends BookInput { id: string; createdAt: string; updatedAt: string; totalPages: number | null; currentPage: number | null; lastReadablePage: number | null }
export interface BookSearchResult { title: string; author: string; isbn: string; year: number | null }
export interface BookRecommendation { title: string; author: string; language: string; reason: string }

export type ToReadCategory = 'work' | 'education' | 'personal-development' | 'literature'
export interface ToReadInput { title: string; author: string; isbn: string; language: string; category: ToReadCategory }
export interface ToReadBook extends ToReadInput { id: string; createdAt: string; updatedAt: string }
