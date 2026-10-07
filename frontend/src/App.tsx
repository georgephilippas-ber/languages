import { MotionConfig } from 'motion/react'
import { Navigate, Outlet, ScrollRestoration, type RouteObject } from 'react-router'
import { MetaProvider } from './context/MetaContext'
import { quizExercise, typedExercise, writingExercise } from './exercises'
import { ExerciseRunner } from './components/ExerciseRunner'
import { Header } from './components/Header'
import { AddPage } from './pages/AddPage'
import { AskPage } from './pages/AskPage'
import { FlashcardsPage } from './pages/FlashcardsPage'
import { HomePage } from './pages/HomePage'

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
      { path: 'quiz', element: <ExerciseRunner key="quiz" definition={quizExercise} /> },
      { path: 'typed', element: <ExerciseRunner key="typed" definition={typedExercise} /> },
      { path: 'writing', element: <ExerciseRunner key="writing" definition={writingExercise} /> },
      { path: 'review', element: <FlashcardsPage /> },
      { path: 'add', element: <AddPage /> },
      { path: 'ask', element: <AskPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]
