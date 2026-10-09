# Frontend

## Architecture

- Each exercise is an
  `ExerciseDefinition` in `src/exercises/` (generate, check, outcome, Question and Feedback views, review entry), all
  run by the generic `components/ExerciseRunner.tsx` (setup, loading, timer, progress, feedback, results, resume).
  Unfinished sessions and settings live in `localStorage` under `languages.*`. Changing the language discards all
  unfinished sessions (`setLanguage` in `context/MetaContext.tsx`), and the runner immediately restarts an exercise
  that is running or loading in the new language, with the same request; it never resumes across languages. Add,
  Review, and Ask are standalone pages in `src/pages/` (`AddPage.tsx`, `FlashcardsPage.tsx`, `AskPage.tsx`; not
  `ExerciseDefinition`s); Add
  keeps its drafts in `localStorage` and calls `refresh` in `MetaContext` after saving. The model picker (`components/ModelPicker.tsx`, next to the theme button) stores the choice under
  `languages.model` (`null` = default), and `api.ts` adds the header from it. Colours are CSS variables in `src/index.css` (light and `.dark`), exposed as Tailwind colours (`bg-surface`, `text-muted`,
  `text-good`, …).

## Conventions

- Don't pass a class to a component that conflicts with one of its own (e.g. `hidden` against
  `inline-flex`, `px-0` against `px-4`): Tailwind's order, not the class order, decides which wins. Wrap the element
  or add a prop instead.
