# Guess The Prompt – Backend

A backend API for an online multiplayer game where players take turns generating images using AI (Replicate – Stable Diffusion), and others try to guess the prompt. Features user registration, authentication, persistent profiles, leaderboards, scoring, real-time gameplay (WebSocket), flexible game settings, and more.

---

## Features

- **User Accounts:** Registration, JWT login, and persistent player stats (score, avatar, total games, etc).
- **Game Rooms:** Create, join, leave, kick players, change settings, start game, and manage rounds.
- **Gameplay:** Prompt submission, AI image generation, guessing, scores, and automated turn timers.
- **Leaderboards:** Top players by score.
- **Real-time:** WebSocket support for instant room updates.
- **Persistent Storage:** PostgreSQL + SQLAlchemy ORM + Alembic migrations.
- **Image Generation:** Replicate Stable Diffusion integration (see [replicate.com](https://replicate.com/)).
- **Dockerized:** Fast deployment for dev and prod.
- **Async Test Coverage:** Pytest-based async tests included.

---

## Requirements

- **Docker** & **Docker Compose** (recommended)
- Replicate API key (for image generation)
- Python 3.11+ (for local runs)

---

## Quick Start (Docker)

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

3. **Build and run the backend:**
    ```bash
    docker compose up --build -d
    ```

4. **Apply database migrations:**
    ```bash
    docker compose exec backend alembic upgrade head
    ```

5. **Check API:**
    - API root: [http://localhost:8000](http://localhost:8000)
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

## API Endpoints

### User Accounts

- `POST   /api/v1/accounts/register`    – Register new user
- `POST   /api/v1/accounts/login`       – Obtain JWT token
- `GET    /api/v1/accounts/me`          – Current user profile (auth required)
- `GET    /api/v1/accounts/leaderboard` – Top 10 by score
- `GET    /api/v1/accounts/stats/{username}` – Public stats for any player

### Rooms & Game Management

- `POST   /rooms`                      – Create a new game room
- `POST   /rooms/{room_id}/join`       – Join a room by nickname
- `POST   /rooms/{room_id}/leave`      – Leave room
- `POST   /rooms/{room_id}/kick_player` – Kick player (admin only)
- `POST   /rooms/{room_id}/change_settings` – Change game settings (admin)
- `POST   /rooms/{room_id}/start_game` – Start the game (admin)
- `GET    /rooms/{room_id}`            – Get current room state
- `POST   /rooms/{room_id}/prompt`     – Submit a prompt for image (by current prompter)
- `POST   /rooms/{room_id}/guess`      – Guess the prompt
- `GET    /health`                     – Health check

### WebSocket

- `ws://localhost:8000/ws/rooms/{room_id}?token=JWT`  
  Real-time room updates, timer events, chat, etc.

> See interactive docs at `/docs` for the full OpenAPI specification.

---

## Game Flow

1. **Create / Join Room:** Players join a lobby, can chat, and wait for others.
2. **Game Settings:** Admin (room creator) sets rounds, turn timer, and prompt length.
3. **Start Game:** Admin starts; server manages round/turn order, timers, and sends updates.
4. **Prompt Submission:** Current player submits a prompt (1–2 words) → AI image generated.
5. **Guessing:** Other players submit guesses during the turn timer.
6. **Scoring:** Scores tracked in real-time; after all rounds, total stats are updated.
7. **Leaderboard:** See who’s on top!

---

## Folder Structure

.
├── app/
│ ├── main.py
│ ├── ws_manager.py
│ ├── replicate_client.py
│ ├── rooms.py
│ ├── models.py
│ ├── schemas.py
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

yaml
Copy
Edit

---

## Environment Variables

- `DATABASE_URL`
- `REPLICATE_API_TOKEN`
- `SECRET_KEY`
- (See `.env.example` or `.env.docker` for a template)

---

## License

MIT License

---

**Made with ❤️ by [Profy8712](https://github.com/Profy8712) – PRs & stars welcome!**