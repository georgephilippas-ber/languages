import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from sqlite3 import OperationalError
from typing import Dict, List, Optional, Tuple

from src.configuration import LATEST_FILES_NUMBER
from src.database import get_database_connection
from src.domain import Vocabulary
from src.library import library_file_name, library_file_numbers, read_library_file, split_entries

GRADES: List[str] = ["again", "hard", "good", "easy"]
DIRECTIONS: List[str] = ["forward", "reverse"]

START_EASE: float = 2.5
MIN_EASE: float = 1.3
AGAIN_MINUTES: int = 10
HARD_FACTOR: float = 1.2
EASY_BONUS: float = 1.3
FIRST_INTERVALS: Dict[str, float] = {"hard": 1, "good": 1, "easy": 4}
SECOND_GOOD_INTERVAL: float = 3

TRANSLATION_LABELS: List[str] = ["English", "German", "French"]
TRANSLATION_SECTION: str = "Translation"

LABEL_REGEXP = re.compile(r"^\*\*([A-Za-z ]+):\*\*\s*(.*)$", flags=re.S)
PLAIN_LABEL_REGEXP = re.compile(r"^(Another example|Useful nuance):\s*(.*)$", flags=re.S)
BULLET_REGEXP = re.compile(r"^[*-] ")


@dataclass
class CardSection:
    label: str
    text: str


@dataclass
class CardState:
    ease: float = START_EASE
    interval_days: float = 0
    repetitions: int = 0
    lapses: int = 0
    due_at: Optional[str] = None
    reviewed_at: Optional[str] = None


@dataclass
class Flashcard:
    term: str
    file_name: str
    sections: List[CardSection]
    state: CardState = field(default_factory=CardState)
    is_new: bool = True
    is_due: bool = True
    intervals: Dict[str, str] = field(default_factory=dict)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def select_library_file_numbers(vocabulary_: Vocabulary, selection_: int | str) -> List[int]:
    file_numbers_ = library_file_numbers(vocabulary_)
    if selection_ == "all":
        return file_numbers_
    if selection_ == "latest":
        return file_numbers_[-LATEST_FILES_NUMBER:]
    if selection_ not in file_numbers_:
        raise ValueError(f"there is no file {library_file_name(vocabulary_, int(selection_))}")

    return [int(selection_)]


def __paragraph_text(paragraph_: str) -> str:
    text_ = ""
    for line_ in paragraph_.strip().splitlines():
        line_ = line_.strip()
        text_ += ("\n" if BULLET_REGEXP.match(line_) and text_ else " " if text_ else "") + line_

    return text_


def entry_sections(body_: str) -> List[CardSection]:
    sections_: List[CardSection] = []
    for paragraph_ in re.split(r"\n\s*\n", body_):
        if not paragraph_.strip():
            continue
        text_ = __paragraph_text(paragraph_)
        label_match_ = LABEL_REGEXP.match(text_)
        plain_match_ = PLAIN_LABEL_REGEXP.match(text_)
        if label_match_ and label_match_.group(1) in TRANSLATION_LABELS:
            sections_.append(CardSection(label=TRANSLATION_SECTION, text=text_))
        elif label_match_:
            sections_.append(CardSection(label=label_match_.group(1), text=label_match_.group(2).strip()))
        elif plain_match_:
            sections_.append(CardSection(label=plain_match_.group(1), text=plain_match_.group(2).strip()))
        elif sections_:
            sections_[-1].text += "\n\n" + text_
        else:
            sections_.append(CardSection(label="Note", text=text_))

    return sections_


def read_cards(vocabulary_: Vocabulary, file_numbers_: List[int]) -> List[Flashcard]:
    cards_: List[Flashcard] = []
    for file_number_ in file_numbers_:
        for entry_ in split_entries(read_library_file(vocabulary_, file_number_)):
            heading_, _, body_ = entry_.partition("\n")
            cards_.append(Flashcard(term=heading_[3:].strip(), file_name=library_file_name(vocabulary_, file_number_),
                                    sections=entry_sections(body_)))

    return cards_


def __create_table(connection_) -> None:
    connection_.execute(
        """
        CREATE TABLE IF NOT EXISTS flashcard_reviews
        (
            id            INTEGER PRIMARY KEY,
            vocabulary    TEXT    NOT NULL,
            term          TEXT    NOT NULL,
            direction     TEXT    NOT NULL,
            ease          REAL    NOT NULL,
            interval_days REAL    NOT NULL,
            repetitions   INTEGER NOT NULL,
            lapses        INTEGER NOT NULL,
            due_at        TEXT    NOT NULL,
            reviewed_at   TEXT    NOT NULL,
            UNIQUE (vocabulary, term, direction)
        )
        """
    )


