import { MotionConfig } from 'motion/react'
import { Navigate, Outlet, ScrollRestoration, type RouteObject } from 'react-router'
import { MetaProvider } from './context/MetaContext'
import { articlesExercise, prepositionsExercise, quizExercise, typedExercise, writingExercise } from './exercises'
import { ExerciseRunner } from './components/ExerciseRunner'
import { Header } from './components/Header'
import { ExerciseWordMenu } from './components/ExerciseWordMenu'
import { AddPage } from './pages/AddPage'
import { AskPage } from './pages/AskPage'
import { FlashcardsPage } from './pages/FlashcardsPage'
import { HomePage } from './pages/HomePage'
import { ReadPage } from './pages/ReadPage'
import { TranslatePage } from './pages/TranslatePage'
import { mixedRecognizeExercise, mixedProduceExercise } from './exercises/mixed'

function Layout() {
  return (
    <MotionConfig reducedMotion="user">
      <MetaProvider>
        <div className="relative min-h-dvh">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(60%_55%_at_50%_0%,color-mix(in_oklab,var(--accent)_13%,transparent),transparent)]"
          />
          <Header />
          <main className="relative mx-auto max-w-5xl px-4 pb-24 pt-8 sm:px-6">
            <Outlet />
          </main>
        </div>
        <ScrollRestoration />
      </MetaProvider>
    </MotionConfig>
  )
}

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'read', element: <ReadPage /> },
      { path: 'translate', element: <TranslatePage /> },
      { path: 'translate/recognize', element: <ExerciseWordMenu><ExerciseRunner key="mixed-recognize" definition={mixedRecognizeExercise} /></ExerciseWordMenu> },
      { path: 'translate/produce', element: <ExerciseWordMenu><ExerciseRunner key="mixed-produce" definition={mixedProduceExercise} /></ExerciseWordMenu> },
      { path: 'quiz', element: <ExerciseWordMenu><ExerciseRunner key="quiz" definition={quizExercise} /></ExerciseWordMenu> },
      { path: 'typed', element: <ExerciseWordMenu><ExerciseRunner key="typed" definition={typedExercise} /></ExerciseWordMenu> },
      { path: 'writing', element: <ExerciseWordMenu><ExerciseRunner key="writing" definition={writingExercise} /></ExerciseWordMenu> },
      { path: 'prepositions', element: <ExerciseWordMenu><ExerciseRunner key="prepositions" definition={prepositionsExercise} /></ExerciseWordMenu> },
      { path: 'articles', element: <ExerciseWordMenu><ExerciseRunner key="articles" definition={articlesExercise} /></ExerciseWordMenu> },
      { path: 'review', element: <ExerciseWordMenu><FlashcardsPage /></ExerciseWordMenu> },
      { path: 'add', element: <AddPage /> },
      { path: 'ask', element: <AskPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]
