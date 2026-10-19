FROM python:3.12-alpine AS builder

RUN apk add build-base libffi-dev libpq-dev mariadb-connector-c-dev curl \
  && adduser -h /home/tg -D -u 1000 tg \
  && install -d -o tg -g tg /home/tg/app
USER tg
WORKDIR /home/tg/app
ENV PATH=/home/tg/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
COPY --chown=tg:tg uv.lock pyproject.toml /home/tg/app/
RUN sh <(curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs) -y \
  && curl -LsSf https://astral.sh/uv/install.sh | sh \
  && uv sync --frozen --no-dev

FROM python:3.12-alpine
RUN apk add libpq mariadb-connector-c ffmpeg libogg opus lame \
  && adduser -h /home/tg -D -u 1000 tg \
  && install -d -o tg -g tg /home/tg/app
USER tg
WORKDIR /home/tg/app
ENV PATH=/home/tg/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
COPY --from=builder --chown=tg:tg /home/tg/app /home/tg/app
COPY --chown=tg:tg . /home/tg/app/
RUN .venv/bin/pybabel compile --domain=tour_guide_bot --directory=tour_guide_bot/locales
ENTRYPOINT [ "/home/tg/app/docker_entrypoint.sh" ]
