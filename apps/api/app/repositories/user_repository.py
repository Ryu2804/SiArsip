from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User

def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User).where(User.email == email)
    )

def get_by_username(db: Session, name: str) -> User | None:
    return db.scalar(
        select(User).where(User.name == name)
    )

def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.scalar(
        select(User).where(User.id == str(user_id))
    )

def create_user(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    return user
