import { Link2 } from 'lucide-react'
import { api } from '../api'
import type { TypedCorrection, TypedQuestion } from '../types'
import { typedExercise, TypedQuestionView } from './typed'
import type { ExerciseDefinition, QuestionProps } from './types'

function PrepositionQuestionView(props: QuestionProps<TypedQuestion, string, TypedCorrection>) {
  return <TypedQuestionView {...props} translationHint />
}

export const prepositionsExercise: ExerciseDefinition<TypedQuestion, string, TypedCorrection> = {
  ...typedExercise,
  kind: 'prepositions',
  path: '/prepositions',
  step: 4,
  verb: 'Connect',
  name: 'Prepositions',
  description: 'Type only the missing German preposition. Hover over or tap the hint to reveal the English sentence translation.',
  icon: Link2,
  languages: ['DE'],
  outcomeLabels: { correct: 'Correct', partial: 'Right preposition, wrong spelling', wrong: 'Incorrect' },
  generate: async (request, signal) => {
    const set = await api.prepositions(request, signal)
    return { items: set.questions, source: set.source }
  },
  check: (item, answer, request, signal) => api.prepositionsCheck(request.language, item, answer, signal),
  Question: PrepositionQuestionView,
}
