# Stage 1: Builder (Compile and install dependencies in an isolated prefix)
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime (Clean, minimal image running as a non-root user)
FROM python:3.11-slim
WORKDIR /app

# Create a non-privileged user so the container does not run as root
RUN useradd --create-home appuser

# Copy only the installed packages from the builder stage
COPY --from=builder /install /usr/local

# Copy the modular application package
COPY app/ ./app/

# Switch to the non-root user and expose the FastAPI port
USER appuser
EXPOSE 8000

# Bind to 0.0.0.0 so external container networking can reach the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]