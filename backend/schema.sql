CREATE TABLE IF NOT EXISTS riding_rings (
 code text PRIMARY KEY,title text NOT NULL,surface text NOT NULL CHECK (surface IN ('sand','fiber')),
 max_riders int NOT NULL CHECK (max_riders>0), sheltered boolean NOT NULL
);
CREATE TABLE IF NOT EXISTS ring_walks (
 code text PRIMARY KEY,ring text NOT NULL REFERENCES riding_rings(code),observed date NOT NULL,
 puddle int NOT NULL CHECK(puddle BETWEEN 0 AND 100),rut int NOT NULL CHECK(rut BETWEEN 0 AND 100),
 moisture int NOT NULL CHECK(moisture BETWEEN 0 AND 100),barrier text NOT NULL CHECK(barrier IN ('clear','review','closed')),
 outcome boolean,source text NOT NULL
);
CREATE TABLE IF NOT EXISTS ring_calls (
 ring text PRIMARY KEY REFERENCES riding_rings(code), walk text NOT NULL REFERENCES ring_walks(code),
 feature text NOT NULL, cutoff real NOT NULL, probability real NOT NULL CHECK(probability BETWEEN 0 AND 1),
 close_recommended boolean NOT NULL, calibration jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS lessons (
 code text PRIMARY KEY,group_name text NOT NULL,riders int NOT NULL CHECK(riders>0), starts_at timestamptz NOT NULL,
 ring text NOT NULL REFERENCES riding_rings(code), state text NOT NULL CHECK(state IN ('scheduled','moved','paused'))
);
CREATE TABLE IF NOT EXISTS lesson_moves (
 lesson text PRIMARY KEY REFERENCES lessons(code), origin text NOT NULL REFERENCES riding_rings(code),
 target text NOT NULL REFERENCES riding_rings(code),walk text NOT NULL REFERENCES ring_walks(code),
 reasoning text NOT NULL, reviewed_by text NOT NULL, changed_on timestamptz NOT NULL DEFAULT now(),
 CHECK (origin<>target)
);
