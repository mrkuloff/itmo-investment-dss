# ---------- 1. Схема (аналог онтологии) ----------
CLASSES = {
    'Project':      {'desc': 'Инвестиционный проект'},
    'Portfolio':    {'desc': 'Портфель проектов'},
    'Criterion':    {'desc': 'Критерий оценки'},
    'Scenario':     {'desc': 'Сценарий экономической ситуации'},
}

OBJECT_PROPS = {
    'includedIn':  {'domain': 'Project', 'range': 'Portfolio'},
    'evaluatedBy': {'domain': 'Project', 'range': 'Criterion'},
}

DATA_PROPS = {
    'hasCost':   {'domain': 'Project', 'range': 'float'},
    'hasE_NPV':  {'domain': 'Project', 'range': 'float'},
    'hasNPV_s1': {'domain': 'Project', 'range': 'float'},
    'hasAHP':    {'domain': 'Project', 'range': 'float'},
    'hasBudget': {'domain': 'Portfolio', 'range': 'float'},
    'hasRiskThreshold': {'domain': 'Portfolio', 'range': 'float'},
}

# ---------- 2. Факты (рабочая память) ----------
facts = {
    # проекты
    ('P1', 'cost',   120), ('P1', 'E_NPV',  48.75), ('P1', 'NPV_s1', 35.0), ('P1', 'AHP', 0.1836),
    ('P2', 'cost',    80), ('P2', 'E_NPV',  23.125),('P2', 'NPV_s1', 12.5), ('P2', 'AHP', 0.1294),
    ('P3', 'cost',   150), ('P3', 'E_NPV',  70.0),  ('P3', 'NPV_s1', 28.0), ('P3', 'AHP', 0.2664),
    ('P4', 'cost',   100), ('P4', 'E_NPV',  34.125),('P4', 'NPV_s1', 28.0), ('P4', 'AHP', 0.1673),
    ('P5', 'cost',    90), ('P5', 'E_NPV',  60.0),  ('P5', 'NPV_s1', 36.0), ('P5', 'AHP', 0.2533),
    # параметры ЛПР
    ('Portfolio', 'budget',        300),
    ('Portfolio', 'risk_threshold', 70),
}

# ---------- 3. Продукционные правила ----------
def r_priority(f):
    """R1: AHP >= 0.25 -> PrioritySet"""
    for s, p, v in list(f):
        if p == 'AHP' and v >= 0.25:
            yield (s, 'member', 'PrioritySet')

def r_risk_ok(f):
    """R2: NPV_s1 >= 30 -> RiskCompatible"""
    for s, p, v in list(f):
        if p == 'NPV_s1' and v >= 30:
            yield (s, 'member', 'RiskCompatible')

def r_core(f):
    """R3: PrioritySet AND RiskCompatible -> Core"""
    prio = {s for s, p, v in f if p == 'member' and v == 'PrioritySet'}
    rc   = {s for s, p, v in f if p == 'member' and v == 'RiskCompatible'}
    for s in prio & rc:
        yield (s, 'status', 'Core')

def r_excluded(f):
    """R4: PrioritySet AND NOT RiskCompatible -> ExcludedByRisk"""
    prio = {s for s, p, v in f if p == 'member' and v == 'PrioritySet'}
    rc   = {s for s, p, v in f if p == 'member' and v == 'RiskCompatible'}
    for s in prio - rc:
        yield (s, 'status', 'ExcludedByRisk')

def r_filler(f):
    """R5: добавить проекты по убыванию E_NPV, если бюджет и риск позволяют"""
    core = {s for s, p, v in f if p == 'status' and v == 'Core'}
    B = next(v for s, p, v in f if p == 'budget')
    L = next(v for s, p, v in f if p == 'risk_threshold')
    cost = {s: v for s, p, v in f if p == 'cost'}
    e    = {s: v for s, p, v in f if p == 'E_NPV'}
    nps1 = {s: v for s, p, v in f if p == 'NPV_s1'}
    chosen = set(core)
    used   = sum(cost[p] for p in chosen)
    for p in sorted((p for p in cost if p not in chosen), key=lambda x: -e[x]):
        if used + cost[p] <= B and sum(nps1[c] for c in chosen | {p}) >= L:
            chosen.add(p)
            used += cost[p]
            yield (p, 'status', 'Filler')

def r_final(f):
    """R6: портфель = Core + Filler"""
    chosen = {s for s, p, v in f if p == 'status' and v in ('Core', 'Filler')}
    if chosen:
        yield ('Portfolio1', 'members', tuple(sorted(chosen)))

def r_verify(f):
    """R7: проверить бюджет и риск-порог -> Recommended"""
    mem = next((v for s, p, v in f if p == 'members'), None)
    if not mem:
        return
    B = next(v for s, p, v in f if p == 'budget')
    L = next(v for s, p, v in f if p == 'risk_threshold')
    cost = {s: v for s, p, v in f if p == 'cost'}
    nps1 = {s: v for s, p, v in f if p == 'NPV_s1'}
    c = sum(cost[p] for p in mem)
    n = sum(nps1[p] for p in mem)
    if c <= B and n >= L:
        yield ('Portfolio1', 'status', 'Recommended')

def r_explain(f):
    """R8: объяснение по каждому проекту вне портфеля"""
    mem = next((v for s, p, v in f if p == 'members'), None)
    if not mem:
        return
    for s, p, v in list(f):
        if p == 'status' and v == 'ExcludedByRisk':
            yield (s, 'explanation', 'risk: NPV_s1 below risk-compatible level')
    # P4 и подобные — исключены бюджетом
    cost = {s: v for s, p, v in f if p == 'cost'}
    B = next(v for s, p, v in f if p == 'budget')
    for s in cost:
        if s not in mem and not any(ss == s and pp == 'status' for ss, pp, _ in f):
            yield (s, 'explanation', f'budget: adding would exceed B={B}')

# ---------- 4. Движок прямого вывода ----------
RULES = [r_priority, r_risk_ok, r_core, r_excluded,
         r_filler, r_final, r_verify, r_explain]

def infer(facts):
    trace = []
    changed = True
    step = 0
    while changed:
        changed = False
        for rule in RULES:
            for new in rule(facts):
                if new not in facts:
                    facts.add(new)
                    trace.append((step, rule.__name__, new))
                    changed = True
        step += 1
    return facts, trace

facts, trace = infer(facts)

# ---------- 5. Вывод ----------
print("=== Трассировка вывода ===")
for step, rule, fact in trace:
    print(f"  шаг {step} | {rule:12s} -> {fact}")

print("\n=== Итоговые утверждения ===")
for s, p, v in sorted(facts):
    if p in ('member', 'status', 'members', 'explanation'):
        print(f"  {s:12s} {p:12s} {v}")
