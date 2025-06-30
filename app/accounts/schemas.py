from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    total_games: int
    total_score: int
    avatar_url: str | None = None

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserStats(BaseModel):
    username: str
    total_games: int
    total_score: int

    class Config:
        orm_mode = True
