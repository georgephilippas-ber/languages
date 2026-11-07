from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.configuration import DEFAULT_CEFR_LEVEL

LanguageCode = Literal["EN", "DE", "FR"]
LevelName = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
Category = Literal["general", "legal", "financial", "phrasal-verbs"]
FileSelection = Literal["latest", "all", "current", "general", "legal", "financial", "phrasal-verbs"] | Annotated[str, Field(pattern=r"^(?:(?:general|legal|financial|phrasal-verbs):(?:current|latest)|(?:legal|financial|phrasal-verbs):[1-9][0-9]*)$")] | Annotated[int, Field(ge=1)]
Verdict = Literal["correct", "wrong_form", "wrong_word"]
Direction = Literal["forward", "reverse"]
Grade = Literal["again", "hard", "good", "easy"]

MAX_COUNT: int = 50


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True,
                              from_attributes=True)


class FileInfoModel(ApiModel):
    number: int | str
    name: str
    terms: int


class LanguageModel(ApiModel):
    code: LanguageCode
    name: str
    support_language: str
    files: List[FileInfoModel]
    latest: List[int]


class DefaultsModel(ApiModel):
    language: LanguageCode
    level: LevelName
    questions: int
    sentences: int
    revise: int
    seconds_per_question: int
    latest_files: int
    max_count: int
    max_terms_per_file: int


class MetaModel(ApiModel):
    blank: str
    levels: List[LevelName]
    topics: List[str]
    languages: List[LanguageModel]
    defaults: DefaultsModel


class ModelsModel(ApiModel):
    default: str
    models: List[str]


class ApiKeyModel(ApiModel):
    configured: bool
    hint: Optional[str] = None
    source: Optional[Literal["environment", "file"]] = None


class ApiKeyRequestModel(ApiModel):
    key: str


class ExerciseRequestModel(ApiModel):
    language: LanguageCode
    level: LevelName = DEFAULT_CEFR_LEVEL.name
    count: int = Field(ge=1, le=MAX_COUNT)
    files: FileSelection = "latest"


class QuizQuestionModel(ApiModel):
    term: str
    question: str
    choices: List[str]
    choices_translations: List[str]
    correct_choice: int
    complete_sentence: str
    english_translation: str


class QuizModel(ApiModel):
    source: str
    questions: List[QuizQuestionModel]


class TypedQuestionModel(ApiModel):
    term: str
    question: str
    hint: str
    correct_answer: str
    complete_sentence: str
    english_translation: str


class TypedModel(ApiModel):
    source: str
    questions: List[TypedQuestionModel]


class CorrectionModel(ApiModel):
    original: str
    corrected: str
    explanation: str


class TypedCheckRequestModel(ApiModel):
    language: LanguageCode
    question: TypedQuestionModel
    answer: str = Field(min_length=1, max_length=200)


class TypedCorrectionModel(ApiModel):
    verdict: Verdict
    corrected_answer: str
    errors: List[CorrectionModel]
    comment: str
    suggestions: List[str]
    notice: Optional[str] = None


class WritingTermModel(ApiModel):
    term: str
    file_name: str
    hint: str


class WritingModel(ApiModel):
    source: str
    rounds: List[List[WritingTermModel]]


class WritingCheckRequestModel(ApiModel):
    language: LanguageCode
    level: LevelName = DEFAULT_CEFR_LEVEL.name
    terms: List[WritingTermModel] = Field(min_length=1, max_length=4)
    sentence: str = Field(min_length=1, max_length=1000)


class TermCheckModel(ApiModel):
    term: str
    used: bool
    used_correctly: bool
    comment: str


class WritingCorrectionModel(ApiModel):
    is_correct: bool
    minimal_correction: str
    natural_version: str
    natural_explanation: str
    translation: str
    terms: List[TermCheckModel]
    corrections: List[CorrectionModel]
    feedback: str
    target_level: LevelName
    level: Literal["", "A1", "A2", "B1", "B2", "C1", "C2"]
    level_comment: str


class DefineRequestModel(ApiModel):
    language: LanguageCode
    term: str = Field(min_length=1, max_length=200)


class DefinedEntryModel(ApiModel):
    term: str
    markdown: str
    gloss: str


class TranslateRequestModel(ApiModel):
    language: LanguageCode
    phrase: str = Field(min_length=1, max_length=1000)


class TranslationModel(ApiModel):
    source_language: str
    target_language: str
    translation: str
    notes: List[str]


