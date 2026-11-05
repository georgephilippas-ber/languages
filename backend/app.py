from contextlib import asynccontextmanager
from os.path import basename
from pathlib import Path
from typing import Callable, List, Optional
from secrets import token_urlsafe
from hmac import compare_digest
from threading import Timer

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, Response
from openai import OpenAIError

from backend.schemas import MAX_COUNT, ExerciseRequestModel, MetaModel, QuizModel, TypedModel, \
    TypedCheckRequestModel, TypedCorrectionModel, WritingModel, WritingCheckRequestModel, WritingCorrectionModel, \
    DefineRequestModel, DefinedEntryModel, SaveRequestModel, SaveResultModel, FlashcardsRequestModel, \
    FlashcardsModel, ReviewRequestModel, ReviewModel, TranslateRequestModel, TranslationModel, AskRequestModel, \
    AnswerModel, ModelsModel, ReadRequestModel, ArticleModel, ApiKeyModel, ApiKeyRequestModel
from src.api_key import api_key_status, normalize_api_key, save_api_key
from src.adding import check_definition, save_entries
from src.articles import construct_questions as construct_articles, check_answer as check_articles
from src.asking import Turn, check_question
from src.reading import TOPICS, check_article
from src.configuration import DEFAULT_NUMBER_OF_QUESTIONS, DEFAULT_NUMBER_OF_SENTENCES, DEFAULT_VOCABULARY, \
    DEFAULT_CEFR_LEVEL, REVISION_QUESTIONS_NUMBER, SECONDS_PER_QUESTION, LATEST_FILES_NUMBER, UNSEEN_ALPHA, MODEL
from src.domain import Vocabulary, CEFRLevel, BLANK, LANGUAGE_CODES, language_code
from src.device_access import DeviceAccess
from src.internet_access import InternetAccess
from src.flashcards import cards_with_states, review_card, select_library_file_numbers
from src.library import MAX_TERMS_PER_FILE, library_file_name, all_library_files
from src.models import available_models
from src.openai_integration import openai_construct_exercise, select_model
from src.parser import get_vocabulary_file_numbers, get_vocabulary_file_path, count_vocabulary_file_terms
from src.prepositions import construct_questions as construct_prepositions, check_answer as check_preposition
from src.selection import select_file_numbers, describe_file_numbers, latest_file_numbers
from src.translating import check_translation
from src.typed import TypedQuestion, CHOICES_LANGUAGE, construct_questions, check_answer
from src.writing import IndexedTerm, WORDS_PER_SENTENCE, index_vocabulary, pick_word_pairs, check_sentence

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