def retrieve_states(vocabulary_: Vocabulary, direction_: str) -> Dict[str, CardState]:
    connection_ = get_database_connection()
    try:
        rows_ = connection_.execute(
            """
            SELECT term, ease, interval_days, repetitions, lapses, due_at, reviewed_at
            FROM flashcard_reviews
            WHERE vocabulary = ? AND direction = ?
            """,
            (vocabulary_.name, direction_)).fetchall()
    except OperationalError:
        rows_ = []
    finally:
        connection_.close()

    return {row_[0]: CardState(*row_[1:]) for row_ in rows_}


def store_state(vocabulary_: Vocabulary, direction_: str, term_: str, state_: CardState) -> None:
    connection_ = get_database_connection()
    try:
        __create_table(connection_)
        connection_.execute(
            """
            INSERT INTO flashcard_reviews (vocabulary, term, direction, ease, interval_days, repetitions, lapses, due_at,
                                           reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vocabulary, term, direction) DO UPDATE SET ease          = excluded.ease,
                                                                   interval_days = excluded.interval_days,
                                                                   repetitions   = excluded.repetitions,
                                                                   lapses        = excluded.lapses,
                                                                   due_at        = excluded.due_at,
                                                                   reviewed_at   = excluded.reviewed_at;
            """,
            (vocabulary_.name, term_, direction_, state_.ease, state_.interval_days, state_.repetitions, state_.lapses,
             state_.due_at, state_.reviewed_at))
        connection_.commit()
    finally:
        connection_.close()


def schedule(state_: CardState, grade_: str, now_: datetime) -> CardState:
    if grade_ not in GRADES:
        raise ValueError(f"unknown grade {grade_!r}")

    ease_, interval_, repetitions_, lapses_ = state_.ease, state_.interval_days, state_.repetitions, state_.lapses
    if grade_ == "again":
        lapses_ += 1 if repetitions_ > 0 else 0
        repetitions_ = 0
        ease_ = max(MIN_EASE, ease_ - 0.2)
        interval_ = AGAIN_MINUTES / (24 * 60)
    else:
        if repetitions_ == 0:
            interval_ = FIRST_INTERVALS[grade_]
        elif grade_ == "hard":
            interval_ = max(1.0, interval_ * HARD_FACTOR)
        elif grade_ == "good":
            interval_ = SECOND_GOOD_INTERVAL if repetitions_ == 1 else max(1.0, interval_ * ease_)
        else:
            interval_ = max(SECOND_GOOD_INTERVAL + 1, interval_ * ease_ * EASY_BONUS)
        interval_ = float(round(interval_))
        ease_ = max(MIN_EASE, ease_ - 0.15) if grade_ == "hard" else ease_ + 0.15 if grade_ == "easy" else ease_
        repetitions_ += 1

    return CardState(ease=round(ease_, 2), interval_days=interval_, repetitions=repetitions_, lapses=lapses_,
                     due_at=(now_ + timedelta(days=interval_)).isoformat(timespec="seconds"),
                     reviewed_at=now_.isoformat(timespec="seconds"))


def describe_interval(days_: float) -> str:
    if days_ < 1:
        return f"{round(days_ * 24 * 60)} min"
    if days_ < 31:
        return f"{round(days_)} d"
    if days_ < 365:
        return f"{round(days_ / 30.4, 1):g} mo"

    return f"{round(days_ / 365, 1):g} y"


def next_intervals(state_: CardState, now_: datetime) -> Dict[str, str]:
    return {grade_: describe_interval(schedule(state_, grade_, now_).interval_days) for grade_ in GRADES}


def cards_with_states(vocabulary_: Vocabulary, file_numbers_: List[int], direction_: str,
                      now_: Optional[datetime] = None) -> List[Flashcard]:
    now_ = now_ if now_ is not None else now_utc()
    states_ = retrieve_states(vocabulary_, direction_)

    cards_ = read_cards(vocabulary_, file_numbers_)
    for card_ in cards_:
        if card_.term in states_:
            card_.state = states_[card_.term]
            card_.is_new = False
            card_.is_due = datetime.fromisoformat(card_.state.due_at) <= now_
        else:
            card_.is_due = False
        card_.intervals = next_intervals(card_.state, now_)

    return cards_


def review_card(vocabulary_: Vocabulary, direction_: str, term_: str, grade_: str,
                demo_: bool = False) -> Tuple[CardState, Dict[str, str]]:
    now_ = now_utc()
    state_ = schedule(retrieve_states(vocabulary_, direction_).get(term_, CardState()), grade_, now_)
    if not demo_:
        store_state(vocabulary_, direction_, term_, state_)

    return state_, next_intervals(state_, now_)
