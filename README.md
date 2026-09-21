# Nginx Log Explorer

Local web application for uploading and exploring Nginx access logs. Log import and analysis are not implemented yet.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 22 or newer
- npm
- Make (optional, for root convenience commands)

## Install dependencies

```sh
cd backend
uv sync --frozen

cd ../frontend
npm ci
```

## Development

Start the backend from the repository root:

```sh
cd backend
uv run uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```sh
cd frontend
npm run dev
```

Both development servers listen on the local interface by default.

## Tests and lint

From the repository root:

```sh
make test-backend
make test-frontend
make test
make lint
```

Build the frontend directly with:

```sh
cd frontend
npm run build
```
