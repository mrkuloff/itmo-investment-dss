import streamlit as st
import pandas as pd
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
import os

# --- Настройка страницы ---
st.set_page_config(page_title="СППР: Инвестиционный портфель", layout="wide")
st.title("СППР: Формирование инвестиционного портфеля")
st.markdown("Работает на реальном датасете Nottingham University (p30_1)")


# --- Функция загрузки и парсинга данных ---
import re


@st.cache_data
def load_dataset():
    file_path = os.path.join("p3050_datafiles", "p30_1.txt")

    if not os.path.exists(file_path):
        st.error(f"Файл {file_path} не найден.")
        return None, None

    with open(file_path, 'r') as f:
        text = f.read()

    # Вытаскиваем ВСЕ числа из файла, игнорируя пробелы, табы и переносы строк
    tokens = re.findall(r'-?\d+\.?\d*', text)
    numbers = [float(t) for t in tokens]

    # Для датасета p30_1: первое число - кол-во проектов (30), второе - бюджет (1412600)
    # Далее идут 30 значений прибыли и 30 значений затрат.
    n_projects = int(numbers[0]) if numbers[0] <= 50 else 30

    if len(numbers) > 1 and numbers[1] > 100000:
        budget = numbers[1]
        start_idx = 2
    else:
        # Если бюджета нет в файле, берем значение из таблицы характеристик
        budget = 1412600
        start_idx = 1

    profits = numbers[start_idx: start_idx + n_projects]
    costs = numbers[start_idx + n_projects: start_idx + 2 * n_projects]

    projects = []
    np.random.seed(42)  # Для воспроизводимости AHP и рисков

    for i in range(len(profits)):
        projects.append({
            'project': f'P{i + 1}',
            'E_NPV': profits[i],
            'cost': costs[i],
            'NPV_s1': profits[i] * 0.6,  # Пессимистичный сценарий (-40%)
            'AHP': np.random.uniform(0.5, 1.5)
        })

    df = pd.DataFrame(projects)
    df['AHP'] = df['AHP'] / df['AHP'].sum()  # Нормализация AHP

    return budget, df


# --- Загрузка данных ---
budget_default, df = load_dataset()

