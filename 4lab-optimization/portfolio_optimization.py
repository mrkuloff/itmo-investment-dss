import pulp  # pulp==3.3.2

# ---------- Исходные данные ----------
projects = ['P1', 'P2', 'P3', 'P4', 'P5']
C      = {'P1':120, 'P2':80,  'P3':150, 'P4':100, 'P5':90}
E_NPV  = {'P1':48.75, 'P2':23.125, 'P3':70.0, 'P4':34.125, 'P5':60.0}
NPV_s1 = {'P1':35.0,  'P2':12.5,   'P3':28.0, 'P4':28.0,   'P5':36.0}
G      = {'P1':0.1836,'P2':0.1294, 'P3':0.2664,'P4':0.1673, 'P5':0.2533}
B, L = 300, 70

def solve(objective, K_max=None):
    prob = pulp.LpProblem("Portfolio", pulp.LpMaximize)
    x = pulp.LpVariable.dicts("x", projects, cat='Binary')

    # Целевая функция
    if objective == 'E_NPV':
        prob += pulp.lpSum(E_NPV[i] * x[i] for i in projects)
    else:  # AHP
        prob += pulp.lpSum(G[i] * x[i] for i in projects)

    # Ограничения
    prob += pulp.lpSum(C[i] * x[i] for i in projects) <= B
    prob += pulp.lpSum(NPV_s1[i] * x[i] for i in projects) >= L
    if K_max is not None:
        prob += pulp.lpSum(x[i] for i in projects) <= K_max

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    selected = [i for i in projects if x[i].varValue == 1]
    val  = pulp.value(prob.objective)
    cost = sum(C[i] for i in selected)
    risk = sum(NPV_s1[i] for i in selected)
    return selected, val, cost, risk

# ---------- Расчёт четырёх сценариев ----------
for obj in ['E_NPV', 'AHP']:
    for K in [None, 2]:
        sel, val, cost, risk = solve(obj, K)
        print(f"Цель: {obj:5s} | K_max={str(K):4s} | Портфель: {sel}")
        print(f"  Значение: {val:.4f} | Затраты: {cost} | NPV(s1): {risk}\n")
