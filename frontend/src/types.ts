export type LanguageCode = 'EN' | 'DE' | 'FR'
export type Level = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'
export type FileSelection = 'latest' | 'all' | number
export type ExerciseKind = 'quiz' | 'typed' | 'writing'
export type Outcome = 'correct' | 'partial' | 'wrong' | 'skipped'
export type Verdict = 'correct' | 'wrong_form' | 'wrong_word'
export type EntryKind = 'vocabulary' | 'idioms' | 'grammatical'
export type Direction = 'forward' | 'reverse'
export type Grade = 'again' | 'hard' | 'good' | 'easy'

export interface FileInfo {
  number: number
  name: string
  terms: number
}

export interface LanguageInfo {
  code: LanguageCode
  name: string
  supportLanguage: string
  files: FileInfo[]
  latest: number[]
  idioms: FileInfo[]
  grammatical: FileInfo[]
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

export interface Meta {
  demo: boolean
  blank: string
  levels: Level[]
  languages: LanguageInfo[]
  defaults: Defaults
}

export interface ExerciseRequest {
  language: LanguageCode
  level: Level
  count: number
  files: FileSelection
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
  choices: string[]
  choicesTranslations: string[]
  correctChoice: number
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
}

export interface DefinedEntry {
  term: string
  markdown: string
  gloss: string
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
  demo: boolean
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
  kind: EntryKind
  files: FileSelection
  direction: Direction
}

export interface Review {
  state: CardState
  intervals: Record<Grade, string>
}
