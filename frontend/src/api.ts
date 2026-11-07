import type {
  Answer,
  Book, BookInput, BookSearchResult, BookRecommendation, BookCategory, BookCategoryInfo,
  ApiKeyStatus,
  Article,
  Category,
  AskTurn,
  DefinedEntry,
  Direction,
  ExerciseRequest,
  FlashcardSet,
  FlashcardsRequest,
  Grade,
  LanguageCode,
  Level,
  Meta,
  MixedQuestion, MixedSet, MixedCorrection,
  Models,
  QuizSet,
  Review,
  SaveResult,
  Translation,
  TypedCorrection,
  TypedQuestion,
  TypedSet,
  WritingCorrection,
  WritingSet,
  WritingTerm,
} from './types'
import { readStored } from './lib/storage'

export const MODEL_KEY = 'model'
export const API_KEY_CHANGED = 'languages:api-key-changed'

function modelHeaders(): Record<string, string> {
  const model = readStored<string | null>(MODEL_KEY)
  return model ? { 'X-OpenAI-Model': model } : {}
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : String(item)))
        .join('; ')
    }
  }
  return fallback
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...(path.startsWith('/api/settings/') ? {} : modelHeaders()), ...init.headers } })
  } catch (error) {
    if (isAbort(error)) throw error
    throw new ApiError(0, "Can't reach the server. Is ./scripts/run_web.py still running?")
  }

  const text = await response.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, detailMessage(body, `The server answered ${response.status} ${response.statusText}.`))
  }
  return body as T
}

function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return call<T>(path, { method: 'POST', body: JSON.stringify(body), signal })
}

export const api = {
  books: () => call<Book[]>('/api/books'),
  bookCategories: () => call<BookCategoryInfo[]>('/api/books/categories'),
  createBookCategory: (name: string) => post<BookCategoryInfo>('/api/books/categories', { name }),
  searchBooks: (query: string, signal?: AbortSignal) => call<BookSearchResult[]>(`/api/books/search?q=${encodeURIComponent(query)}`, { signal }),
  addBook: (book: BookInput) => post<Book>('/api/books', book),
  updateBook: (id: string, book: BookInput) => call<Book>(`/api/books/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(book) }),
  bookPageCount: (id: string) => post<{ totalPages: number | null }>(`/api/books/${encodeURIComponent(id)}/page-count`, {}),
  updateBookProgress: (id: string, progress: number, currentPage?: number, totalPages?: number) => call<Book>(`/api/books/${encodeURIComponent(id)}/progress`, { method: 'PATCH', body: JSON.stringify({ progress, currentPage, totalPages }) }),
  bookNotes: (id: string) => call<{ markdown: string; revision: number }>(`/api/books/${encodeURIComponent(id)}/notes`),
  saveBookNotes: (id: string, markdown: string, revision: number) => call<{ markdown: string; revision: number }>(`/api/books/${encodeURIComponent(id)}/notes`, { method: 'PUT', body: JSON.stringify({ markdown, revision }) }),
  deleteBook: (id: string) => call<void>(`/api/books/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  recommendBook: (category: BookCategory | 'all', language: string, signal?: AbortSignal) => post<BookRecommendation>('/api/books/recommend', { category, language }, signal),
  allowance: (language: LanguageCode) => call<{ available: number; reviews_toward_next: number }>(`/api/entries/allowance?language=${language}`),
  exerciseProgress: (event: unknown) => post<void>('/api/exercise-progress', event),
  meta: () => call<Meta>('/api/meta'),
  models: () => call<Models>('/api/models'),
  readSources: () => call<Record<LanguageCode, { name: string; domain: string }[]>>('/api/read/sources'),
  apiKey: () => call<ApiKeyStatus>('/api/settings/api-key'),
  elevenlabsKey: () => call<ApiKeyStatus>('/api/settings/elevenlabs-key'),
  setElevenlabsKey: (key: string) => call<ApiKeyStatus>('/api/settings/elevenlabs-key', { method: 'PUT', body: JSON.stringify({ key }) }),
  setApiKey: (key: string) => call<ApiKeyStatus>('/api/settings/api-key', { method: 'PUT', body: JSON.stringify({ key }) }),
  mixedTranslation: (request: ExerciseRequest, mode: 'recognize' | 'produce', signal?: AbortSignal) =>
    post<MixedSet>('/api/mixed-translation', { count: request.count, level: request.level, includePhrasal: !!request.includePhrasal, pairLanguage: request.pairLanguage, mode }, signal),
  mixedTranslationCheck: (question: MixedQuestion, answers: string[], signal?: AbortSignal) =>
    post<MixedCorrection>('/api/mixed-translation/check', { question, answers }, signal),
  quiz: (request: ExerciseRequest, signal?: AbortSignal) => post<QuizSet>('/api/quiz', request, signal),
  typed: (request: ExerciseRequest, signal?: AbortSignal) => post<TypedSet>('/api/typed', request, signal),
  typedCheck: (language: LanguageCode, question: TypedQuestion, answer: string, signal?: AbortSignal) =>
    post<TypedCorrection>('/api/typed/check', { language, question, answer }, signal),
  prepositions: (request: ExerciseRequest, signal?: AbortSignal) => post<TypedSet>('/api/prepositions', request, signal),
  prepositionsCheck: (language: LanguageCode, question: TypedQuestion, answer: string, signal?: AbortSignal) =>
    post<TypedCorrection>('/api/prepositions/check', { language, question, answer }, signal),
  articles: (request: ExerciseRequest, signal?: AbortSignal) => post<TypedSet>('/api/articles', request, signal),
  articlesCheck: (language: LanguageCode, question: TypedQuestion, answer: string, signal?: AbortSignal) =>
    post<TypedCorrection>('/api/articles/check', { language, question, answer }, signal),
  writing: (request: ExerciseRequest, signal?: AbortSignal) => post<WritingSet>('/api/writing', request, signal),
  writingCheck: (language: LanguageCode, level: Level, terms: WritingTerm[], sentence: string, signal?: AbortSignal) =>
    post<WritingCorrection>('/api/writing/check', { language, level, terms, sentence }, signal),
  define: (language: LanguageCode, term: string, signal?: AbortSignal) =>
    post<DefinedEntry>('/api/entries/define', { language, term }, signal),
  translate: (language: LanguageCode, phrase: string, signal?: AbortSignal) =>
    post<Translation>('/api/entries/translate', { language, phrase }, signal),
  transcribe: (audio: Blob, language: LanguageCode, signal?: AbortSignal) =>
    call<{ text: string; usage?: { credits?: number; audioSeconds?: number } }>(`/api/transcribe?language=${encodeURIComponent(language)}`, { method: 'POST', body: audio, headers: { 'Content-Type': audio.type || 'audio/webm' }, signal }),
  ask: (language: LanguageCode, question: string, history: AskTurn[], signal?: AbortSignal) =>
    post<Answer>('/api/ask', { language, question, history }, signal),
  read: (language: LanguageCode, topic: string, level: Level, signal?: AbortSignal, mode: 'find' | 'url' | 'text' = 'find', source = '', summaryWords = 100) =>
    post<Article>('/api/read', { language, topic, level, mode, source, summaryWords }, signal),
  save: (language: LanguageCode, entries: string[], category: Category) =>
    post<SaveResult>('/api/entries/save', { language, entries, category }),
  flashcards: (request: FlashcardsRequest, signal?: AbortSignal) => post<FlashcardSet>('/api/flashcards', request, signal),
  review: (language: LanguageCode, direction: Direction, term: string, grade: Grade) =>
    post<Review>('/api/flashcards/review', { language, direction, term, grade }),
}

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}
