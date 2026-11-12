import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
import networkx as nx
import matplotlib.pyplot as plt

# ---------- 1. Исходные данные ----------
projects = ['P1', 'P2', 'P3', 'P4', 'P5']
C = np.array([120, 80, 150, 100, 90])          # затраты
NPV_base = np.array([50, 25, 70, 35, 60])      # базовый NPV
# сценарные коэффициенты: строки - проекты, столбцы - сценарии s1,s2,s3
K = np.array([
    [0.70, 1.00, 1.20],   # P1
    [0.50, 1.00, 1.20],   # P2
    [0.40, 1.00, 1.60],   # P3
    [0.80, 1.00, 1.10],   # P4
    [0.60, 1.00, 1.40],   # P5
])
p = np.array([0.25, 0.50, 0.25])               # вероятности сценариев
B = 300                                        # бюджет
L = 70                                         # риск-ограничение: NPV в s1 >= 70

NPV_s = NPV_base[:, None] * K                  # матрица NPV (проекты x сценарии)
E_NPV = NPV_s @ p                              # ожидаемый NPV по проектам

print("NPV по сценариям (строки - проекты, столбцы - s1,s2,s3):")
print(np.round(NPV_s, 2))
print("Ожидаемый NPV:", np.round(E_NPV, 2))

# ---------- 2. Оптимизация портфеля (milp) ----------
# Переменные x1..x5, бинарные. Минимизируем -E[NPV] = c @ x
c = -E_NPV
constraints = [
    LinearConstraint(C, -np.inf, B),                 # бюджет
    LinearConstraint(NPV_s[:, 0], L, np.inf),        # риск: NPV(s1) >= L
]
res = milp(c=c, constraints=constraints,
           integrality=np.ones(5), bounds=Bounds(0, 1))
x_opt = np.round(res.x).astype(int)
print("\nОптимальный портфель (milp):", [projects[i] for i in range(5) if x_opt[i] == 1])
print("Ожидаемый NPV портфеля:", round(-res.fun, 2))
print("NPV в пессимистическом сценарии:", round(NPV_s[:, 0] @ x_opt, 2))
print("Затраты:", C @ x_opt)

# ---------- 3. Сравнение стратегий ----------
def evaluate(x):
    x = np.array(x)
    e = E_NPV @ x
    worst = NPV_s[:, 0] @ x
    cost = C @ x
    return e, worst, cost

strategies = {
    'S1: {P3,P5} (макс. E[NPV])': [0,0,1,0,1],
    'S2: {P1,P5} (оптимум с риском)': [1,0,0,0,1],
    'S3: {P1,P2,P4} (диверсификация)': [1,1,0,1,0],
}
print("\nСравнение стратегий:")
print(f"{'Стратегия':35s} {'E[NPV]':>8s} {'NPV(s1)':>8s} {'Затраты':>8s}")
for name, x in strategies.items():
    e, w, cst = evaluate(x)
    print(f"{name:35s} {e:8.2f} {w:8.2f} {cst:8d}")

# ---------- 4. Дерево решений для оптимального портфеля ----------
G = nx.DiGraph()
root = "Решение: портфель {P1,P5}"
G.add_node(root, type='decision')
scenario_names = ['Пессимистический (p=0.25)', 'Базовый (p=0.50)', 'Оптимистический (p=0.25)']
port_npv = NPV_s @ x_opt  # NPV портфеля по сценариям

for s, name in enumerate(scenario_names):
    chance = f"Сценарий: {name}"
    outcome = f"NPV = {port_npv[s]:.1f}"
    G.add_edge(root, chance, label=f"p={p[s]}")
    G.add_edge(chance, outcome)

pos = nx.spring_layout(G, seed=42)
plt.figure(figsize=(10, 6))
nx.draw(G, pos, with_labels=True, node_size=3000, node_color='lightblue',
        font_size=9, arrows=True)
nx.draw_networkx_edge_labels(G, pos,
    edge_labels={(u,v): d['label'] for u,v,d in G.edges(data=True) if 'label' in d},
    font_size=8)
plt.title("Дерево решений для портфеля {P1, P5}")
plt.tight_layout()
plt.show()
