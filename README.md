# Guess The Prompt – Backend

A backend API for an online game where players take turns generating images using AI (Replicate – Stable Diffusion), and other players try to guess the prompt.

## Features

- **Room Management:** Create, join, and leave game rooms.
- **Player Management:** Assign roles, track scores.
- **Game Flow:** Prompt submission, guessing, turn management.
- **Image Generation:** Integration with Replicate (Stable Diffusion).
- **WebSockets:** Real-time updates for room events.
- **PostgreSQL Database:** Persistent storage via SQLAlchemy/Alembic.
- **Dockerized:** Fast deployment and easy testing.
- **Test Coverage:** Async API tests included.

## Requirements

- Docker & Docker Compose
- Replicate API key (for image generation)
- Python 3.11 (if running locally without Docker)

## Quick Start (with Docker)

1. **Clone the repo:**
    ```bash
    git clone https://github.com/Profy8712/guess-the-prompt-backend.git
    cd guess-the-prompt-backend
    ```

2. **Configure environment:**

    Copy and edit the example env file:
    ```bash
    cp .env.example .env.docker
    # Edit .env.docker: set your REPLICATE_API_TOKEN
    ```

3. **Run services:**
    ```bash
    docker-compose up --build -d
    ```

4. **Apply migrations:**
    ```bash
    docker-compose exec backend alembic upgrade head
    ```

5. **Check that everything is running:**
    - API: http://localhost:8000
    - Swagger UI: http://localhost:8000/docs

6. **Run tests:**
    ```bash
    docker-compose exec backend bash
    # Inside container:
    export DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/guess_the_prompt_test
    export REPLICATE_API_TOKEN=your-replicate-token
    pytest -v --asyncio-mode=auto
    ```

## Main Endpoints

- `POST   /rooms`                 – Create a new game room
- `POST   /rooms/{room_id}/join`  – Join a room
- `POST   /rooms/{room_id}/leave` – Leave a room
- `GET    /rooms/{room_id}`       – Room info
- `POST   /rooms/{room_id}/prompt`– Submit a prompt (image generation)
- `POST   /rooms/{room_id}/guess` – Submit a guess
- `POST   /rooms/{room_id}/next`  – Next turn

See full interactive API docs at `/docs`.

## Folder Structure

.
├── app/
│ ├── main.py
│ ├── models.py
│ ├── rooms.py
│ ├── replicate_client.py
│ ├── ws_manager.py
│ └── db/
├── tests/
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
