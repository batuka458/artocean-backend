from pydantic import BaseModel,ConfigDict,Field,EmailStr,json
from enum import Enum
from datetime import datetime
class UserRole(str, Enum):  # Inherits from both str and Enum
    ARTIST="artist"
    ORGANIZER="organizer"

class EventStatus(str,Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class UserBase(BaseModel):
    
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    
    email: EmailStr|None = None
    password: str| None = Field(default=None, min_length=1)

class UserResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    email: EmailStr
    role: UserRole
    id:int
    created_at:datetime

class artist_profilesBase(BaseModel):

    full_name:str= Field(min_length=1)
    bio:str|None =Field(max_length=50)
    talent_skill: str|None
    location:str|None
    phone_number:str|None

class artist_profilesCreate(artist_profilesBase):
    pass

class artist_profilesUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    bio: str | None = Field(default=None, max_length=50)
    talent_skill: str | None = None
    location: str | None = None
    phone_number: str | None = None

class artist_profilesResponse(artist_profilesBase):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    id:int

class artist_publicResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    id: int
    full_name: str
    bio: str | None
    talent_skill: str | None
    location: str | None

class organizer_profilesBase(BaseModel):
    company_name:str|None
    description:str|None
    website_url:str|None
    location:str|None

class organizer_profilesCreate(organizer_profilesBase):
    pass

class organizer_profilesResponse(organizer_profilesBase):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    id:int

class organizer_publicResponse(BaseModel):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    id: int
    company_name: str
    description: str | None
    website_url: str | None
    location: str | None

class portfolio_itemsBase(BaseModel):
    title:str = Field(min_length=1)
    description:str|None
    media_url:str = Field(min_length=1)
    ai_tags:list[str]|None = Field(default_factory=list)

class portfolio_itemsResponse(portfolio_itemsBase):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    id:int
    artist_id:int
    media_type: str | None = None
    created_at:datetime

class eventsBase(BaseModel):
    title:str=Field(min_length=1)
    description:str=Field(min_length=1)
    budget:float|None=None
    event_date:datetime|None=None

class eventsCreate(eventsBase):
    pass

class eventsUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    budget: float | None = None
    event_date: datetime | None = None
    status: EventStatus | None = None

class eventsResponse(eventsBase):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    id:int
    organizer_id:int
    status:EventStatus
    created_at:datetime

class applicationsBase(BaseModel):
    pitch_note:str|None =None


class applicationsCreate(applicationsBase):
    pass 

class applicationsUpdate(BaseModel):
    status: ApplicationStatus

class applicationsResponse(applicationsBase):
    model_config = ConfigDict(validate_assignment=True, str_strip_whitespace=True,from_attributes=True)

    id:int
    event_id:int
    artist_id:int
    status:ApplicationStatus
    applied_at:datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
