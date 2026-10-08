from os import environ
from os.path import basename
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, Response
from openai import OpenAIError

from backend.schemas import MAX_COUNT, ExerciseRequestModel, MetaModel, QuizModel, TypedModel, \
    TypedCheckRequestModel, TypedCorrectionModel, WritingModel, WritingCheckRequestModel, WritingCorrectionModel, \
    DefineRequestModel, DefinedEntryModel, SaveRequestModel, SaveResultModel, FlashcardsRequestModel, \
    FlashcardsModel, ReviewRequestModel, ReviewModel, TranslateRequestModel, TranslationModel, AskRequestModel, \
    AnswerModel, ModelsModel
from src.adding import check_definition, save_entries
from src.asking import Turn, check_question
from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_NUMBER_OF_SENTENCES, DEFAULT_VOCABULARY, \
    DEFAULT_CEFR_LEVEL, REVISION_QUESTIONS_NUMBER, SECONDS_PER_QUESTION, LATEST_FILES_NUMBER, UNSEEN_ALPHA, MODEL
from src.domain import Vocabulary, CEFRLevel, BLANK, LANGUAGE_CODES, language_code
from src.flashcards import cards_with_states, review_card, select_library_file_numbers
from src.library import MAX_TERMS_PER_FILE, library_file_name
from src.models import available_models
from src.openai_integration import openai_construct_exercise, select_model
from src.parser import get_vocabulary_file_numbers, get_vocabulary_file_path, count_vocabulary_file_terms
from src.prepositions import construct_questions as construct_prepositions, check_answer as check_preposition
from src.selection import select_file_numbers, describe_file_numbers, latest_file_numbers
from src.translating import check_translation
from src.typed import TypedQuestion, CHOICES_LANGUAGE, construct_questions, check_answer
from src.writing import IndexedTerm, WORDS_PER_SENTENCE, index_vocabulary, pick_word_pairs, check_sentence

DEMO_VARIABLE: str = "LANGUAGES_DEMO"
MODEL_HEADER: str = "X-OpenAI-Model"
FRONTEND_DIST: Path = Path(__file__).resolve().parent.parent / "frontend" / "dist"

