from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.database import get_db
from app.db.models_db import User
from app.accounts import schemas, services, auth

router = APIRouter()

@router.post("/register", response_model=schemas.UserRead)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = services.get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post("/login", response_model=schemas.Token)
async def login(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalars().first()
    if not db_user or not services.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserRead)
async def get_me(current_user: User = Depends(auth.get_current_user)):
    return current_user

@router.get("/leaderboard", response_model=list[schemas.UserStats])
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.total_score.desc()).limit(10))
    users = result.scalars().all()
    return users

# --- PUBLIC STATS ENDPOINT ---
@router.get("/stats/{username}", response_model=schemas.UserStats)
async def get_user_stats(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

accounts_router = router
