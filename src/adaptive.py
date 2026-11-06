"""Private scheduling based on answered exercises, not generated questions."""
from datetime import datetime, timedelta, timezone
from random import choices
from sqlite3 import OperationalError

from src.database import get_database_connection


def _now():
    return datetime.now(timezone.utc)


def _schema(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS exercise_progress (
        vocabulary TEXT NOT NULL, term TEXT NOT NULL, skill TEXT NOT NULL,
        attempts INTEGER NOT NULL, mistakes INTEGER NOT NULL, streak INTEGER NOT NULL,
        last_answered TEXT NOT NULL, due_at TEXT NOT NULL,
        PRIMARY KEY (vocabulary, term, skill))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS vocabulary_allowance (
        vocabulary TEXT PRIMARY KEY, earned_reviews INTEGER NOT NULL DEFAULT 0,
        words_added INTEGER NOT NULL DEFAULT 0)''')
    connection.execute('''CREATE TABLE IF NOT EXISTS exercise_views (
        vocabulary TEXT NOT NULL, term TEXT NOT NULL, skill TEXT NOT NULL,
        last_seen TEXT NOT NULL, PRIMARY KEY (vocabulary, term, skill))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS exercise_events (
        event_id TEXT NOT NULL, vocabulary TEXT NOT NULL, term TEXT NOT NULL,
        PRIMARY KEY (event_id, vocabulary, term))''')


def record_answers(event_id, vocabulary, skill, answers, exempt_terms=frozenset()):
    now = _now()
    with get_database_connection() as connection:
        _schema(connection)
        for term, outcome, assisted in answers:
            inserted = connection.execute('INSERT OR IGNORE INTO exercise_events VALUES (?, ?, ?)',
                                          (event_id, vocabulary.name, term)).rowcount
            if not inserted:
                continue
            if outcome == 'seen':
                connection.execute('''INSERT INTO exercise_views VALUES (?, ?, ?, ?)
                    ON CONFLICT(vocabulary, term, skill) DO UPDATE SET last_seen=excluded.last_seen''',
                    (vocabulary.name, term, skill, now.isoformat()))
                continue
            row = connection.execute('SELECT attempts, mistakes, streak FROM exercise_progress WHERE vocabulary=? AND term=? AND skill=?',
                                     (vocabulary.name, term, skill)).fetchone()
            attempts, mistakes, streak = row if row else (0, 0, 0)
            if outcome == 'correct' and not assisted and term not in exempt_terms:
                connection.execute('''INSERT INTO vocabulary_allowance(vocabulary, earned_reviews) VALUES (?, 1)
                    ON CONFLICT(vocabulary) DO UPDATE SET earned_reviews=earned_reviews+1''', (vocabulary.name,))
            if outcome != 'correct':
                mistakes += 1
                streak = 0
                interval = timedelta(hours=6)
            elif assisted:
                streak = 0
                interval = timedelta(hours=18)
            else:
                streak += 1
                interval = timedelta(days=min(60, 2 ** min(streak - 1, 6)))
            connection.execute('''INSERT INTO exercise_progress VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vocabulary, term, skill) DO UPDATE SET attempts=excluded.attempts,
                mistakes=excluded.mistakes, streak=excluded.streak, last_answered=excluded.last_answered,
                due_at=excluded.due_at''', (vocabulary.name, term, skill, attempts + 1, mistakes, streak,
                                            now.isoformat(), (now + interval).isoformat()))


def select_entries(entries, vocabulary, skill, count):
    """Sample without replacement, favouring new, due and previously difficult terms."""
    pool = list(entries)
    if not pool or count <= 0:
        return []
    try:
        with get_database_connection() as connection:
            rows = connection.execute('SELECT term, mistakes, streak, last_answered, due_at FROM exercise_progress WHERE vocabulary=? AND skill=?',
                                      (vocabulary.name, skill)).fetchall()
            views = dict(connection.execute('SELECT term, last_seen FROM exercise_views WHERE vocabulary=? AND skill=?', (vocabulary.name, skill)).fetchall())
    except OperationalError:
        rows, views = [], {}
    states = {row[0]: row[1:] for row in rows}
    now = _now()
    weights = []
    for entry in pool:
        state = states.get(entry.term)
        if state is None:
            last_seen = views.get(entry.term)
            weights.append(0.1 if last_seen and now - datetime.fromisoformat(last_seen) < timedelta(minutes=10) else (4.0 if last_seen else 5.0))
            continue
        mistakes, streak, last_answered, due_at = state
        last = datetime.fromisoformat(last_answered)
        due = datetime.fromisoformat(due_at)
        if now - last < timedelta(minutes=10):
            weight = 0.1
        elif due > now:
            weight = 0.5
        else:
            weight = 6.0 + min(mistakes, 3) if streak == 0 else 6.0
        weights.append(weight)
    selected = []
    original_pool, original_weights = pool[:], weights[:]
    for _ in range(count):
        if not pool:
            pool, weights = original_pool[:], original_weights[:]
        index = choices(range(len(pool)), weights=weights, k=1)[0]
        selected.append(pool.pop(index))
        weights.pop(index)
    return selected


def allowance(vocabulary):
    with get_database_connection() as connection:
        _schema(connection)
        row = connection.execute('SELECT earned_reviews, words_added FROM vocabulary_allowance WHERE vocabulary=?', (vocabulary.name,)).fetchone()
        earned, added = row if row else (0, 0)
        return {'available': max(0, 10 + earned // 5 - added), 'reviews_toward_next': earned % 5}


def save_with_allowance(vocabulary, entries, category, save):
    if vocabulary.name == 'ENGLISH' and category == 'phrasal-verbs':
        return save(vocabulary, entries, category)
    connection = get_database_connection()
    try:
        connection.execute('BEGIN IMMEDIATE')
        _schema(connection)
        row = connection.execute('SELECT earned_reviews, words_added FROM vocabulary_allowance WHERE vocabulary=?', (vocabulary.name,)).fetchone()
        earned, added = row if row else (0, 0)
        remaining = max(0, 10 + earned // 5 - added)
        if len(entries) > remaining:
            raise ValueError(f'You can add {remaining} more {vocabulary.name.lower()} words. Complete more reviews to earn additional space.')
        result = save(vocabulary, entries, category)
        connection.execute("INSERT INTO vocabulary_allowance(vocabulary, words_added) VALUES (?, ?) ON CONFLICT(vocabulary) DO UPDATE SET words_added=words_added+excluded.words_added", (vocabulary.name, len(result.saved)))
        connection.commit()
        return result
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def exempt_phrasal_terms(vocabulary):
    if vocabulary.name != 'ENGLISH':
        return set()
    from src.library import all_library_files
    from src.parser import parse_vocabulary_to_list
    files = [file for file in all_library_files(vocabulary) if isinstance(file, str) and file.startswith('phrasal-verbs:')]
    return {entry.term for entry in parse_vocabulary_to_list(vocabulary, files)} if files else set()
