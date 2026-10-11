import type { ExerciseInfo } from './types'
import { quizExercise } from './quiz'
import { typedExercise } from './typed'
import { writingExercise } from './writing'
import { prepositionsExercise } from './prepositions'
import { articlesExercise } from './articles'
import type { LanguageCode } from '../types'

export const exercises: ExerciseInfo[] = [quizExercise, typedExercise, writingExercise, prepositionsExercise, articlesExercise]

export function exercisesFor(language: LanguageCode): ExerciseInfo[] {
  return exercises.filter((exercise) => !exercise.languages || exercise.languages.includes(language))
}

export { quizExercise, typedExercise, writingExercise, prepositionsExercise, articlesExercise }
