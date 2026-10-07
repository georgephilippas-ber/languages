from typing import Annotated, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.configuration import DEFAULT_CEFR_LEVEL

LanguageCode = Literal["EN", "DE", "FR"]
LevelName = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
FileSelection = Literal["latest", "all"] | Annotated[int, Field(ge=1)]
Verdict = Literal["correct", "wrong_form", "wrong_word"]
KindName = Literal["vocabulary", "idioms", "grammatical"]
Direction = Literal["forward", "reverse"]
Grade = Literal["again", "hard", "good", "easy"]

MAX_COUNT: int = 50


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True,
                              from_attributes=True)


class FileInfoModel(ApiModel):
    number: int
    name: str
    terms: int


class LanguageModel(ApiModel):
    code: LanguageCode
    name: str
    support_language: str
    files: List[FileInfoModel]
    latest: List[int]
    idioms: List[FileInfoModel]
    grammatical: List[FileInfoModel]


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
    demo: bool
    blank: str
    levels: List[LevelName]
    languages: List[LanguageModel]
    defaults: DefaultsModel


class ModelsModel(ApiModel):
    default: str
    models: List[str]


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
    kind: KindName = "vocabulary"
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


class AnswerModel(ApiModel):
    on_topic: bool
    answer: str


class SaveRequestModel(ApiModel):
    language: LanguageCode
    kind: KindName = "vocabulary"
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
    demo: bool


class FlashcardsRequestModel(ApiModel):
    language: LanguageCode
    kind: KindName = "vocabulary"
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
    kind: KindName = "vocabulary"
    direction: Direction = "forward"
    term: str = Field(min_length=1)
    grade: Grade