NOT_BUILT_PAGE: str = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Languages</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 36rem; margin: 4rem auto; padding: 0 1rem;
line-height: 1.6">
<h1>The frontend has not been built yet</h1>
<p>The API is running. To build the web app once, run:</p>
<pre style="background: #f3f1ec; padding: 1rem; border-radius: 0.5rem">cd frontend
npm install
npm run build</pre>
<p>Then reload this page.</p></body></html>"""


def demo_from_environment() -> bool:
    return environ.get(DEMO_VARIABLE, "").strip().lower() not in ("", "0", "false", "no")


def __vocabulary(code_: str) -> Vocabulary:
    return LANGUAGE_CODES[code_]


def __file_numbers(vocabulary_: Vocabulary, selection_: int | str) -> List[int]:
    try:
        file_numbers_ = select_file_numbers(vocabulary_, selection_)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"There is no file {vocabulary_.name.lower()}-{selection_}.md.")
    if not file_numbers_:
        raise HTTPException(status_code=400, detail=f"There are no {vocabulary_.name.capitalize()} vocabulary files.")

    return file_numbers_


def __openai_failure(error_: OpenAIError) -> HTTPException:
    return HTTPException(status_code=502, detail=f"The request to OpenAI failed: {error_}")


def __meta(demo_: bool) -> MetaModel:
    languages_ = []
    for code_, vocabulary_ in LANGUAGE_CODES.items():
        files_ = [{"number": i_, "name": basename(get_vocabulary_file_path(vocabulary_, i_)),
                   "terms": count_vocabulary_file_terms(vocabulary_, i_)}
                  for i_ in get_vocabulary_file_numbers(vocabulary_)]
        languages_.append({"code": code_, "name": vocabulary_.name.capitalize(),
                           "support_language": CHOICES_LANGUAGE[vocabulary_], "files": files_,
                           "latest": latest_file_numbers(vocabulary_)})

    return MetaModel.model_validate({
        "demo": demo_, "blank": BLANK, "levels": [level_.name for level_ in CEFRLevel], "languages": languages_,
        "defaults": {"language": language_code(DEFAULT_VOCABULARY), "level": DEFAULT_CEFR_LEVEL.name,
                     "questions": DEFAULT_NUMBER_OF_QUESTIONS, "sentences": DEFAULT_NUMBER_OF_SENTENCES,
                     "revise": REVISION_QUESTIONS_NUMBER, "seconds_per_question": SECONDS_PER_QUESTION,
                     "latest_files": LATEST_FILES_NUMBER, "max_count": MAX_COUNT,
                     "max_terms_per_file": MAX_TERMS_PER_FILE}})


def __frontend_file(path_: str) -> Response:
    index_ = FRONTEND_DIST / "index.html"
    if not index_.is_file():
        return HTMLResponse(NOT_BUILT_PAGE, status_code=503)

    file_ = (FRONTEND_DIST / path_).resolve()
    if path_ and file_.is_file() and FRONTEND_DIST in file_.parents:
        return FileResponse(file_)

    return FileResponse(index_, headers={"Cache-Control": "no-cache"})


def create_app(demo_: Optional[bool] = None) -> FastAPI:
    demo_ = demo_from_environment() if demo_ is None else demo_

    async def use_model(model_: Optional[str] = Header(default=None, alias=MODEL_HEADER)) -> None:
        model_ = (model_ or "").strip() or None
        if model_ and model_ not in await run_in_threadpool(available_models, demo_):
            raise HTTPException(status_code=400, detail=f"The model {model_} is not available.")
        select_model(model_)

    app_ = FastAPI(title="Languages", summary="Vocabulary, prepositions, and writing exercises.",
                   dependencies=[Depends(use_model)])

    @app_.get("/api/meta", response_model=MetaModel)
    def meta() -> MetaModel:
        return __meta(demo_)

    @app_.get("/api/models", response_model=ModelsModel)
    def models() -> ModelsModel:
        return ModelsModel.model_validate({"default": MODEL, "models": available_models(demo_)})

    @app_.post("/api/quiz", response_model=QuizModel)
    def quiz(request_: ExerciseRequestModel) -> QuizModel:
        vocabulary_ = __vocabulary(request_.language)
        file_numbers_ = __file_numbers(vocabulary_, request_.files)
        try:
            questions_ = openai_construct_exercise(request_.count, vocabulary_=vocabulary_,
                                                   cefr_level_=CEFRLevel[request_.level], unseen_alpha=UNSEEN_ALPHA,
                                                   file_numbers_=file_numbers_, demo=demo_)
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if not questions_:
            raise HTTPException(status_code=502, detail="No usable questions came back from the model. Try again.")

        return QuizModel.model_validate({"source": describe_file_numbers(vocabulary_, file_numbers_),
                                         "questions": questions_})

    @app_.post("/api/typed", response_model=TypedModel)
    def typed(request_: ExerciseRequestModel) -> TypedModel:
        vocabulary_ = __vocabulary(request_.language)
        file_numbers_ = __file_numbers(vocabulary_, request_.files)
        try:
            questions_ = construct_questions(vocabulary_, CEFRLevel[request_.level], request_.count, file_numbers_,
                                             demo_)
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if not questions_:
            raise HTTPException(status_code=502, detail="No usable questions came back from the model. Try again.")

        return TypedModel.model_validate({"source": describe_file_numbers(vocabulary_, file_numbers_),
                                          "questions": questions_})

    @app_.post("/api/typed/check", response_model=TypedCorrectionModel)
    def typed_check(request_: TypedCheckRequestModel) -> TypedCorrectionModel:
        answer_ = " ".join(request_.answer.split())
        if not answer_:
            raise HTTPException(status_code=400, detail="The answer is empty.")
        try:
            correction_, notice_ = check_answer(__vocabulary(request_.language),
                                                TypedQuestion(**request_.question.model_dump()), answer_, demo_)
        except OpenAIError as error_:
            raise __openai_failure(error_)

        return TypedCorrectionModel.model_validate({**vars(correction_), "notice": notice_})

    @app_.post("/api/prepositions", response_model=TypedModel)
    def prepositions(request_: ExerciseRequestModel) -> TypedModel:
        vocabulary_ = __vocabulary(request_.language)
        file_numbers_ = __file_numbers(vocabulary_, request_.files)
        try:
            questions_ = construct_prepositions(CEFRLevel[request_.level], request_.count, file_numbers_, demo_, vocabulary_)
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=str(error_))
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if not questions_:
            raise HTTPException(status_code=502, detail="No usable preposition questions came back. Try again.")

        return TypedModel.model_validate({"source": describe_file_numbers(vocabulary_, file_numbers_),
                                          "questions": questions_})

    @app_.post("/api/prepositions/check", response_model=TypedCorrectionModel)
    def prepositions_check(request_: TypedCheckRequestModel) -> TypedCorrectionModel:
        answer_ = " ".join(request_.answer.split())
        if not answer_:
            raise HTTPException(status_code=400, detail="The answer is empty.")
        try:
            correction_, notice_ = check_preposition(TypedQuestion(**request_.question.model_dump()), answer_, demo_,
                                                    __vocabulary(request_.language))
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=str(error_))
        except OpenAIError as error_:
            raise __openai_failure(error_)

        return TypedCorrectionModel.model_validate({**vars(correction_), "notice": notice_})

    @app_.post("/api/writing", response_model=WritingModel)
    def writing(request_: ExerciseRequestModel) -> WritingModel:
        vocabulary_ = __vocabulary(request_.language)
        file_numbers_ = __file_numbers(vocabulary_, request_.files)
        index_ = index_vocabulary(vocabulary_, file_numbers_)
        if len(index_) < WORDS_PER_SENTENCE:
            raise HTTPException(status_code=400,
                                detail=f"Not enough {vocabulary_.name.capitalize()} terms for this exercise.")

        return WritingModel.model_validate({"source": describe_file_numbers(vocabulary_, file_numbers_),
                                            "rounds": [list(pair_) for pair_ in pick_word_pairs(index_,
                                                                                                 request_.count)]})

    @app_.post("/api/writing/check", response_model=WritingCorrectionModel)
    def writing_check(request_: WritingCheckRequestModel) -> WritingCorrectionModel:
        sentence_ = request_.sentence.strip()
        if not sentence_:
            raise HTTPException(status_code=400, detail="The sentence is empty.")
        terms_ = [IndexedTerm(**term_.model_dump()) for term_ in request_.terms]
        try:
            correction_, notice_ = check_sentence(__vocabulary(request_.language), terms_, sentence_,
                                                    CEFRLevel[request_.level], demo_)
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if correction_ is None:
            raise HTTPException(status_code=502, detail=notice_)

        return WritingCorrectionModel.model_validate(correction_)

    @app_.post("/api/entries/define", response_model=DefinedEntryModel)
    def define(request_: DefineRequestModel) -> DefinedEntryModel:
        term_ = " ".join(request_.term.split())
        if not term_:
            raise HTTPException(status_code=400, detail="The term is empty.")
        try:
            entry_, notice_ = check_definition(__vocabulary(request_.language), term_, demo_)
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if entry_ is None:
            raise HTTPException(status_code=502, detail=notice_)

        return DefinedEntryModel.model_validate(entry_)

    @app_.post("/api/entries/translate", response_model=TranslationModel)
    def translate(request_: TranslateRequestModel) -> TranslationModel:
        phrase_ = " ".join(request_.phrase.split())
        if not phrase_:
            raise HTTPException(status_code=400, detail="The phrase is empty.")
        try:
            translation_, notice_ = check_translation(__vocabulary(request_.language), phrase_, demo_)
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if translation_ is None:
            raise HTTPException(status_code=502, detail=notice_)

        return TranslationModel.model_validate(translation_)

    @app_.post("/api/ask", response_model=AnswerModel)
    def ask(request_: AskRequestModel) -> AnswerModel:
        question_ = request_.question.strip()
        if not question_:
            raise HTTPException(status_code=400, detail="The question is empty.")
        history_ = [Turn(question=turn_.question, answer=turn_.answer) for turn_ in request_.history]
        try:
            answer_, notice_ = check_question(__vocabulary(request_.language), question_, history_, demo_)
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if answer_ is None:
            raise HTTPException(status_code=502, detail=notice_)

        return AnswerModel.model_validate(answer_)

    @app_.post("/api/entries/save", response_model=SaveResultModel)
    def save(request_: SaveRequestModel) -> SaveResultModel:
        try:
            result_ = save_entries(__vocabulary(request_.language), request_.entries, demo_)
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=f"An entry is not in the expected format: {error_}.")

        return SaveResultModel.model_validate({**vars(result_), "demo": demo_})

    @app_.post("/api/flashcards", response_model=FlashcardsModel)
    def flashcards(request_: FlashcardsRequestModel) -> FlashcardsModel:
        vocabulary_ = __vocabulary(request_.language)
        try:
            file_numbers_ = select_library_file_numbers(vocabulary_, request_.files)
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=f"The file selection is not valid: {error_}.")
        names_ = [library_file_name(vocabulary_, i_) for i_ in file_numbers_]

        return FlashcardsModel.model_validate({
            "source": ", ".join(names_) if names_ else "no files",
            "cards": cards_with_states(vocabulary_, file_numbers_, request_.direction)})

    @app_.post("/api/flashcards/review", response_model=ReviewModel)
    def flashcards_review(request_: ReviewRequestModel) -> ReviewModel:
        state_, intervals_ = review_card(__vocabulary(request_.language), request_.direction, request_.term,
                                         request_.grade, demo_)

        return ReviewModel.model_validate({"state": state_, "intervals": intervals_})

    @app_.get("/api/{path_:path}", include_in_schema=False)
    def api_not_found(path_: str):
        raise HTTPException(status_code=404, detail=f"There is no API endpoint /api/{path_}.")

    @app_.get("/{path_:path}", include_in_schema=False, response_model=None)
    def frontend(path_: str) -> Response:
        return __frontend_file(path_)

    return app_


app = create_app()
