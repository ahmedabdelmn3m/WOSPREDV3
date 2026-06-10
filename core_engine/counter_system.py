from .troop_stats import ArmyStats

COUNTER_BONUS = {
    ('infantry', 'lancer'):   0.10,   # VERIFIED
    ('lancer',   'marksman'): 0.10,   # ESTIMATED
    ('marksman', 'infantry'): 0.10,   # ESTIMATED
}

def calculate_cross_damage(attacker: ArmyStats, defender: ArmyStats) -> float:
    """
    Cross-type weighted damage with counter bonuses applied before formula.
    army_damage = ΣΣ (atk_weight_i × def_weight_j × damage(i→j))
    where damage(i→j) adds counter_bonus to attack_bonus before the formula.
    """
    total_damage = 0.0
    
    attacker_types = ['infantry', 'lancer', 'marksman']
    defender_types = ['infantry', 'lancer', 'marksman']
    
    for atk_type in attacker_types:
        atk_stats = getattr(attacker, atk_type)
        atk_weight = attacker.formation.get_weight(atk_type)
        if atk_weight <= 0: continue
        
        for def_type in defender_types:
            def_weight = defender.formation.get_weight(def_type)
            if def_weight <= 0: continue
            
            # Apply counter bonus to attack bonus
            counter_bonus = COUNTER_BONUS.get((atk_type, def_type), 0.0)
            
            # Formula: damage = (attack × (1 + Σ attack_bonus) × lethality × (1 + Σ lethality_bonus)) / 100
            # Modified attack bonus: modified_attack_bonus = attacker_type.attack_bonus + counter_bonus
            
            eff_atk_bonus = atk_stats.attack_bonus + counter_bonus
            
            damage_ij = (atk_stats.attack * (1 + eff_atk_bonus) * 
                         atk_stats.lethality * (1 + atk_stats.lethality_bonus)) / 100.0
            
            total_damage += atk_weight * def_weight * damage_ij
            
    return total_damage
