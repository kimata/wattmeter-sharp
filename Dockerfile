FROM python:3.12.5-bookworm AS build

RUN --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install --no-install-recommends --assume-yes \
    clang \
    curl

ENV PYTHONDONTWRITEBYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen --no-hashes --format requirements-txt > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt


FROM python:3.12.5-slim-bookworm AS prod

ARG IMAGE_BUILD_DATE

ENV TZ=Asia/Tokyo
ENV IMAGE_BUILD_DATE=${IMAGE_BUILD_DATE}

COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

WORKDIR /opt/wattmeter-sharp

COPY . .

CMD ["./src/sharp_hems_logger.py"]
