# Guess The Prompt – Backend

A backend API for an online game where players take turns generating images using AI (Replicate – Stable Diffusion), and other players try to guess the prompt. Supports user registration, authentication, persistent profiles, scoring, and real-time gameplay via WebSockets.

---

## Features

- **User Accounts:** Registration, login, JWT authentication, and persistent player profiles (score, avatar, stats).
- **Room Management:** Create, join, and leave game rooms.
- **Player Management:** Assign roles, link game progress to users, track scores and stats.
- **Game Flow:** Prompt submission, guessing, turn management.
- **Image Generation:** Integration with Replicate (Stable Diffusion).
- **WebSockets:** Real-time updates for room events.
- **Leaderboards:** Top players by score.
- **PostgreSQL Database:** Persistent storage via SQLAlchemy/Alembic.
- **Dockerized:** Fast deployment and easy testing.
- **Test Coverage:** Async API tests included.

---

## Requirements

- Docker & Docker Compose
- Replicate API key (for image generation)
- Python 3.11+ (for local runs without Docker)

---

## Quick Start (with Docker)

1. **Clone the repository:**
    ```bash
    git clone https://github.com/Profy8712/guess-the-prompt-backend.git
    cd guess-the-prompt-backend
    ```

2. **Configure environment variables:**
    ```bash
    cp .env.example .env.docker
    # Edit .env.docker: set your REPLICATE_API_TOKEN, SECRET_KEY, etc.
    ```

3. **Build and run services:**
    ```bash
    docker compose up --build -d
    ```

4. **Apply database migrations:**
    ```bash
    docker compose exec backend alembic upgrade head
    ```

5. **Check API status:**
    - API: [http://localhost:8000](http://localhost:8000)
    - Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

6. **Run tests:**
    ```bash
    docker compose exec backend bash
    # Inside container:
    export DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/guess_the_prompt_test
    export REPLICATE_API_TOKEN=your-replicate-token
    pytest -v --asyncio-mode=auto
    ```

---

## Main Endpoints

### Accounts

- `POST   /api/v1/accounts/register`   – Register a new user
- `POST   /api/v1/accounts/login`      – Obtain JWT access token
- `GET    /api/v1/accounts/me`         – Get current user profile
- `GET    /api/v1/accounts/leaderboard`– Top 10 players by score

### Rooms & Gameplay

- `POST   /rooms`                     – Create a new game room
- `POST   /rooms/{room_id}/join`      – Join a room
- `POST   /rooms/{room_id}/leave`     – Leave a room
- `GET    /rooms/{room_id}`           – Get room info
- `POST   /rooms/{room_id}/prompt`    – Submit a prompt (image generation)
- `POST   /rooms/{room_id}/guess`     – Submit a guess
- `POST   /rooms/{room_id}/next`      – Next turn
- `GET    /health`                    – Health check

> See full, interactive API docs at `/docs`.

---

## Folder Structure

.
├── app/
│ ├── main.py
│ ├── ws_manager.py
│ ├── replicate_client.py
│ ├── rooms.py
│ ├── db/
│ │ ├── database.py
│ │ └── models_db.py
│ └── accounts/
│ ├── routes.py
│ ├── schemas.py
│ ├── services.py
│ └── auth.py
├── tests/
│ ├── conftest.py
│ └── test_accounts/
│ ├── test_auth.py
│ └── test_profile.py
├── alembic/
│ └── versions/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
└── .env.docker

