CREATE TABLE IF NOT EXISTS riding_rings (
 code text PRIMARY KEY,title text NOT NULL,surface text NOT NULL CHECK (surface IN ('sand','fiber')),
 max_riders int NOT NULL CHECK(max_riders>0), sheltered boolean NOT NULL
);
CREATE TABLE IF NOT EXISTS ring_walks (
 code text PRIMARY KEY,ring text NOT NULL REFERENCES riding_rings(code),observed date NOT NULL,
 puddle int NOT NULL CHECK(puddle BETWEEN 0 AND 100),rut int NOT NULL CHECK(rut BETWEEN 0 AND 100),
 moisture int NOT NULL CHECK(moisture BETWEEN 0 AND 100),barrier text NOT NULL CHECK(barrier IN ('clear','review','closed')),
 outcome boolean,source text NOT NULL
);
CREATE INDEX IF NOT EXISTS ring_walks_ring_day_code_idx
 ON ring_walks(ring, observed DESC, code DESC);
CREATE TABLE IF NOT EXISTS ring_calls (
 ring text PRIMARY KEY REFERENCES riding_rings(code), walk text NOT NULL REFERENCES ring_walks(code),
 feature text NOT NULL, cutoff real NOT NULL, probability real NOT NULL CHECK(probability BETWEEN 0 AND 1),
 close_recommended boolean NOT NULL, calibration jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS lessons (
 code text PRIMARY KEY,group_name text NOT NULL,riders int NOT NULL CHECK(riders>0), starts_at timestamptz NOT NULL,
 ring text NOT NULL REFERENCES riding_rings(code), state text NOT NULL CHECK(state IN ('scheduled','moved','paused','review','pending_review'))
);
-- Existing databases created before the review state was introduced need the
-- named check constraint replaced rather than relying on CREATE TABLE IF NOT
-- EXISTS, which is a no-op for an already-created table.
ALTER TABLE lessons DROP CONSTRAINT IF EXISTS lessons_state_check;
ALTER TABLE lessons ADD CONSTRAINT lessons_state_check
 CHECK (state IN ('scheduled','moved','paused','review','pending_review'));
CREATE TABLE IF NOT EXISTS lesson_moves (
 lesson text PRIMARY KEY REFERENCES lessons(code), origin text NOT NULL REFERENCES riding_rings(code),
 target text NOT NULL REFERENCES riding_rings(code),walk text NOT NULL REFERENCES ring_walks(code),
 reasoning text NOT NULL, reviewed_by text NOT NULL, changed_on timestamptz NOT NULL DEFAULT now(),
 CHECK (origin<>target)
);
ALTER TABLE lesson_moves ADD COLUMN IF NOT EXISTS target_walk text REFERENCES ring_walks(code);
ALTER TABLE lesson_moves ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'signed';
ALTER TABLE lesson_moves ADD COLUMN IF NOT EXISTS trigger_walk text REFERENCES ring_walks(code);
ALTER TABLE lesson_moves ADD COLUMN IF NOT EXISTS review_reason text;
ALTER TABLE lesson_moves DROP CONSTRAINT IF EXISTS lesson_moves_status_check;
ALTER TABLE lesson_moves ADD CONSTRAINT lesson_moves_status_check
 CHECK (status IN ('signed','review','pending_review','stale'));
CREATE INDEX IF NOT EXISTS lesson_moves_target_idx ON lesson_moves(target, status);
CREATE TABLE IF NOT EXISTS lesson_move_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 lesson text NOT NULL REFERENCES lessons(code),
 event text NOT NULL CHECK (event IN ('signed','review_opened','resigned','signoff_rejected')),
 move_status text NOT NULL CHECK (move_status IN ('signed','review','pending_review','stale')),
 origin text NOT NULL REFERENCES riding_rings(code),
 target text NOT NULL REFERENCES riding_rings(code),
 origin_walk text REFERENCES ring_walks(code),
 target_walk text REFERENCES ring_walks(code),
 trigger_walk text REFERENCES ring_walks(code),
 reasoning text,
 actor text NOT NULL,
 detail text,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS lesson_move_events_lesson_idx
 ON lesson_move_events(lesson, created_at, id);

-- Keep the review invariant even when a paper record is back-filled with raw
-- SQL or a fixture.  The API service additionally writes an audit event.
CREATE OR REPLACE FUNCTION lesson_move_late_seal_review()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.barrier <> 'closed' THEN
    RETURN NEW;
  END IF;

  UPDATE lesson_moves m
  SET status='review',
      trigger_walk=NEW.code,
      review_reason='迟到的封栏记录 ' || NEW.code || ' 已成为目标场最新依据'
  FROM lessons l
  WHERE m.lesson=l.code
    AND m.target=NEW.ring
    AND l.state <> 'paused'
    AND NEW.code = (
      SELECT w.code
      FROM ring_walks w
      WHERE w.ring=m.target
        AND w.outcome IS NULL
        AND w.observed=((l.starts_at AT TIME ZONE 'UTC') + INTERVAL '8 hours')::date
      ORDER BY NULLIF(regexp_replace(w.code, '[^0-9]', '', 'g'), '')::bigint DESC NULLS LAST,
               w.code DESC
      LIMIT 1
    );

  UPDATE lessons l
  SET state='review'
  FROM lesson_moves m
  WHERE m.lesson=l.code
    AND m.status='review'
    AND m.trigger_walk=NEW.code
    AND l.state='moved';

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS ring_walk_late_seal_review ON ring_walks;
CREATE TRIGGER ring_walk_late_seal_review
AFTER INSERT OR UPDATE OF barrier, code ON ring_walks
FOR EACH ROW EXECUTE FUNCTION lesson_move_late_seal_review();
