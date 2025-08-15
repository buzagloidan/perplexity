# Use Python 3.12 with minimal setup
FROM python:3.12

# Install Chrome dependencies and download Chrome
RUN apt-get update && apt-get install -y \
    wget \
    xvfb \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN python3.12 -m pip install --upgrade pip setuptools
RUN python3.12 -m pip install -r requirements.txt

# Copy application code
COPY . .

# Set environment variables for Chrome
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV DISPLAY=:99

# Run the application
CMD ["xvfb-run", "-a", "--server-args=-screen 0 1024x768x24", "python", "perplexity_railway.py"]