ARG PYTHON_VERSION=3.14

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7
FROM ubuntu as timestamp
RUN TZ=UTC date -u +"%Y-%m-%dT%H:%M:%SZ" > /build_date.txt


FROM python:${PYTHON_VERSION}-slim as base

LABEL org.opencontainers.image.authors="Kirill Shypachov @kshypachov"


# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1



WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.

#RUN --mount=type=cache,target=/root/.cache/pip \
#    --mount=type=bind,source=requirements.txt,target=requirements.txt \
#    python3 -m pip uninstall -y redis || true && \
#    python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the source code into the container.
COPY . .
RUN chmod +x /app/entrypoint.sh

RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Switch to the non-privileged user to run the application.
USER appuser
# Expose the port that the application listens on.
EXPOSE 8000
ARG FLASK_APP=app.py
COPY --from=timestamp /build_date.txt /app/build_date.txt


# Run the application.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD gunicorn app:app --bind ${HOST:-0.0.0.0}:${PORT:-5000} --workers ${WORKERS:-1} --log-level ${LOG_LEVEL:-info}