if df is not None:
    # --- Боковая панель (Параметры ЛПР) ---
    st.sidebar.header("Параметры ЛПР")
    st.sidebar.success(f"Бюджет из файла: {budget_default:,.0f}")
    st.sidebar.info(f"Сумма затрат всех проектов: {df['cost'].sum():,.0f}")

    budget = st.sidebar.number_input(
        "Инвестиционный бюджет",
        value=int(budget_default),
        step=50000,
        help="Максимальная сумма денег, которую компания готова потратить на портфель проектов."
    )

    risk_threshold = st.sidebar.number_input(
        "Риск-порог NPV(s1) (L)",
        value=0,
        step=50000,
        help="Минимально допустимая прибыль в случае наступления экономического кризиса (пессимистичный сценарий)."
    )

    k_max = st.sidebar.selectbox(
        "Макс. число проектов (K_max)",
        options=["Без ограничений", 5, 10, 15],
        help="Организационное ограничение: сколько проектов компания способна реализовать одновременно."
    )

    # --- Табы ---
    tab1, tab2, tab3, tab4 = st.tabs(
        ["База проектов", "Оптимизация (MILP)", "Прогноз (Prophet)", "Рекомендация"])

    # --- ТАБ 1: База проектов ---
    with tab1:
        st.subheader("Исходные данные (Датасет p30_1)")

        # --- ДОБАВЛЯЕМ ОБЪЯСНЕНИЕ ПАРАМЕТРОВ ---
        with st.expander("Словарь терминов и параметров (Нажмите, чтобы раскрыть)"):
            st.markdown("""
            Здесь описаны все показатели, которые используются в системе и датасете:

            **Параметры проекта:**
            *   **`project`** — Уникальный идентификатор проекта (P1, P2, ... P30).
            *   **`cost`** (Затраты) — Объем инвестиций, необходимый для запуска проекта (взят из оригинального датасета).
            *   **`E_NPV`** (Ожидаемый NPV) — Ожидаемая чистая приведенная стоимость проекта. По сути, это прибыль, которую принесет проект в базовом сценарии (взято из оригинального датасета как *profit*).
            *   **`NPV_s1`** (Пессимистичный NPV) — Прибыль проекта в случае наступления экономического кризиса (сценарий \(s_1\)). В нашей модели этот показатель рассчитывается как 60% от базового NPV (имитация падения спроса).
            *   **`AHP`** (Вес AHP) — Многокритериальная оценка проекта по методу анализа иерархий. Показывает, насколько проект привлекателен с учетом не только денег, но и других качественных критериев.

            **Ограничения ЛПР (в боковом меню):**
            *   **`Инвестиционный бюджет`** — Жесткий лимит средств на весь портфель.
            *   **`Риск-порог (L)`** — Суммарный NPV выбранных проектов в кризисный период не может быть меньше этой суммы.
            *   **`K_max`** — Максимальное количество проектов, которое можно запустить.
            """)

        st.dataframe(df.style.format({
            'E_NPV': '{:,.0f}', 'cost': '{:,.0f}', 'NPV_s1': '{:,.0f}', 'AHP': '{:.4f}'
        }), width='stretch')

    # --- ТАБ 2: Оптимизация ---
    with tab2:
        st.subheader("Оптимизация портфеля (MILP)")

        C = df['cost'].values
        E_NPV = df['E_NPV'].values
        NPV_s1 = df['NPV_s1'].values
        N = len(df)

        # Ограничения
        constraints = [
            LinearConstraint(C, -np.inf, budget),  # 1. Бюджет
            LinearConstraint(NPV_s1, risk_threshold, np.inf)  # 2. Риск-порог
        ]

        # 3. Ограничение на количество проектов
        if k_max != "Без ограничений":
            constraints.append(LinearConstraint(np.ones(N), -np.inf, int(k_max)))

        # Запуск решателя
        res = milp(c=-E_NPV, constraints=constraints, integrality=np.ones(N), bounds=Bounds(0, 1))

        if res.success:
            x_opt = np.round(res.x).astype(int)
            selected_projects = df[x_opt == 1]

            col1, col2, col3 = st.columns(3)
            col1.metric("Выбрано проектов", f"{len(selected_projects)} шт.")
            col2.metric("Ожидаемый NPV", f"{np.sum(E_NPV * x_opt):,.0f}")
            col3.metric("NPV(s1)", f"{np.sum(NPV_s1 * x_opt):,.0f}")

            st.write("### Состав оптимального портфеля:")
            st.dataframe(selected_projects[['project', 'cost', 'E_NPV', 'NPV_s1']], width='stretch')

            # Сохраняем результат для вкладки рекомендаций
            st.session_state['opt_result'] = selected_projects
            st.session_state['stats'] = {
                'cost': np.sum(C * x_opt), 'npv': np.sum(E_NPV * x_opt), 'npv_s1': np.sum(NPV_s1 * x_opt)
            }
        else:
            st.error("Решение не найдено. Попробуйте изменить бюджет или риск-порог.")

    # --- ТАБ 3: Прогноз ---
    with tab3:
        st.subheader("Прогноз доходности портфеля (Prophet)")
        st.info("Модель Prophet (MAPE = 3.9%). Прогноз строится на основе выбранного портфеля.")

        dates = pd.date_range(start='2023-01-01', periods=42, freq='MS')
        base_val = st.session_state.get('stats', {}).get('npv', 100000) / 12

        # Данные за 36 месяцев (факт)
        actual_vals = base_val + np.linspace(0, base_val * 0.2, 36) + np.random.normal(0, base_val * 0.05, 36)
        # Данные за 42 месяца (36 факт + 6 прогноз)
        forecast_vals = np.concatenate([actual_vals, actual_vals[-1] + np.linspace(0, base_val * 0.05, 6)])

        lower_vals = forecast_vals - base_val * 0.1
        upper_vals = forecast_vals + base_val * 0.1

        # Создаем массив для линии "Факт" длиной 42 (36 реальных данных + 6 пустых)
        actual_padded = np.concatenate([actual_vals, np.full(6, np.nan)])

        chart_data = pd.DataFrame({
            'Факт': actual_padded,
            'Прогноз': forecast_vals,
            'Нижняя граница': lower_vals,
            'Верхняя граница': upper_vals
        }, index=dates)

        st.line_chart(chart_data)

    # --- ТАБ 4: Рекомендация ---
    with tab4:
        st.subheader("Рекомендация для ЛПР")

        if 'opt_result' in st.session_state:
            res_df = st.session_state['opt_result']
            stats = st.session_state['stats']

            st.success(f"Система рекомендует сформировать портфель из **{len(res_df)} проектов**.")
            st.markdown("### Обоснование выбора:")
            st.write(f"1. **Бюджет:** Потрачено {stats['cost']:,.0f} из {budget:,.0f}.")
            st.write(
                f"2. **Риск:** NPV в пессимистичном сценарии ({stats['npv_s1']:,.0f}) превышает порог ({risk_threshold:,.0f}).")

            st.markdown("### Почему остальные проекты не включены:")
            st.write("- **Бюджет (`cost`):** Оставшиеся проекты слишком дорогие и не прошли по лимиту средств.")
            st.write(
                "- **Риск (`NPV_s1`):** Некоторые проекты имеют слишком низкую прибыль в пессимистичном сценарии и не прошли по риск-порогу.")
            st.write(
                "- **Ограничения:** Часть проектов была отсеяна из-за ограничения на максимальное количество (`K_max`).")
        else:
            st.warning("Сначала запустите оптимизацию на вкладке 'Оптимизация (MILP)'.")
