FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

# Вариант 1: Зеркало Tsinghua (рекомендую)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Вариант 2: Зеркало Aliyun (если Tsinghua не сработает)
# RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

# Вариант 3: Российское зеркало depkit (если предыдущие не подойдут)
# RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.depkit.ru/simple

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
