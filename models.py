from enum import Enum as PyEnum
from datetime import datetime
from sqlalchemy import Column,Integer,String,Boolean,Float,DateTime,Enum as SQLEnum,ForeignKey,JSON,Text
from sqlalchemy.orm import relationship
from database import Base

class UserRole(str, PyEnum):  # Inherits from both str and Enum
    ARTIST="artist"
    ORGANIZER="organizer"

class EventStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class ApplicationStatus(str, PyEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    password=Column(String,nullable=False)
    role=Column(SQLEnum(UserRole), nullable=False)
    created_at=Column(DateTime, default=datetime.utcnow)

    artist_profile=relationship("ArtistsProfile",back_populates="user",uselist=False)
    organizer_profile=relationship("OrganizerProfile",back_populates="user",uselist=False)

class ArtistsProfile(Base):
    __tablename__= "artistsprofile"
    id= Column(Integer,primary_key=True, index=True)
    user_id=Column(Integer,ForeignKey("users.id"), unique=True, nullable=False)
    full_name=Column(String, nullable=False)
    bio=Column(Text,nullable=True)
    talent_skill=Column(String, nullable=True)
    location=Column(String, nullable=True)
    phone_number=Column(String, nullable=True)

    user=relationship("User",back_populates="artist_profile")
    portfolios=relationship("PortfolioItem",back_populates="artist", cascade="all, delete-orphan")
    applications= relationship("Application",back_populates="artist")

class OrganizerProfile(Base):
    __tablename__= "organizerprofile"
    id= Column(Integer,primary_key=True, index=True)
    user_id=Column(Integer,ForeignKey("users.id"),unique=True,nullable=False)
    company_name=Column(String,nullable=False)
    description=Column(String,nullable=True)
    website_url=Column(String,nullable=True)
    location=Column(String,nullable=True)

    user=relationship("User",back_populates="organizer_profile")
    events=relationship("Event",back_populates="organizer", cascade="all, delete-orphan")

class PortfolioItem(Base):
    __tablename__="portfolioitems"
    id=Column(Integer,primary_key=True,index=True)
    artist_id=Column(Integer,ForeignKey("artistsprofile.id"),nullable=False)
    title=Column(String,nullable=False)
    description=Column(Text,nullable=True)
    media_url=Column(String,nullable=False)
    media_type=Column(String,nullable=True)
    ai_tags=Column(JSON,nullable=True)
    created_at=Column(DateTime, default=datetime.utcnow)

    artist=relationship("ArtistsProfile",back_populates="portfolios")

class Event(Base):
    __tablename__="events"
    id=Column(Integer,primary_key=True,index=True)
    organizer_id=Column(Integer,ForeignKey("organizerprofile.id"),nullable=False)
    title=Column(String,nullable=False)
    description=Column(Text,nullable=False)
    budget=Column(Float,nullable=True)
    event_date=Column(DateTime, nullable=True)
    status=Column(SQLEnum(EventStatus), default=EventStatus.OPEN,nullable=False)
    created_at=Column(DateTime, default=datetime.utcnow)

    organizer=relationship("OrganizerProfile",back_populates="events")
    applications=relationship("Application",back_populates="event",cascade="all, delete-orphan")

class Application(Base):
    __tablename__="applications"
    id=Column(Integer,primary_key=True,index=True)
    event_id=Column(Integer,ForeignKey("events.id"),nullable=False)
    artist_id=Column(Integer,ForeignKey("artistsprofile.id"),nullable=False)
    pitch_note=Column(Text,nullable=True)
    status=Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING,nullable=False)
    applied_at=Column(DateTime, default=datetime.utcnow)

    event=relationship("Event",back_populates="applications")
    artist=relationship("ArtistsProfile",back_populates="applications")


