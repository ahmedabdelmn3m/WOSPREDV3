-- HEROES
CREATE TABLE heroes (
    id UUID PRIMARY KEY,
    name TEXT,
    generation INT,
    role TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE hero_stats (
    id UUID PRIMARY KEY,
    hero_id UUID REFERENCES heroes(id),
    attack FLOAT,
    defense FLOAT,
    health FLOAT,
    lethality FLOAT,
    attack_stats_sum FLOAT,
    defense_stats_sum FLOAT,
    health_stats_sum FLOAT,
    lethality_stats_sum FLOAT,
    version INT,
    is_active BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- BATTLES
CREATE TABLE battles (
    id UUID PRIMARY KEY,
    battle_type TEXT,
    attacker_power FLOAT,
    defender_power FLOAT,
    predicted_winner TEXT,
    actual_winner TEXT,
    prediction_confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE battle_rounds (
    id UUID PRIMARY KEY,
    battle_id UUID REFERENCES battles(id),
    round_number INT,
    attacker_damage FLOAT,
    defender_damage FLOAT,
    attacker_remaining FLOAT,
    defender_remaining FLOAT
);

-- SKILLS
CREATE TABLE skills (
    id UUID PRIMARY KEY,
    hero_id UUID REFERENCES heroes(id),
    name TEXT,
    skill_type TEXT,
    trigger_event TEXT,
    cooldown INT,
    max_level INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE skill_effects (
    id UUID PRIMARY KEY,
    skill_id UUID REFERENCES skills(id),
    effect_type TEXT,
    target TEXT,
    value FLOAT,
    scaling_stat TEXT,
    duration INT,
    probability FLOAT
);
