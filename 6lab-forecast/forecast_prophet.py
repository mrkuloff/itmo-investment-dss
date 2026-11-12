import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

# ---------- 1. Синтетический временной ряд NPV портфеля {P1,P2,P5} ----------
np.random.seed(42)
months = pd.date_range('2026-01-01', periods=36, freq='MS')
trend = np.linspace(80, 125, 36)                      # постепенный рост
season = 8 * np.sin(2 * np.pi * np.arange(36) / 3)    # квартальная сезонность
noise = np.random.normal(0, 3, 36)
npv = trend + season + noise

df = pd.DataFrame({'ds': months, 'y': npv})

# ---------- 2. Train / test ----------
train = df.iloc[:-6]
test  = df.iloc[-6:]

# ---------- 3. Prophet ----------
model = Prophet(
    yearly_seasonality=False,
    weekly_seasonality=False,
    daily_seasonality=False,
    interval_width=0.80
)
model.add_seasonality(name='quarterly', period=91.25, fourier_order=5)
model.fit(train)

# ---------- 4. Прогноз на test + 6 месяцев вперёд ----------
future_test = model.make_future_dataframe(periods=6, freq='MS')
forecast = model.predict(future_test)

# ---------- 5. Метрики на test ----------
pred_test = forecast.set_index('ds').loc[test['ds'], 'yhat'].values
mae  = mean_absolute_error(test['y'], pred_test)
rmse = np.sqrt(mean_squared_error(test['y'], pred_test))
mape = np.mean(np.abs((test['y'].values - pred_test) / test['y'].values)) * 100

print(f"MAE  = {mae:.2f}")
print(f"RMSE = {rmse:.2f}")
print(f"MAPE = {mape:.1f}%")

# ---------- 6. Экспорт для BI ----------
actual = df.rename(columns={'ds': 'month', 'y': 'npv_actual'})
forecast_out = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].rename(
    columns={
        'ds': 'month',
        'yhat': 'npv_forecast',
        'yhat_lower': 'npv_lower',
        'yhat_upper': 'npv_upper'
    }
)

actual.to_csv('npv_actual.csv', index=False)
forecast_out.to_csv('npv_forecast.csv', index=False)
print("\nФайлы npv_actual.csv и npv_forecast.csv сохранены.")
