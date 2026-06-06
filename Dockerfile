FROM python:3.12-slim

WORKDIR /app

# Install runtime deps separately so they get cached across code-only changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install the package itself (registers the `camforce` entry point).
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY vendors/ ./vendors/
RUN pip install --no-cache-dir .

ENTRYPOINT ["camforce"]
CMD ["--help"]
