FROM python:3.12-slim

WORKDIR /app

COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "\
import pathlib, re; \
base = pathlib.Path('/usr/local/lib/python3.12/site-packages/streamlit_cookies_manager'); \
enc = base / 'encrypted_cookie_manager.py'; \
enc.write_text(enc.read_text().replace('@st.cache\n', '@st.cache_data\n')); \
cm = base / 'cookie_manager.py'; \
t = cm.read_text(); \
t = t.replace('if self._cookies.get(key) != value:', 'if self._cookies.get(self._prefix + key) != value:'); \
t = t.replace('if key in self._cookies:', 'if self._prefix + key in self._cookies:'); \
cm.write_text(t)"

COPY dashboard/ .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
