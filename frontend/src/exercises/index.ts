import type { ExerciseInfo } from './types'
import { quizExercise } from './quiz'
import { typedExercise } from './typed'
import { writingExercise } from './writing'

export const exercises: ExerciseInfo[] = [quizExercise, typedExercise, writingExercise]

export { quizExercise, typedExercise, writingExercise }
