from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from fastapi import Depends,FastAPI,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
import os,jwt
from datetime import datetime,timedelta,timezone
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session
from database import get_db
from models import User,UserRole

SECRET_KEY=os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET-KEY environment variable is not set")
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(password, hashed_password)
    except UnknownHashError:
        return False

def create_token(user:User ,expire_delta:timedelta | None=None)->str:

    if expire_delta is None:
        expire_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expire_time=datetime.now(timezone.utc) + expire_delta

    payload={"sub":str(user.id),"role":user.role,"exp":expire_time}

    return jwt.encode(
        payload,SECRET_KEY,algorithm=ALGORITHM
    )

oauth2_scheme=OAuth2PasswordBearer(
    tokenUrl="auth/login"
)

def get_current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(get_db))->User:

    credential_exceptions=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="could not validate credential",headers={"WWW-Authenticate":"Bearer"})

    try:
        payload=jwt.decode(
            token,SECRET_KEY,algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if not isinstance(user_id, str):
            raise credential_exceptions

        try:
            user_id = int(user_id)
        except ValueError:
            raise credential_exceptions

        if user_id <= 0:
            raise credential_exceptions

    except(InvalidTokenError,ValueError):
        raise credential_exceptions

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credential_exceptions

    return user

def get_current_artist(current_User:User=Depends(get_current_user)):
    if current_User.role!=UserRole.ARTIST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Artist access required")

    if current_User.artist_profile is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Artist profile not found")
    return current_User.artist_profile

def get_current_organizer(
    current_user: User = Depends(get_current_user)
):

    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer access required"
        )

    if current_user.organizer_profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organizer profile not found"
        )

    return current_user.organizer_profile
