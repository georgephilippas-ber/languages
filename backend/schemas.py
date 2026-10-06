from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.configuration import DEFAULT_CEFR_LEVEL

LanguageCode = Literal["EN", "DE", "FR"]
LevelName = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
FileSelection = Literal["latest", "all"] | Annotated[int, Field(ge=1)]
Verdict = Literal["correct", "wrong_form", "wrong_word"]

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


class DefaultsModel(ApiModel):
    language: LanguageCode
    level: LevelName
    questions: int
    sentences: int
    revise: int
    seconds_per_question: int
    latest_files: int
    max_count: int


class MetaModel(ApiModel):
    demo: bool
    blank: str
    levels: List[LevelName]
    languages: List[LanguageModel]
    defaults: DefaultsModel


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
    choices: List[str]
    choices_translations: List[str]
    correct_choice: int
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
