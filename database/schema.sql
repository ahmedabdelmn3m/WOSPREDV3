-- ============================================================
-- WOSPREDV3 — Complete Database Schema
-- PostgreSQL 15+
-- Run: psql $DATABASE_URL -f schema.sql
-- ============================================================

-- ── Extensions ────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Users ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    username    VARCHAR(80) UNIQUE NOT NULL,
    email       VARCHAR(255) UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Presets ───────────────────────────────────────────────────
-- Stores saved army configurations per user.
CREATE TABLE IF NOT EXISTS presets (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID        REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    troop_count     INT         NOT NULL DEFAULT 500000,
    -- Formation fractions (sum = 1.0)
    form_infantry   FLOAT       NOT NULL DEFAULT 0.50,
    form_lancer     FLOAT       NOT NULL DEFAULT 0.20,
    form_marksman   FLOAT       NOT NULL DEFAULT 0.30,
    -- Infantry stats (%)
    inf_attack_pct      FLOAT NOT NULL DEFAULT 0,
    inf_defense_pct     FLOAT NOT NULL DEFAULT 0,
    inf_health_pct      FLOAT NOT NULL DEFAULT 0,
    inf_lethality_pct   FLOAT NOT NULL DEFAULT 0,
    -- Lancer stats (%)
    lan_attack_pct      FLOAT NOT NULL DEFAULT 0,
    lan_defense_pct     FLOAT NOT NULL DEFAULT 0,
    lan_health_pct      FLOAT NOT NULL DEFAULT 0,
    lan_lethality_pct   FLOAT NOT NULL DEFAULT 0,
    -- Marksman stats (%)
    mrk_attack_pct      FLOAT NOT NULL DEFAULT 0,
    mrk_defense_pct     FLOAT NOT NULL DEFAULT 0,
    mrk_health_pct      FLOAT NOT NULL DEFAULT 0,
    mrk_lethality_pct   FLOAT NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- ── Enemy Scouts ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS enemy_scouts (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID        REFERENCES users(id) ON DELETE SET NULL,
    label           VARCHAR(100),
    troop_count     INT         DEFAULT 500000,
    form_infantry   FLOAT       DEFAULT 0.50,
    form_lancer     FLOAT       DEFAULT 0.20,
    form_marksman   FLOAT       DEFAULT 0.30,
    inf_attack_pct      FLOAT DEFAULT 0,
    inf_defense_pct     FLOAT DEFAULT 0,
    inf_health_pct      FLOAT DEFAULT 0,
    inf_lethality_pct   FLOAT DEFAULT 0,
    lan_attack_pct      FLOAT DEFAULT 0,
    lan_defense_pct     FLOAT DEFAULT 0,
    lan_health_pct      FLOAT DEFAULT 0,
    lan_lethality_pct   FLOAT DEFAULT 0,
    mrk_attack_pct      FLOAT DEFAULT 0,
    mrk_defense_pct     FLOAT DEFAULT 0,
    mrk_health_pct      FLOAT DEFAULT 0,
    mrk_lethality_pct   FLOAT DEFAULT 0,
    ocr_source      VARCHAR(255),   -- filename if created via OCR
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Heroes ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS heroes (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    hero_id         VARCHAR(50) UNIQUE NOT NULL,   -- e.g. 'flint', 'mia', 'alonso'
    name            VARCHAR(100) NOT NULL,
    generation      INT         DEFAULT 1,
    specialty       VARCHAR(50),                   -- 'infantry', 'lancer', 'marksman', 'general'
    rarity          VARCHAR(20) DEFAULT 'epic',    -- 'rare', 'epic', 'legendary'
    verified        BOOLEAN     DEFAULT FALSE,
    confidence_pct  INT         DEFAULT 0,         -- 0–100
    source_notes    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Hero Skills ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hero_skills (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    hero_id         UUID        REFERENCES heroes(id) ON DELETE CASCADE,
    skill_number    INT         NOT NULL,          -- 1, 2, 3, 4
    name            VARCHAR(100),
    skill_type      VARCHAR(50),                   -- 'active', 'passive', 'aura'
    trigger         VARCHAR(100),                  -- 'on_round_start', 'on_kill', etc.
    target_type     VARCHAR(50),                   -- 'self', 'ally', 'enemy', 'all'
    cooldown        INT,                           -- rounds; NULL = no cooldown
    duration        INT,                           -- rounds; NULL = permanent
    description     TEXT,
    verified        BOOLEAN     DEFAULT FALSE,
    confidence_pct  INT         DEFAULT 0,
    source_notes    TEXT
);

-- ── Hero Scaling ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hero_scaling (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    hero_skill_id   UUID        REFERENCES hero_skills(id) ON DELETE CASCADE,
    stat_affected   VARCHAR(50) NOT NULL,          -- 'attack_pct', 'defense_pct', etc.
    effect_type     VARCHAR(50) NOT NULL,          -- 'buff', 'debuff', 'multiplier'
    base_value      FLOAT,                         -- NULL = unknown
    per_star_value  FLOAT,                         -- NULL = unknown
    per_widget_value FLOAT,                        -- NULL = unknown
    verified        BOOLEAN     DEFAULT FALSE,
    confidence_pct  INT         DEFAULT 0
);

-- ── Hero Widgets ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hero_widgets (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    hero_id         UUID        REFERENCES heroes(id) ON DELETE CASCADE,
    widget_level    INT         NOT NULL,          -- 1–5
    stat_affected   VARCHAR(50),
    value           FLOAT,
    verified        BOOLEAN     DEFAULT FALSE
);

-- ── Formations ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS formations (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    label           VARCHAR(50) NOT NULL,           -- e.g. '50/20/30'
    infantry_pct    INT         NOT NULL,
    lancer_pct      INT         NOT NULL,
    marksman_pct    INT         NOT NULL,
    notes           TEXT,
    UNIQUE(infantry_pct, lancer_pct, marksman_pct)
);

-- ── Battle Simulations ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS battle_simulations (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID        REFERENCES users(id) ON DELETE SET NULL,
    attacker_preset_id  UUID    REFERENCES presets(id) ON DELETE SET NULL,
    defender_scout_id   UUID    REFERENCES enemy_scouts(id) ON DELETE SET NULL,
    winner          VARCHAR(20) NOT NULL,           -- 'attacker', 'defender', 'draw'
    rounds_played   INT         NOT NULL,
    atk_initial     INT,
    atk_survivors   INT,
    atk_casualties  INT,
    def_initial     INT,
    def_survivors   INT,
    def_casualties  INT,
    engine_version  VARCHAR(10) DEFAULT 'v1',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Battle Rounds ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS battle_rounds (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID        REFERENCES battle_simulations(id) ON DELETE CASCADE,
    round_number    INT         NOT NULL,
    atk_damage      FLOAT,
    atk_defense     FLOAT,
    atk_penetration FLOAT,
    atk_casualties  INT,
    atk_remaining   INT,
    def_damage      FLOAT,
    def_defense     FLOAT,
    def_penetration FLOAT,
    def_casualties  INT,
    def_remaining   INT
);

-- ── Predictions ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id       UUID        REFERENCES battle_simulations(id) ON DELETE CASCADE,
    win_probability     FLOAT,
    predicted_winner    VARCHAR(20),
    confidence_label    VARCHAR(20),
    strength_inf_status VARCHAR(20),
    strength_lan_status VARCHAR(20),
    strength_mrk_status VARCHAR(20),
    bottleneck_troop    VARCHAR(20),
    bottleneck_stat     VARCHAR(30),
    summary             TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Battle Reports (submitted by users after actual battle) ───
CREATE TABLE IF NOT EXISTS battle_reports (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id   UUID        REFERENCES battle_simulations(id) ON DELETE SET NULL,
    actual_winner   VARCHAR(20) NOT NULL,
    actual_rounds   INT,
    notes           TEXT,
    submitted_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── Feedback Logs ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feedback_logs (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id       UUID        REFERENCES predictions(id) ON DELETE SET NULL,
    predicted_winner    VARCHAR(20),
    actual_winner       VARCHAR(20),
    correct             BOOLEAN,
    notes               TEXT,
    submitted_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── Combat Equations ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS combat_equations (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100) NOT NULL,
    formula         TEXT        NOT NULL,
    description     TEXT,
    verified        BOOLEAN     DEFAULT FALSE,
    confidence_pct  INT         DEFAULT 0,
    source          VARCHAR(255),
    patch_version   VARCHAR(20),
    added_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── OCR Results ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ocr_results (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename        VARCHAR(255),
    raw_text        TEXT,
    parsed_json     JSONB,
    confidence_pct  INT,
    manually_corrected BOOLEAN  DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Knowledge Sources ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       VARCHAR(255) NOT NULL,
    url         VARCHAR(500),
    source_type VARCHAR(50),  -- 'official', 'community', 'patch_note', 'screenshot'
    notes       TEXT,
    added_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── Patch Notes ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patch_notes (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    version         VARCHAR(20) NOT NULL,
    release_date    DATE,
    summary         TEXT,
    affects_combat  BOOLEAN     DEFAULT FALSE,
    full_text       TEXT,
    source_id       UUID        REFERENCES knowledge_sources(id) ON DELETE SET NULL,
    added_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── Seed: verified combat equations ───────────────────────────
INSERT INTO combat_equations (name, formula, description, verified, confidence_pct, source)
VALUES
  (
    'Damage Formula',
    'damage = (attack × (1 + Σ attack_stats) × lethality × (1 + Σ lethality_stats)) / 100',
    'Damage power for one troop type. Divided by 100 to keep numbers manageable.',
    TRUE, 100,
    'WOS community research + screenshot confirmation'
  ),
  (
    'Defense Formula',
    'defense = (defense × (1 + Σ defense_stats) × health × (1 + Σ health_stats)) / 100',
    'Defense power for one troop type. Mirrors damage formula structure.',
    TRUE, 100,
    'WOS community research + screenshot confirmation'
  )
ON CONFLICT DO NOTHING;

-- ============================================================
-- WOS Battle Predictor MVP calibration tables
-- These tables intentionally store JSONB snapshots so future
-- formula calibration can replay old predictions exactly.
-- ============================================================

CREATE TABLE IF NOT EXISTS player_presets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    name            VARCHAR(100) NOT NULL,
    preset_type     VARCHAR(20) NOT NULL DEFAULT 'own',
    scout_stats     JSONB NOT NULL,
    formation       JSONB NOT NULL,
    troop_count     INT NOT NULL DEFAULT 500000,
    heroes          JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scout_uploads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    side            VARCHAR(20),
    filename        VARCHAR(255),
    content_type    VARCHAR(100),
    storage_ref     VARCHAR(500),
    raw_text        TEXT,
    parsed_stats    JSONB,
    ocr_status      VARCHAR(50) DEFAULT 'pending_provider',
    manually_corrected BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hero_definitions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hero_id         VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(100) NOT NULL,
    generation      INT NOT NULL,
    specialty       VARCHAR(50),
    max_stars       INT DEFAULT 5,
    widget_supported BOOLEAN DEFAULT TRUE,
    verified        BOOLEAN DEFAULT FALSE,
    status          VARCHAR(50) DEFAULT 'pending verification',
    skills          JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_notes    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prediction_runs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    own_stats           JSONB NOT NULL,
    enemy_stats         JSONB NOT NULL,
    own_formation       JSONB NOT NULL,
    enemy_formation     JSONB,
    own_heroes          JSONB NOT NULL DEFAULT '[]'::jsonb,
    enemy_heroes        JSONB NOT NULL DEFAULT '[]'::jsonb,
    prediction_result   JSONB NOT NULL,
    confidence_level    VARCHAR(20),
    warnings            JSONB NOT NULL DEFAULT '[]'::jsonb,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS battle_logs (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID REFERENCES users(id) ON DELETE SET NULL,
    own_stats                   JSONB NOT NULL,
    enemy_stats                 JSONB NOT NULL,
    own_formation               JSONB NOT NULL,
    enemy_formation             JSONB,
    own_heroes                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    enemy_heroes                JSONB NOT NULL DEFAULT '[]'::jsonb,
    prediction_result           JSONB,
    actual_result               VARCHAR(50),
    notes                       TEXT,
    uploaded_report_image_ref   VARCHAR(255),
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS combat_constants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100) UNIQUE NOT NULL,
    value_json      JSONB NOT NULL,
    verified        BOOLEAN DEFAULT FALSE,
    status          VARCHAR(50) DEFAULT 'pending verification',
    note            TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Seed: standard formations ─────────────────────────────────
INSERT INTO formations (label, infantry_pct, lancer_pct, marksman_pct)
VALUES
  ('Balanced',          50, 20, 30),
  ('Infantry Heavy',    60, 10, 30),
  ('Lancer Boost',      40, 30, 30),
  ('Infantry Dominant', 70, 10, 20),
  ('Marksman Heavy',    40, 20, 40),
  ('Equal Thirds',      33, 34, 33),
  ('Marksman Dominant', 20, 10, 70)
ON CONFLICT DO NOTHING;
