FROM python:3.11-slim

WORKDIR /app

# Set Python execution environment flags to optimize runtime logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy package requirements list
COPY requirements.txt /app/

# Install python dependencies without storing cache directories (keeps image small)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code files
COPY . /app/

EXPOSE 8000

# Start Uvicorn ASGI server hosting the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
