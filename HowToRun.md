# How to Run

## Prerequisites

- [Docker Desktop](https://docs.docker.com/desktop/) (includes Docker Compose)

## Run

```bash
docker compose up --build
```

Open **http://localhost:8080**

## Stop

```
Ctrl+C
```

or, to remove the container:

```bash
docker compose down
```

## Notes

- After changing any code, rebuild with `docker compose up --build` to see the changes (the image is not live-reloaded).
- Alternative without Docker: `./run.sh` (requires Python deps from `requirements.txt` installed locally).
