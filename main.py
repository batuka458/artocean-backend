from fastapi import Depends, FastAPI, HTTPException,status
from sqlalchemy.orm import Session
from security import hash_password
from security import verify_password
from database import Base, engine, get_db
from models import User,ArtistsProfile,OrganizerProfile,Event,PortfolioItem,Application,EventStatus
from schemas import (
    UserCreate,
    UserResponse,
    artist_profilesCreate,
    artist_profilesUpdate,
    artist_profilesResponse,
    organizer_profilesCreate,
    UserUpdate,
    organizer_profilesResponse,
    LoginRequest,
    portfolio_itemsCreate,
    portfolio_itemsUpdate,
    portfolio_itemsResponse,

    eventsCreate,
    eventsUpdate,
    eventsResponse,

    applicationsCreate,
    applicationsUpdate,
    applicationsResponse
)

app=FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message":"Hello building beckend for artocean"}


@app.get("/user/",response_model=list[UserResponse])
def users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/user/{user_id}",response_model=UserResponse)
def user(user_id:int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user

@app.post("/auth/register", response_model=UserResponse,status_code=status.HTTP_201_CREATED)
def post_user(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    user = User(
        email=user_data.email,
        password=hash_password(user_data.password),
        role=user_data.role.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login")
def login(data: LoginRequest,db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=401,detail="Invalid email or password")

    stored_password = user.password
    is_valid = verify_password(data.password, stored_password)

    # Backward compatibility for old rows saved as plain text: allow once, then upgrade to hash.
    if (not is_valid) and (data.password == stored_password):
        user.password = hash_password(data.password)
        db.commit()
        is_valid = True

    if not is_valid:
        raise HTTPException(status_code=401,detail="Invalid email or password")
    return {
        "message": "Login successful",
        "user_id": user.id,
        "role": user.role
    }

@app.patch("/user/{user_id}",response_model=UserResponse)
def upd_user(user_id:int, update_data:UserUpdate,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data= update_data.model_dump(exclude_unset=True)

    if "email" in data and data["email"] is not None:
        user.email=data["email"]
    if "password" in data and data["password"] is not None:
        user.password = hash_password(data["password"])

    db.commit()
    db.refresh(user)
    return user

@app.delete("/user/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
def del_user(user_id:int,db:Session =Depends(get_db)):
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()

@app.post("/artist/profile/{user_id}", response_model=artist_profilesResponse, status_code=status.HTTP_201_CREATED)
def create_artist_profile(user_id:int, profile_data: artist_profilesCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.value != "artist":
        raise HTTPException(status_code=400, detail="User role must be artist")
    if user.artist_profile is not None:
        raise HTTPException(status_code=400, detail="Artist profile already exists")

    artist = ArtistsProfile(
        user_id=user_id,
        full_name=profile_data.full_name,
        bio=profile_data.bio,
        talent_skill=profile_data.talent_skill,
        location=profile_data.location,
        phone_number=profile_data.phone_number,
    )
    db.add(artist)
    db.commit()
    db.refresh(artist)
    return artist


@app.post("/organizer/profile/{user_id}", response_model=organizer_profilesResponse, status_code=status.HTTP_201_CREATED)
def create_organizer_profile(user_id:int, profile_data: organizer_profilesCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role.value != "organizer":
        raise HTTPException(status_code=400, detail="User role must be organizer")
    if user.organizer_profile is not None:
        raise HTTPException(status_code=400, detail="Organizer profile already exists")

    organizer = OrganizerProfile(
        user_id=user_id,
        company_name=profile_data.company_name,
        description=profile_data.description,
        website_url=profile_data.website_url,
        location=profile_data.location,
    )
    db.add(organizer)
    db.commit()
    db.refresh(organizer)
    return organizer


@app.get("/artist/", response_model=list[artist_profilesResponse])
def artists(db:Session = Depends(get_db)):
    return db.query(ArtistsProfile).all()

@app.get("/artist/{artist_id}",response_model=artist_profilesResponse)
def artist(artist_id:int,db:Session=Depends(get_db)):
    artist=db.query(ArtistsProfile).filter(ArtistsProfile.id==artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail= "User not found")
    return artist

@app.patch("/artist/{artist_id}", response_model=artist_profilesResponse)
def update_artist_profile(
    artist_id: int,
    update_data: artist_profilesUpdate,
    db: Session = Depends(get_db),
):
    artist = db.query(ArtistsProfile).filter(ArtistsProfile.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist profile not found")

    data = update_data.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(artist, field, value)

    db.commit()
    db.refresh(artist)
    return artist

@app.delete("/artist/{artist_id}",status_code=status.HTTP_204_NO_CONTENT)
def del_artist(artist_id:int, db:Session=Depends(get_db)):
    artist=db.query(ArtistsProfile).filter(ArtistsProfile.id==artist_id).first()
    if not artist:
        raise HTTPException(status_code=404,detail="artist not found")
    db.delete(artist)
    db.commit()

@app.get("/organizer/", response_model=list[organizer_profilesResponse])
def organizers(db:Session=Depends(get_db)):
    return db.query(OrganizerProfile).all()

@app.get("/organizer/{organizer_id}",response_model=organizer_profilesResponse)
def organizer(organizer_id:int,db:Session=Depends(get_db)):
    organizer=db.query(OrganizerProfile).filter(OrganizerProfile.id==organizer_id).first()
    if not organizer:
        raise HTTPException(status_code=404, detail="organizer not found")
    return organizer

@app.patch("/organizer/{organizer_id}",response_model=organizer_profilesResponse)
def upd_organizer(organizer_id:int,update_data:organizer_profilesCreate,db:Session=Depends(get_db)):
    organizer=db.query(OrganizerProfile).filter(OrganizerProfile.id==organizer_id).first()
    if not organizer:
        raise HTTPException(status_code=404, detail="organizer not found")
    data=update_data.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(organizer, field, value)
    db.commit()
    db.refresh(organizer)
    return organizer

@app.delete("/organizer/{organizer_id}",status_code=status.HTTP_204_NO_CONTENT)
def del_organizer(organizer_id:int, db:Session=Depends(get_db)):
    organizer=db.query(OrganizerProfile).filter(OrganizerProfile.id==organizer_id).first()
    if not organizer:
        raise HTTPException(status_code=404, detail="Organizer not found")
    db.delete(organizer)
    db.commit()

@app.post("/artist/{artist_id}/portfolio",response_model=portfolio_itemsResponse,status_code=status.HTTP_201_CREATED)
def create_portfolio_item(artist_id: int,data: portfolio_itemsCreate,db: Session = Depends(get_db)):
    artist = db.query(ArtistsProfile).filter(ArtistsProfile.id == artist_id).first()

    if not artist:
        raise HTTPException(status_code=404,detail="Artist not found")

    portfolio_item = PortfolioItem(
        artist_id=artist_id,
        title=data.title,
        description=data.description,
        media_url=data.media_url,
        ai_tags=data.ai_tags
    )

    db.add(portfolio_item)
    db.commit()
    db.refresh(portfolio_item)

    return portfolio_item

@app.get("/artist/{artist_id}/portfolio",response_model=list[portfolio_itemsResponse])
def get_artist_portfolio(artist_id: int,db: Session = Depends(get_db)):
    artist = db.query(ArtistsProfile).filter(ArtistsProfile.id == artist_id).first()

    if not artist:
        raise HTTPException(status_code=404,detail="Artist not found")

    return (db.query(PortfolioItem).filter(PortfolioItem.artist_id == artist_id).all())

@app.get("/portfolio/{portfolio_id}",response_model=portfolio_itemsResponse)
def get_portfolio_item(portfolio_id: int,db: Session = Depends(get_db)):
    item = (db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_id).first())
    if not item:
        raise HTTPException(status_code=404,detail="Portfolio item not found")

    return item

@app.patch("/portfolio/{portfolio_id}",response_model=portfolio_itemsResponse)
def update_portfolio_item(portfolio_id: int,data: portfolio_itemsUpdate,db: Session = Depends(get_db)):
    item = db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_id).first()
    
    if not item:
        raise HTTPException(status_code=404,detail="Portfolio item not found")

    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return item

@app.delete("/portfolio/{portfolio_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_item(portfolio_id: int,db: Session = Depends(get_db)):
    item = db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_id).first()

    if not item:
        raise HTTPException(status_code=404,detail="Portfolio item not found")

    db.delete(item)
    db.commit()

@app.post("/organizer/{organizer_id}/events",response_model=eventsResponse,status_code=status.HTTP_201_CREATED)
def create_event(organizer_id: int,data: eventsCreate,db: Session = Depends(get_db)):
    organizer = db.query(OrganizerProfile).filter(OrganizerProfile.id == organizer_id).first()
    if not organizer:
        raise HTTPException(status_code=404,detail="Organizer not found")

    event = Event(
        organizer_id=organizer_id,
        title=data.title,
        description=data.description,
        budget=data.budget,
        event_date=data.event_date
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event

@app.get("/events",response_model=list[eventsResponse])
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).all()

@app.get("/events/{event_id}",response_model=eventsResponse)
def get_event(event_id: int,db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404,detail="Event not found")

    return event

@app.get("/organizer/{organizer_id}/events",response_model=list[eventsResponse])
def load_events(organizer_id:int,db:Session=Depends(get_db)):
    organizer=db.query(OrganizerProfile).filter(OrganizerProfile.id==organizer_id).first()
    if not organizer:
        raise HTTPException(status_code=404, detail="organizer not found")
    return organizer.events

@app.patch("/events/{event_id}",response_model=eventsResponse)
def upd_event(event_id: int, upd_event: eventsUpdate, db: Session = Depends(get_db)):
    event=db.query(Event).filter(Event.id==event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    data=upd_event.model_dump(exclude_unset=True)

    for key,value in data.items():
        setattr(event,key,value)
    db.commit()
    db.refresh(event)

    return event

@app.delete("/events/{event_id}",status_code=status.HTTP_204_NO_CONTENT)
def del_event(event_id:int,db:Session=Depends(get_db)):
    event=db.query(Event).filter(Event.id==event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    db.delete(event)
    db.commit()

@app.post("/events/{event_id}/applications",response_model=applicationsResponse,status_code=status.HTTP_201_CREATED)
def create_application(event_id: int,data: applicationsCreate,artist_id: int,db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404,detail="Event not found")

    artist = db.query(ArtistsProfile).filter(ArtistsProfile.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404,detail="Artist not found")

    if event.status != EventStatus.OPEN:
        raise HTTPException(status_code=400,detail="Applications are closed for this event")

    existing_application = db.query(Application).filter(Application.event_id == event_id,Application.artist_id == artist_id).first()

    if existing_application:
        raise HTTPException(status_code=400,detail="Artist has already applied to this event")

    application = Application(
        event_id=event_id,
        artist_id=artist_id,
        pitch_note=data.pitch_note
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return application

@app.get("/events/{event_id}/applications",response_model=list[applicationsResponse])
def get_event_applications(event_id: int,db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404,detail="Event not found")

    return db.query(Application).filter(Application.event_id == event_id).all()

@app.get("/applications/{application_id}",response_model=applicationsResponse)
def get_application(application_id:int,db:Session=Depends(get_db)):
    application=db.query(Application).filter(Application.id==application_id).first()
    if not application:
        raise HTTPException(status_code=404,detail="application not found")
    return application

@app.patch("/applications/{application_id}",response_model=applicationsResponse)
def update_application(application_id: int,data: applicationsUpdate,db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404,detail="Application not found")

    application.status = data.status

    db.commit()
    db.refresh(application)

    return application

@app.delete("/applications/{application_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int,db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404,detail="Application not found")

    db.delete(application)
    db.commit()

