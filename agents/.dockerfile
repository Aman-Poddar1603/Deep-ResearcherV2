# Use the official crawl4ai image as the base, which pre-configures
# Python, Playwright, Chromium, and crawl4ai dependencies.
FROM unclecode/crawl4ai:latest

# Install the uv package manager from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory inside the container
WORKDIR /app

# Copy dependency definition files first to leverage Docker layer caching
# (Assuming README.md is required by pyproject.toml for metadata)
COPY pyproject.toml README.md ./

# Install the rest of the project dependencies into the system environment using uv
RUN uv pip install --system .

# Copy the rest of the application codebase
COPY . .

# Expose the port that FastAPI will run on
EXPOSE 8000

# Start the server using uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