def __meta() -> MetaModel:
    languages_ = []
    for code_, vocabulary_ in LANGUAGE_CODES.items():
        files_ = [{"number": i_, "name": basename(get_vocabulary_file_path(vocabulary_, i_)),
                   "terms": count_vocabulary_file_terms(vocabulary_, i_)}
                  for i_ in all_library_files(vocabulary_)]
        languages_.append({"code": code_, "name": vocabulary_.name.capitalize(),
                           "support_language": CHOICES_LANGUAGE[vocabulary_], "files": files_,
                           "latest": latest_file_numbers(vocabulary_)})

    return MetaModel.model_validate({
        "blank": BLANK, "levels": [level_.name for level_ in CEFRLevel], "topics": list(TOPICS),
        "languages": languages_,
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


def create_app(shutdown: Optional[Callable[[], None]] = None) -> FastAPI:
    exit_token = token_urlsafe(32)
    async def use_model(model_: Optional[str] = Header(default=None, alias=MODEL_HEADER)) -> None:
        model_ = (model_ or "").strip() or None
        if model_ and model_ not in await run_in_threadpool(available_models):
            raise HTTPException(status_code=400, detail=f"The model {model_} is not available.")
        select_model(model_)

    device_access = DeviceAccess(None)
    internet_access = InternetAccess(None)

    @asynccontextmanager
    async def lifespan(app):
        yield
        device_access.close()
        internet_access.stop()

    app_ = FastAPI(title="Languages", summary="Vocabulary, prepositions, and writing exercises.",
                   dependencies=[Depends(use_model)], lifespan=lifespan)
    device_access.app = app_
    internet_access.app = app_

    def require_local_request(request: Request, action: str = "Exit"):
        if request.url.hostname not in ("127.0.0.1", "localhost", "::1") or not request.client or request.client.host not in ("127.0.0.1", "::1", "testclient"):
            raise HTTPException(status_code=403, detail=f"{action} is only available locally.")
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(status_code=403, detail=f"{action} requires a same-origin request.")

    @app_.get("/api/device")
    def device_status(request: Request):
        require_local_request(request, "Device access")
        return device_access.status()

    @app_.post("/api/device/start")
    def start_device(request: Request):
        require_local_request(request, "Device access")
        try:
            return device_access.start()
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error))

    @app_.post("/api/device/revoke")
    def revoke_device(request: Request):
        require_local_request(request, "Device access")
        return device_access.revoke()

    @app_.post("/api/device/awake/{minutes}")
    def awake_device(request: Request, minutes: int):
        require_local_request(request, "Keep awake")
        try:
            return device_access.keep_awake(minutes)
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error))

    @app_.get("/api/internet")
    def internet_status(request: Request):
        require_local_request(request, "Internet access")
        return internet_access.status()

    @app_.post("/api/internet/start")
    def start_internet(request: Request):
        require_local_request(request, "Internet access")
        try:
            return internet_access.start()
        except (OSError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error))

    @app_.post("/api/internet/stop")
    def stop_internet(request: Request):
        require_local_request(request, "Internet access")
        return internet_access.stop()

    @app_.get("/api/lifecycle")
    def lifecycle(request: Request):
        require_local_request(request)
        return {"exitToken": exit_token if shutdown else None}

    @app_.post("/api/exit")
    def exit_app(request: Request, token: str = Header(default="", alias="X-Languages-Exit")):
        require_local_request(request)
        if shutdown is None:
            raise HTTPException(status_code=409, detail="Quit the development server from its terminal.")
        if not compare_digest(token, exit_token):
            raise HTTPException(status_code=403, detail="Invalid exit token. Reload the page and try again.")
        timer = Timer(0.4, shutdown)
        timer.daemon = True
        timer.start()
        return {"status": "quitting"}

    @app_.get("/api/settings/api-key", response_model=ApiKeyModel)
    def api_key(request: Request) -> ApiKeyModel:
        require_local_request(request, "The API key status")
        return ApiKeyModel.model_validate(api_key_status())

    @app_.put("/api/settings/api-key", response_model=ApiKeyModel)
    def set_api_key(request: Request, request_: ApiKeyRequestModel) -> ApiKeyModel:
        require_local_request(request, "Changing the API key")
        try:
            key_ = normalize_api_key(request_.key)
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=f"{error_}.")
        save_api_key(key_)

        return ApiKeyModel.model_validate(api_key_status())

    @app_.get("/api/health")
    def health():
        from src.domain import DATA_ROOT
        return {"application": "languages", "dataRoot": DATA_ROOT}

    @app_.get("/api/meta", response_model=MetaModel)
    def meta() -> MetaModel:
        return __meta()

    @app_.get("/api/models", response_model=ModelsModel)
    def models() -> ModelsModel:
        return ModelsModel.model_validate({"default": MODEL, "models": available_models()})

    @app_.post("/api/read", response_model=ArticleModel)
    def read(request_: ReadRequestModel) -> ArticleModel:
        topic_ = " ".join(request_.topic.split()).lower()
        if topic_ not in TOPICS:
            raise HTTPException(status_code=400,
                                detail=f"{topic_.capitalize()} is not one of the topics: {', '.join(TOPICS)}.")
        try:
            article_, notice_ = check_article(__vocabulary(request_.language), topic_, CEFRLevel[request_.level])
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if article_ is None:
            raise HTTPException(status_code=502, detail=notice_)

        return ArticleModel.model_validate(vars(article_))

    @app_.post("/api/quiz", response_model=QuizModel)
    def quiz(request_: ExerciseRequestModel) -> QuizModel:
        vocabulary_ = __vocabulary(request_.language)
        file_numbers_ = __file_numbers(vocabulary_, request_.files)
        try:
            questions_ = openai_construct_exercise(request_.count, vocabulary_=vocabulary_,
                                                   cefr_level_=CEFRLevel[request_.level], unseen_alpha=UNSEEN_ALPHA,
                                                   file_numbers_=file_numbers_)
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
            questions_ = construct_questions(vocabulary_, CEFRLevel[request_.level], request_.count, file_numbers_)
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
                                                TypedQuestion(**request_.question.model_dump()), answer_)
        except OpenAIError as error_:
            raise __openai_failure(error_)

        return TypedCorrectionModel.model_validate({**vars(correction_), "notice": notice_})

    @app_.post("/api/prepositions", response_model=TypedModel)
    def prepositions(request_: ExerciseRequestModel) -> TypedModel:
        vocabulary_ = __vocabulary(request_.language)
        file_numbers_ = __file_numbers(vocabulary_, request_.files)
        try:
            questions_ = construct_prepositions(CEFRLevel[request_.level], request_.count, file_numbers_, vocabulary_)
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
            correction_, notice_ = check_preposition(TypedQuestion(**request_.question.model_dump()), answer_,
                                                    __vocabulary(request_.language))
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=str(error_))
        except OpenAIError as error_:
            raise __openai_failure(error_)

        return TypedCorrectionModel.model_validate({**vars(correction_), "notice": notice_})

    @app_.post("/api/articles", response_model=TypedModel)
    def articles(request_: ExerciseRequestModel) -> TypedModel:
        vocabulary_ = __vocabulary(request_.language)
        file_numbers_ = __file_numbers(vocabulary_, request_.files)
        try:
            questions_ = construct_articles(CEFRLevel[request_.level], request_.count, file_numbers_, vocabulary_)
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=str(error_))
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if not questions_:
            raise HTTPException(status_code=502, detail="No usable article questions came back. Try again.")

        return TypedModel.model_validate({"source": describe_file_numbers(vocabulary_, file_numbers_),
                                          "questions": questions_})

    @app_.post("/api/articles/check", response_model=TypedCorrectionModel)
    def articles_check(request_: TypedCheckRequestModel) -> TypedCorrectionModel:
        answer_ = " ".join(request_.answer.split())
        if not answer_:
            raise HTTPException(status_code=400, detail="The answer is empty.")
        try:
            correction_, notice_ = check_articles(TypedQuestion(**request_.question.model_dump()), answer_,
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
                                                    CEFRLevel[request_.level])
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
            entry_, notice_ = check_definition(__vocabulary(request_.language), term_)
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
            translation_, notice_ = check_translation(__vocabulary(request_.language), phrase_)
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
            answer_, notice_ = check_question(__vocabulary(request_.language), question_, history_)
        except OpenAIError as error_:
            raise __openai_failure(error_)
        if answer_ is None:
            raise HTTPException(status_code=502, detail=notice_)

        return AnswerModel.model_validate(answer_)

    @app_.post("/api/entries/save", response_model=SaveResultModel)
    def save(request_: SaveRequestModel) -> SaveResultModel:
        try:
            result_ = save_entries(__vocabulary(request_.language), request_.entries, request_.category)
        except ValueError as error_:
            raise HTTPException(status_code=400, detail=f"An entry is not in the expected format: {error_}.")

        return SaveResultModel.model_validate(result_)

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
                                         request_.grade)

        return ReviewModel.model_validate({"state": state_, "intervals": intervals_})

    @app_.get("/api/{path_:path}", include_in_schema=False)
    def api_not_found(path_: str):
        raise HTTPException(status_code=404, detail=f"There is no API endpoint /api/{path_}.")

    @app_.get("/{path_:path}", include_in_schema=False, response_model=None)
    def frontend(path_: str) -> Response:
        return __frontend_file(path_)

    return app_


app = create_app()
