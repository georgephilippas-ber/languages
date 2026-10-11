import { TextQuote } from 'lucide-react'
import { api } from '../api'
import type { LanguageCode, TypedCorrection, TypedQuestion } from '../types'
import { typedExercise, TypedQuestionView } from './typed'
import type { ExerciseDefinition, QuestionProps } from './types'

function ArticleQuestionView(props: QuestionProps<TypedQuestion, string, TypedCorrection>) {
  return <TypedQuestionView {...props} translationHint />
}

export const articlesExercise: ExerciseDefinition<TypedQuestion, string, TypedCorrection> = {
  ...typedExercise,
  kind: 'articles',
  path: '/articles',
  step: 5,
  verb: 'Agree',
  name: 'Articles',
  languages: ['DE', 'FR'] satisfies LanguageCode[],
  description: 'Type only the missing article before the noun — der, die, das and their case forms, or le, la, les, l’.',
  icon: TextQuote,
  outcomeLabels: { correct: 'Correct', partial: 'Right article, wrong spelling', wrong: 'Incorrect' },
  generate: async (request, signal) => {
    const set = await api.articles(request, signal)
    return { items: set.questions, source: set.source }
  },
  check: (item, answer, request, signal) => api.articlesCheck(request.language, item, answer, signal),
  Question: ArticleQuestionView,
}