class AskTurnModel(ApiModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(max_length=20000)


class AskRequestModel(ApiModel):
    language: LanguageCode
    question: str = Field(min_length=1, max_length=2000)
    history: List[AskTurnModel] = Field(default_factory=list, max_length=MAX_COUNT)


class ReadRequestModel(ApiModel):
    language: LanguageCode
    topic: str = Field(min_length=1, max_length=50)
    level: LevelName = DEFAULT_CEFR_LEVEL.name
    mode: Literal["find", "url", "text"] = "find"
    source: str = Field(default="", max_length=24000)
    summary_words: int = Field(default=80, ge=25, le=300)


class ArticleModel(ApiModel):
    published_at: str = ""
    retrieved_at: str = ""
    topic: str
    title: str
    publication: str
    url: str = ""
    summary: str
    words: List[str]


class AnswerModel(ApiModel):
    on_topic: bool
    answer: str


class SaveRequestModel(ApiModel):
    category: Category = "general"
    language: LanguageCode
    entries: List[str] = Field(min_length=1, max_length=MAX_COUNT)


class SavedEntryModel(ApiModel):
    term: str
    file_name: str
    terms_in_file: int


class SaveResultModel(ApiModel):
    saved: List[SavedEntryModel]
    file_name: str
    terms_in_file: int
    file_full: bool


class FlashcardsRequestModel(ApiModel):
    language: LanguageCode
    files: FileSelection = "all"
    direction: Direction = "forward"


class CardSectionModel(ApiModel):
    label: str
    text: str


class CardStateModel(ApiModel):
    ease: float
    interval_days: float
    repetitions: int
    lapses: int
    due_at: Optional[str] = None
    reviewed_at: Optional[str] = None


class FlashcardModel(ApiModel):
    term: str
    file_name: str
    sections: List[CardSectionModel]
    state: CardStateModel
    is_new: bool
    is_due: bool
    intervals: Dict[Grade, str]


class FlashcardsModel(ApiModel):
    source: str
    cards: List[FlashcardModel]


class ReviewModel(ApiModel):
    state: CardStateModel
    intervals: Dict[Grade, str]


class ReviewRequestModel(ApiModel):
    language: LanguageCode
    direction: Direction = "forward"
    term: str = Field(min_length=1)
    grade: Grade


class MixedTranslationRequestModel(ApiModel):
    mode: Literal['recognize', 'produce']
    level: LevelName = DEFAULT_CEFR_LEVEL.name
    count: int = Field(ge=1, le=MAX_COUNT)
    include_phrasal: bool = False
    pair_language: Optional[LanguageCode] = None


class MixedTranslationQuestionModel(ApiModel):
    source_language: LanguageCode
    target_language: LanguageCode
    source_sentence: str
    segments: List[str]
    answers: List[str]
    hint: str = ''
    choices: List[List[str]] = []
    correct_choice: int = 0
    terms: List[str]


class MixedTranslationSetModel(ApiModel):
    source: str
    questions: List[MixedTranslationQuestionModel]


class MixedTranslationCheckModel(ApiModel):
    question: MixedTranslationQuestionModel
    answers: List[str] = Field(min_length=1, max_length=2)


class MixedTranslationCorrectionModel(ApiModel):
    verdict: Verdict
    corrected_answers: List[str]
    comment: str = ''


class SpeechRequestModel(ApiModel):
    text: str = Field(min_length=1, max_length=1000)
    language: LanguageCode


class AdaptiveAnswerModel(ApiModel):
    term: str = Field(min_length=1, max_length=500)
    outcome: Literal['correct', 'partial', 'wrong', 'seen']
    assisted: bool = False


class AdaptiveEventModel(ApiModel):
    event_id: str = Field(min_length=1, max_length=120)
    language: LanguageCode
    skill: Literal['recognize', 'produce', 'prepositions', 'articles', 'writing']
    answers: List[AdaptiveAnswerModel] = Field(min_length=1, max_length=2)



class BookInputModel(ApiModel):
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(default='', max_length=500)
    isbn: str = Field(default='', max_length=30)
    language: str = Field(min_length=1, max_length=100)
    progress: int = Field(ge=0, le=100)
    status: Literal['current', 'done']
    category: str = Field(default='other', min_length=1, max_length=80, pattern=r'^[a-z0-9][a-z0-9-]*$')
    rating: Optional[int] = Field(default=None, ge=1, le=10)
    personal_category: Optional[Literal['work', 'education', 'personal-development', 'literature']] = None


class BookModel(BookInputModel):
    total_pages: Optional[int] = None
    current_page: Optional[int] = None
    id: str
    created_at: str
    updated_at: str


class BookRecommendationExclusionModel(ApiModel):
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(default='', max_length=500)


class BookRecommendationRequestModel(ApiModel):
    category: str = Field(default='all', min_length=1, max_length=80, pattern=r'^[a-z0-9][a-z0-9-]*$')
    language: str = Field(min_length=1, max_length=100)
    exclude: List[BookRecommendationExclusionModel] = Field(default_factory=list, max_length=50)


class ToReadInputModel(ApiModel):
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(default='', max_length=500)
    isbn: str = Field(default='', max_length=30)
    language: str = Field(min_length=1, max_length=100)
    category: Literal['work', 'education', 'personal-development', 'literature']


class ToReadModel(ToReadInputModel):
    id: str
    created_at: str


class BookCategoryInputModel(ApiModel):
    name: str = Field(min_length=1, max_length=80)


class BookNotesModel(ApiModel):
    markdown: str = Field(max_length=1000000)
    revision: int = Field(ge=0)


class BookProgressModel(ApiModel):
    progress: int = Field(ge=0, le=100)
    current_page: Optional[int] = Field(default=None, ge=0, le=100000)
    total_pages: Optional[int] = Field(default=None, ge=1, le=100000)
