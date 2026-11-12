"""
Рекомендательный модуль СППР выбора инвестиционного проекта.
Формирует рекомендации по проектам и портфелям на основе
AHP-рейтинга, сценарного анализа, оптимизации и прогноза Prophet.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# ---------- Входные данные (из разделов 2–6) ----------
PROJECTS = {
    'P1': {'cost': 120, 'E_NPV': 48.75, 'NPV_s1': 35.0, 'AHP': 0.1836},
    'P2': {'cost': 80,  'E_NPV': 23.125,'NPV_s1': 12.5, 'AHP': 0.1294},
    'P3': {'cost': 150, 'E_NPV': 70.0,  'NPV_s1': 28.0, 'AHP': 0.2664},
    'P4': {'cost': 100, 'E_NPV': 34.125,'NPV_s1': 28.0, 'AHP': 0.1673},
    'P5': {'cost': 90,  'E_NPV': 60.0,  'NPV_s1': 36.0, 'AHP': 0.2533},
}

BUDGET = 300
RISK_THRESHOLD = 70          # L
AHP_THRESHOLD = 0.25
RISK_COMPAT_THRESHOLD = 30   # NPV(s1) >= 30

# Прогноз Prophet (из раздела 6)
FORECAST = {
    'avg_forecast': 102.02,
    'avg_lower': 99.45,
    'mape': 3.9,
}

# ---------- Структуры данных ----------
@dataclass
class ProjectRecommendation:
    project: str
    status: str                      # Core / Filler / ExcludedByRisk / ExcludedByBudget
    decision: str                    # "включить" / "не включать"
    reason: str                      # объяснение

@dataclass
class PortfolioRecommendation:
    members: Tuple[str, ...]
    expected_npv: float
    npv_s1: float
    cost: int
    forecast_lower: float
    safety_margin: float             # forecast_lower - L
    decision: str
    reason: str

@dataclass
class RecommendationReport:
    projects: List[ProjectRecommendation] = field(default_factory=list)
    portfolios: List[PortfolioRecommendation] = field(default_factory=list)

# ---------- Правила классификации проектов ----------
def classify_project(pid: str, data: dict) -> ProjectRecommendation:
    p = data[pid]
    is_priority = p['AHP'] >= AHP_THRESHOLD
    is_risk_ok = p['NPV_s1'] >= RISK_COMPAT_THRESHOLD

    if is_priority and is_risk_ok:
        return ProjectRecommendation(
            project=pid, status='Core', decision='включить',
            reason=(f"AHP = {p['AHP']:.4f} ≥ {AHP_THRESHOLD} и "
                    f"NPV(s1) = {p['NPV_s1']} ≥ {RISK_COMPAT_THRESHOLD} → ядро портфеля")
        )
    if is_priority and not is_risk_ok:
        return ProjectRecommendation(
            project=pid, status='ExcludedByRisk', decision='не включать',
            reason=(f"AHP = {p['AHP']:.4f} ≥ {AHP_THRESHOLD}, но "
                    f"NPV(s1) = {p['NPV_s1']} < {RISK_COMPAT_THRESHOLD} → исключён по риску")
        )
    # не приоритетный, но может стать Filler — решается на уровне портфеля
    return ProjectRecommendation(
        project=pid, status='Candidate', decision='рассмотреть',
        reason=(f"AHP = {p['AHP']:.4f} < {AHP_THRESHOLD}, "
                f"NPV(s1) = {p['NPV_s1']} → кандидат в заполнители")
    )

# ---------- Оценка портфеля ----------
def evaluate_portfolio(members: Tuple[str, ...], data: dict) -> PortfolioRecommendation:
    cost = sum(data[p]['cost'] for p in members)
    e_npv = sum(data[p]['E_NPV'] for p in members)
    npv_s1 = sum(data[p]['NPV_s1'] for p in members)
    forecast_lower = FORECAST['avg_lower']
    safety = forecast_lower - RISK_THRESHOLD

    ok_budget = cost <= BUDGET
    ok_risk = npv_s1 >= RISK_THRESHOLD
    ok_forecast = forecast_lower >= RISK_THRESHOLD

    if ok_budget and ok_risk and ok_forecast:
        decision = 'рекомендуется'
        reason = (f"Затраты {cost} ≤ {BUDGET}, NPV(s1) = {npv_s1} ≥ {RISK_THRESHOLD}, "
                  f"нижняя граница прогноза {forecast_lower:.2f} ≥ {RISK_THRESHOLD} "
                  f"(запас {safety:.2f})")
    elif not ok_budget:
        decision = 'не рекомендуется'
        reason = f"Затраты {cost} > {BUDGET} (превышение бюджета)"
    elif not ok_risk:
        decision = 'не рекомендуется'
        reason = f"NPV(s1) = {npv_s1} < {RISK_THRESHOLD} (нарушен риск-порог)"
    else:
        decision = 'не рекомендуется'
        reason = f"Нижняя граница прогноза {forecast_lower:.2f} < {RISK_THRESHOLD}"

    return PortfolioRecommendation(
        members=members, expected_npv=e_npv, npv_s1=npv_s1, cost=cost,
        forecast_lower=forecast_lower, safety_margin=safety,
        decision=decision, reason=reason
    )

# ---------- Подбор заполнителей (Filler) ----------
def select_fillers(core: List[str], data: dict, budget: int, risk_l: int) -> List[str]:
    chosen = set(core)
    used = sum(data[p]['cost'] for p in chosen)
    npv_s1 = sum(data[p]['NPV_s1'] for p in chosen)
    candidates = sorted(
        (p for p in data if p not in chosen),
        key=lambda x: -data[x]['E_NPV']
    )
    fillers = []
    for p in candidates:
        if used + data[p]['cost'] <= budget and npv_s1 + data[p]['NPV_s1'] >= risk_l:
            chosen.add(p); fillers.append(p)
            used += data[p]['cost']; npv_s1 += data[p]['NPV_s1']
    return fillers

# ---------- Главная функция ----------
def generate_recommendations(data: dict = PROJECTS) -> RecommendationReport:
    report = RecommendationReport()

    # 1. Классификация проектов
    for pid in data:
        report.projects.append(classify_project(pid, data))

    # 2. Ядро и заполнители
    core = [r.project for r in report.projects if r.status == 'Core']
    fillers = select_fillers(core, data, BUDGET, RISK_THRESHOLD)

    # Обновляем статусы заполнителей и исключённых по бюджету
    for r in report.projects:
        if r.project in fillers:
            r.status = 'Filler'
            r.decision = 'включить'
            r.reason = (f"Добавлен как заполнитель: E[NPV] = {data[r.project]['E_NPV']}, "
                        f"не нарушает бюджет и риск-порог")
        elif r.status == 'Candidate':
            r.status = 'ExcludedByBudget'
            r.decision = 'не включать'
            r.reason = (f"Не проходит по бюджету: добавление к ядру и заполнителям "
                        f"превышает {BUDGET}")

    # 3. Оценка портфелей
    p_full = tuple(sorted(core + fillers))
    report.portfolios.append(evaluate_portfolio(p_full, data))

    # Альтернатива при K_max = 2: ядро + лучший заполнитель
    if len(core) == 1:
        best_filler = max(
            (p for p in data if p not in core),
            key=lambda x: data[x]['E_NPV']
        )
        p_k2 = tuple(sorted(core + [best_filler]))
        if p_k2 != p_full:
            report.portfolios.append(evaluate_portfolio(p_k2, data))

    return report

# ---------- Вывод отчёта ----------
def print_report(report: RecommendationReport):
    print("=" * 70)
    print("РЕКОМЕНДАТЕЛЬНЫЙ МОДУЛЬ СППР")
    print("=" * 70)

    print("\n--- Рекомендации по проектам ---")
    for r in report.projects:
        print(f"\n[{r.project}] {r.status} → {r.decision.upper()}")
        print(f"    Причина: {r.reason}")

    print("\n--- Рекомендации по портфелям ---")
    for i, p in enumerate(report.portfolios, 1):
        print(f"\nВариант {i}: {{{', '.join(p.members)}}}")
        print(f"    Затраты: {p.cost} / {BUDGET}")
        print(f"    Ожидаемый NPV: {p.expected_npv:.2f}")
        print(f"    NPV(s1): {p.npv_s1:.2f} / порог {RISK_THRESHOLD}")
        print(f"    Нижняя граница прогноза: {p.forecast_lower:.2f} "
              f"(запас {p.safety_margin:.2f})")
        print(f"    Решение: {p.decision.upper()}")
        print(f"    Обоснование: {p.reason}")

    print("\n" + "=" * 70)
    best = max(
        (p for p in report.portfolios if p.decision == 'рекомендуется'),
        key=lambda x: x.expected_npv,
        default=None
    )
    if best:
        print(f"ИТОГОВАЯ РЕКОМЕНДАЦИЯ: портфель {{{', '.join(best.members)}}} "
              f"(E[NPV] = {best.expected_npv:.2f}, запас {best.safety_margin:.2f})")
    print("=" * 70)


if __name__ == '__main__':
    report = generate_recommendations()
    print_report(report)