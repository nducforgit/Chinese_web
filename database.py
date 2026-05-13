import os
import random
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

DAILY_REVIEW_LIMIT = 20
TZ_GMT7 = timezone(timedelta(hours=7))
VALID_LEVELS = ("HSK2", "HSK3", "HSK4")


def _today_utc_range():
    now_gmt7 = datetime.now(TZ_GMT7)
    start_gmt7 = now_gmt7.replace(hour=0, minute=0, second=0, microsecond=0)
    end_gmt7 = start_gmt7 + timedelta(days=1)
    to_utc = lambda dt: dt.astimezone(timezone.utc).replace(tzinfo=None)
    return to_utc(start_gmt7), to_utc(end_gmt7)


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id SERIAL PRIMARY KEY,
            hanzi TEXT NOT NULL,
            pinyin TEXT NOT NULL,
            meaning TEXT NOT NULL,
            example_zh TEXT DEFAULT '',
            example_vn TEXT DEFAULT '',
            hsk_level TEXT DEFAULT 'HSK2',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            word_id INTEGER NOT NULL REFERENCES words(id),
            interval INTEGER DEFAULT 1,
            repetitions INTEGER DEFAULT 0,
            easiness REAL DEFAULT 2.5,
            next_review TIMESTAMP DEFAULT NOW(),
            last_review TIMESTAMP
        )
    """)

    c.execute("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'words' AND column_name = 'hsk_level'
    """)
    if c.fetchone()[0] == 0:
        c.execute("ALTER TABLE words ADD COLUMN hsk_level TEXT DEFAULT 'HSK2'")

    c.execute("CREATE INDEX IF NOT EXISTS idx_words_hsk ON words(hsk_level)")

    conn.commit()
    conn.close()


def add_word(hanzi: str, pinyin: str, meaning: str,
             example_zh: str = "", example_vn: str = "",
             hsk_level: str = "HSK2"):
    if hsk_level not in VALID_LEVELS:
        hsk_level = "HSK2"
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO words (hanzi, pinyin, meaning, example_zh, example_vn, hsk_level) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (hanzi, pinyin, meaning, example_zh, example_vn, hsk_level)
    )
    word_id = c.fetchone()[0]
    c.execute("INSERT INTO reviews (word_id) VALUES (%s)", (word_id,))
    conn.commit()
    conn.close()


def _level_clause(hsk_level):
    if hsk_level and hsk_level in VALID_LEVELS:
        return " AND w.hsk_level = %s", (hsk_level,)
    return "", ()


def get_due_words(hsk_level: str = None):
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now()
    extra, params = _level_clause(hsk_level)
    c.execute(f"""
        SELECT w.id, w.hanzi, w.pinyin, w.meaning, w.example_zh, w.example_vn, w.hsk_level,
               r.interval, r.repetitions, r.easiness, r.next_review
        FROM words w
        JOIN reviews r ON w.id = r.word_id
        WHERE r.next_review <= %s{extra}
        ORDER BY r.next_review ASC
    """, (now, *params))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    if len(rows) > DAILY_REVIEW_LIMIT:
        rows = random.sample(rows, DAILY_REVIEW_LIMIT)
    return rows


def get_all_words(hsk_level: str = None):
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    extra, params = _level_clause(hsk_level)
    c.execute(f"""
        SELECT w.id, w.hanzi, w.pinyin, w.meaning, w.example_zh, w.example_vn, w.hsk_level,
               r.interval, r.repetitions, r.next_review
        FROM words w
        JOIN reviews r ON w.id = r.word_id
        WHERE 1=1{extra}
        ORDER BY w.created_at DESC
    """, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    for r in rows:
        if isinstance(r.get("next_review"), datetime):
            r["next_review"] = r["next_review"].isoformat()
    return rows


def update_review(word_id: int, quality: int):
    conn = get_conn()
    c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT * FROM reviews WHERE word_id = %s", (word_id,))
    r = dict(c.fetchone())

    easiness = r["easiness"]
    repetitions = r["repetitions"]
    interval = r["interval"]

    easiness = max(1.3, easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * easiness)
        repetitions += 1

    next_review = datetime.now() + timedelta(days=interval)

    c.execute("""
        UPDATE reviews
        SET interval = %s, repetitions = %s, easiness = %s,
            next_review = %s, last_review = NOW()
        WHERE word_id = %s
    """, (interval, repetitions, easiness, next_review, word_id))

    conn.commit()
    conn.close()


def delete_word(word_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM reviews WHERE word_id = %s", (word_id,))
    c.execute("DELETE FROM words WHERE id = %s", (word_id,))
    conn.commit()
    conn.close()


def auto_seed():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM words")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    from hsk_data import HSK2, HSK3, HSK4
    for level, words in (("HSK2", HSK2), ("HSK3", HSK3), ("HSK4", HSK4)):
        rows = [
            (w[0], w[1], w[2],
             w[3] if len(w) > 3 else "",
             w[4] if len(w) > 4 else "",
             level)
            for w in words
        ]
        execute_values(c,
            "INSERT INTO words (hanzi, pinyin, meaning, example_zh, example_vn, hsk_level) "
            "VALUES %s RETURNING id",
            rows
        )
        word_ids = [row[0] for row in c.fetchall()]
        execute_values(c, "INSERT INTO reviews (word_id) VALUES %s",
                       [(wid,) for wid in word_ids])

    conn.commit()
    conn.close()


def get_stats(hsk_level: str = None):
    conn = get_conn()
    c = conn.cursor()
    extra, params = _level_clause(hsk_level)

    c.execute(f"SELECT COUNT(*) FROM words w WHERE 1=1{extra}", params)
    total = c.fetchone()[0]

    now = datetime.now()
    c.execute(f"""
        SELECT COUNT(*) FROM reviews r
        JOIN words w ON w.id = r.word_id
        WHERE r.next_review <= %s{extra}
    """, (now, *params))
    due = min(c.fetchone()[0], DAILY_REVIEW_LIMIT)

    start_utc, end_utc = _today_utc_range()
    c.execute(f"""
        SELECT COUNT(*) FROM reviews r
        JOIN words w ON w.id = r.word_id
        WHERE r.last_review >= %s AND r.last_review < %s{extra}
    """, (start_utc, end_utc, *params))
    learned = c.fetchone()[0]

    conn.close()
    return {"total": total, "due": due, "learned": learned}
