FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ fonts-dejavu-core
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Chromium + its system libs (libnss3, libgbm1, …) for the HTML/Playwright
# natal-PDF renderer. Keep apt lists until after this step so install-deps
# can resolve packages; clean up only at the end.
RUN python -m playwright install --with-deps chromium \
    && python -m playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
