from fastapi import Depends, FastAPI, HTTPException,status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File, Form
from io import BytesIO
from pathlib import Path
import shutil
from fastapi.staticfiles import StaticFiles
import cloudinary
import cloudinary.uploader
import os
import traceback
from datetime import datetime
from pydantic import EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from security import hash_password,create_token,get_current_artist
from security import verify_password,get_current_user,get_current_organizer
from database import Base, engine, get_db
from models import User,ArtistsProfile,OrganizerProfile,Event,PortfolioItem,Application,EventStatus,UserRole
from schemas import (
    UserCreate,
    UserResponse,
    artist_profilesCreate,
    artist_profilesUpdate,
    artist_profilesResponse,
    artist_publicResponse,

    organizer_profilesCreate,
    organizer_profilesResponse,
    organizer_publicResponse,
    
    LoginRequest,Token,

    portfolio_itemsResponse,

    eventsUpdate,
    eventsResponse,

    applicationsCreate,
    applicationsUpdate,
    applicationsResponse
)

app=FastAPI()

@app.exception_handler(Exception)
async def debug_unhandled_error(request, exc):
    traceback.print_exception(type(exc), exc, exc.__traceback__)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Unhandled server error",
            "error_type": type(exc).__name__
        }
    )

Base.metadata.create_all(bind=engine)
# MEDIA_DIR = Path("uploads")
# MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# app.mount(
#     "/uploads",
#     StaticFiles(directory=MEDIA_DIR),
#     name="uploads"
# )

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True
)

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
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login",response_model=Token)
def login(form_data:OAuth2PasswordRequestForm=Depends(),db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
            headers={"Www-Authenticate":"Bearer"}
        )
    if not verify_password(
        form_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )
    access_token=create_token(user)
    return{
        "access_token":access_token,
        "token_type":"bearer"
    }

    
@app.patch("/user/{user_id}",response_model=UserResponse)
def upd_user(
    user_id: int,
    email: EmailStr | None = Form(None),
    password: str | None = Form(None),
    media: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own account"
        )

    if email is not None:
        current_user.email = email

    if password is not None:
        current_user.password = hash_password(password)

    if media is not None:
        allowed_image_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }
        if media.content_type not in allowed_image_types:
            raise HTTPException(
                status_code=400,
                detail="Profile picture must be a JPEG, PNG, or WebP image"
            )

        max_size = 10 * 1024 * 1024
        try:
            content = media.file.read(max_size + 1)
            if len(content) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail="File exceeds the 10 MB limit"
                )

            upload_result = cloudinary.uploader.upload(
                BytesIO(content),
                resource_type="image",
                folder="profile_pictures"
            )
            profile_pic_url = upload_result.get("secure_url")
            if not profile_pic_url:
                raise HTTPException(
                    status_code=502,
                    detail="Profile picture upload failed"
                )
            current_user.profile_pic_url = profile_pic_url
        finally:
            media.file.close()

    db.commit()
    db.refresh(current_user)
    return current_user

@app.delete("/user/{user_id}",status_code=status.HTTP_204_NO_CONTENT)
def del_user(user_id:int,current_user:User=Depends(get_current_user),db:Session =Depends(get_db)):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own account"
        )
    db.delete(current_user)
    db.commit()

@app.post(
    "/artist/profile",
    response_model=artist_profilesResponse,
    status_code=status.HTTP_201_CREATED
)
def create_artist_profile(
    profile_data: artist_profilesCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ARTIST:
        raise HTTPException(
            status_code=403,
            detail="User role must be artist"
        )

    if current_user.artist_profile is not None:
        raise HTTPException(
            status_code=400,
            detail="Artist profile already exists"
        )

    artist = ArtistsProfile(
        user_id=current_user.id,
        full_name=profile_data.full_name,
        bio=profile_data.bio,
        talent_skill=profile_data.talent_skill,
        location=profile_data.location,
        phone_number=profile_data.phone_number
    )

    db.add(artist)
    db.commit()
    db.refresh(artist)

    return artist


@app.post("/organizer/profile/", response_model=organizer_profilesResponse, status_code=status.HTTP_201_CREATED)
def create_organizer_profile( profile_data: organizer_profilesCreate,current_user=Depends(get_current_user), db: Session = Depends(get_db)):

    if current_user.role != UserRole.ORGANIZER:
        raise HTTPException(status_code=403, detail="User role must be organizer")
    if current_user.organizer_profile is not None:
        raise HTTPException(status_code=400, detail="Organizer profile already exists")

    organizer = OrganizerProfile(
        user_id=current_user.id,
        company_name=profile_data.company_name,
        description=profile_data.description,
        website_url=profile_data.website_url,
        location=profile_data.location,
    )
    db.add(organizer)
    db.commit()
    db.refresh(organizer)
    return organizer


@app.get("/artist/", response_model=list[artist_publicResponse])
def artists(db:Session = Depends(get_db)):
    return db.query(ArtistsProfile).all()

@app.get("/artist/profile", response_model=artist_profilesResponse)
def artist(
    current_artist: ArtistsProfile = Depends(get_current_artist)
):
    return current_artist
        

@app.patch("/artist/profile",response_model=artist_profilesResponse)
def update_artist_profile(
    data: artist_profilesUpdate,
    current_artist: ArtistsProfile = Depends(get_current_artist),
    db: Session = Depends(get_db)
):
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_artist, field, value)
    
    db.commit()
    db.refresh(current_artist)

    return current_artist

@app.delete("/artist/profile",status_code=status.HTTP_204_NO_CONTENT)
def del_artist(current_artist:ArtistsProfile=Depends(get_current_artist), db:Session=Depends(get_db)):

    db.delete(current_artist)
    db.commit()

@app.get("/organizer/", response_model=list[organizer_publicResponse])
def organizers(db:Session=Depends(get_db)):
    return db.query(OrganizerProfile).all()

@app.get("/organizer/profile", response_model=organizer_profilesResponse)
def organizer(
    current_organizer: OrganizerProfile = Depends(get_current_organizer)
):
    return current_organizer

@app.patch("/organizer/profile",response_model=organizer_profilesResponse)
def upd_organizer(update_data:organizer_profilesCreate,current_organizer:OrganizerProfile=Depends(get_current_organizer),db:Session=Depends(get_db)):

    data=update_data.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(current_organizer, field, value)
    db.commit()
    db.refresh(current_organizer)
    return current_organizer

@app.delete("/organizer/",status_code=status.HTTP_204_NO_CONTENT)
def del_organizer(current_organizer:OrganizerProfile=Depends(get_current_organizer), db:Session=Depends(get_db)):

    db.delete(current_organizer)
    db.commit()

@app.post(
    "/artist/portfolio",
    response_model=portfolio_itemsResponse,
    status_code=status.HTTP_201_CREATED
)
def create_portfolio_item(
    title: str = Form(...),
    description: str = Form(""),
    media: UploadFile = File(...),
    current_artist: ArtistsProfile = Depends(get_current_artist),
    db: Session = Depends(get_db)
):
    allowed_types = {
        "image/jpeg": "image",
        "image/png": "image",
        "image/webp": "image",
        "video/mp4": "video",
        "audio/mpeg": "audio",
        "audio/wav": "audio",
        "application/pdf": "document",
    }

    media_type = allowed_types.get(media.content_type)

    if media_type is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported media type"
        )

    max_size = 10 * 1024 * 1024  # 10 MB

    try:
        content = media.file.read(max_size + 1)
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the 10 MB limit"
            )

        upload_result = cloudinary.uploader.upload(
            BytesIO(content),
            resource_type="auto",
            folder="portfolio"
        )
        media_url = upload_result.get("secure_url")
        if not media_url:
            raise HTTPException(
                status_code=502,
                detail="Media upload failed"
            )

        item = PortfolioItem(
            artist_id=current_artist.id,
            title=title,
            description=description,
            media_url=media_url,
            media_type=media_type,
            ai_tags=[]
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        return item
    
    finally:
        media.file.close()

@app.get("/artist/portfolio",response_model=list[portfolio_itemsResponse])
def get_artist_portfolio(current_artist:ArtistsProfile=Depends(get_current_artist)):
    return current_artist.portfolios

@app.get("/artist/{artist_id}", response_model=artist_publicResponse)
def public_artist(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(ArtistsProfile).filter(
        ArtistsProfile.id == artist_id
    ).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist

@app.get("/artist/{artist_id}/portfolio", response_model=list[portfolio_itemsResponse])
def get_public_artist_portfolio(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(ArtistsProfile).filter(
        ArtistsProfile.id == artist_id
    ).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    return artist.portfolios

@app.get("/portfolio/{portfolio_id}",response_model=portfolio_itemsResponse)
def get_portfolio_item(portfolio_id: int,db: Session = Depends(get_db)):
    item = (db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_id).first())
    if not item:
        raise HTTPException(status_code=404,detail="Portfolio item not found")

    return item

@app.patch("/portfolio/{portfolio_id}",response_model=portfolio_itemsResponse)
def update_portfolio_item(
    portfolio_id: int,
    title: str | None = Form(None),
    description: str | None = Form(None),
    ai_tags: list[str] | None = Form(None),
    media: UploadFile | None = File(None),
    current_artist: ArtistsProfile = Depends(get_current_artist),
    db: Session = Depends(get_db)
):
    item = db.query(PortfolioItem).filter(PortfolioItem.id == portfolio_id).first()
    if not item:
        raise HTTPException(status_code=404,detail="Portfolio item not found")
    if item.artist_id != current_artist.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this portfolio item")

    if title is not None:
        item.title = title
    if description is not None:
        item.description = description
    if ai_tags is not None:
        item.ai_tags = ai_tags

    if media is not None:
        allowed_types = {
            "image/jpeg": "image",
            "image/png": "image",
            "image/webp": "image",
            "video/mp4": "video",
            "audio/mpeg": "audio",
            "audio/wav": "audio",
            "application/pdf": "document",
        }
        media_type = allowed_types.get(media.content_type)
        if media_type is None:
            raise HTTPException(status_code=400, detail="Unsupported media type")

        max_size = 10 * 1024 * 1024
        try:
            content = media.file.read(max_size + 1)
            if len(content) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail="File exceeds the 10 MB limit"
                )

            upload_result = cloudinary.uploader.upload(
                BytesIO(content),
                resource_type="auto",
                folder="portfolio"
            )
            media_url = upload_result.get("secure_url")
            if not media_url:
                raise HTTPException(
                    status_code=502,
                    detail="Media upload failed"
                )

            item.media_url = media_url
            item.media_type = media_type
        finally:
            media.file.close()

    db.commit()
    db.refresh(item)

    return item

@app.delete("/portfolio/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio_item(
    portfolio_id: int,
    current_artist: ArtistsProfile = Depends(get_current_artist),
    db: Session = Depends(get_db)
):
    item = db.query(PortfolioItem).filter(
        PortfolioItem.id == portfolio_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Portfolio item not found"
        )

    if item.artist_id != current_artist.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to delete this portfolio item"
        )

    db.delete(item)
    db.commit()

@app.post("/organizer/events",response_model=eventsResponse,status_code=status.HTTP_201_CREATED)
def create_event(title:str=Form(...),
                 description:str=Form(""),
                 budget:float=Form(...),
                 event_date:datetime=Form(...),
                 event_poster:UploadFile=File(...),current_organizer:OrganizerProfile=Depends(get_current_organizer),db: Session = Depends(get_db)):
    allowed_types = {
        "image/jpeg": "image",
        "image/png": "image",
        "image/webp": "image",
    }

    if (allowed_types.get(event_poster.content_type)) is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported media type"
        )
    max_size=10*1024*1024
    stage = "reading poster"

    try:
        content = event_poster.file.read(max_size + 1)

        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail="File exceeds 10MB"
            )

        stage = "uploading poster to Cloudinary"

        upload_result = cloudinary.uploader.upload(
            BytesIO(content),
            resource_type="image",
            folder="event_poster"
        )

        event_poster_url = upload_result.get("secure_url")

        if not event_poster_url:
            raise HTTPException(
                status_code=502,
                detail="Image upload failed"
            )

        stage = "creating event record"

        event = Event(
            organizer_id=current_organizer.id,
            title=title,
            description=description,
            budget=budget,
            event_date=event_date,
            event_poster_url=event_poster_url
        )

        db.add(event)

        stage = "saving event to database"
        db.commit()
        db.refresh(event)

        stage = "building response"
        return event

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()
        print(f"EVENT ERROR at {stage}: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Event failed at {stage}: {type(exc).__name__}"
        ) from exc

    finally:
        event_poster.file.close()

@app.get("/events",response_model=list[eventsResponse])
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).all()

@app.get("/events/{event_id}",response_model=eventsResponse)
def get_event(event_id: int,db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404,detail="Event not found")

    return event

@app.get("/organizer/events",response_model=list[eventsResponse])
def load_events(current_organizer:OrganizerProfile=Depends(get_current_organizer)):
    return current_organizer.events

@app.get("/organizer/{organizer_id}", response_model=organizer_publicResponse)
def public_organizer(organizer_id: int, db: Session = Depends(get_db)):
    organizer = db.query(OrganizerProfile).filter(
        OrganizerProfile.id == organizer_id
    ).first()
    if organizer is None:
        raise HTTPException(status_code=404, detail="Organizer not found")
    return organizer

@app.get("/organizer/{organizer_id}/events", response_model=list[eventsResponse])
def get_public_organizer_events(organizer_id: int, db: Session = Depends(get_db)):
    organizer = db.query(OrganizerProfile).filter(
        OrganizerProfile.id == organizer_id
    ).first()
    if organizer is None:
        raise HTTPException(status_code=404, detail="Organizer not found")
    return organizer.events

@app.patch("/events/{event_id}",response_model=eventsResponse)
def upd_event(event_id: int, upd_event: eventsUpdate, current_organizer:OrganizerProfile=Depends(get_current_organizer),db: Session = Depends(get_db)):
    event=db.query(Event).filter(Event.id==event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="event not found")
    if current_organizer.id!=event.organizer_id:
        raise HTTPException(status_code=403,detail="you can update only your events")
    data=upd_event.model_dump(exclude_unset=True)

    for key,value in data.items():
        setattr(event,key,value)
    db.commit()
    db.refresh(event)

    return event

@app.delete("/events/{event_id}",status_code=status.HTTP_204_NO_CONTENT)
def del_event(event_id:int,current_organizer:OrganizerProfile=Depends(get_current_organizer),db:Session=Depends(get_db)):

    event=db.query(Event).filter(Event.id==event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="event not found")

    if current_organizer.id!=event.organizer_id:
        raise HTTPException(status_code=403,detail="you can delete only your events")
    db.delete(event)
    db.commit()

@app.post("/events/{event_id}/applications",response_model=applicationsResponse,status_code=status.HTTP_201_CREATED)
def create_application(event_id: int,data: applicationsCreate,current_artist:ArtistsProfile=Depends(get_current_artist),db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404,detail="Event not found")

    artist = db.query(ArtistsProfile).filter(ArtistsProfile.id == current_artist.id).first()
    if not artist:
        raise HTTPException(status_code=404,detail="Artist not found")

    if event.status != EventStatus.OPEN:
        raise HTTPException(status_code=400,detail="Applications are closed for this event")

    existing_application = db.query(Application).filter(Application.event_id == event_id,Application.artist_id == current_artist.id).first()

    if existing_application:
        raise HTTPException(status_code=400,detail="Artist has already applied to this event")

    application = Application(
        event_id=event_id,
        artist_id=current_artist.id,
        pitch_note=data.pitch_note
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return application

@app.get("/events/{event_id}/applications",response_model=list[applicationsResponse])
def get_event_applications(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user.role == UserRole.ORGANIZER:
        organizer = current_user.organizer_profile
        if organizer is None:
            raise HTTPException(status_code=403, detail="Organizer profile not found")
        if event.organizer_id != organizer.id:
            raise HTTPException(status_code=403, detail="You can only view applications for your own events")

        return db.query(Application).filter(
            Application.event_id == event_id
        ).all()

    if current_user.role == UserRole.ARTIST:
        artist = current_user.artist_profile
        if artist is None:
            raise HTTPException(status_code=403, detail="Artist profile not found")

        return db.query(Application).filter(
            Application.event_id == event_id,
            Application.artist_id == artist.id
        ).all()

    raise HTTPException(status_code=403, detail="Access denied")
    


@app.get("/applications/{application_id}",response_model=applicationsResponse)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if current_user.role == UserRole.ARTIST:
        artist = current_user.artist_profile
        if artist is None:
            raise HTTPException(status_code=403, detail="Artist profile not found")
        if application.artist_id != artist.id:
            raise HTTPException(status_code=403, detail="You can only view your own applications")
        return application

    if current_user.role == UserRole.ORGANIZER:
        organizer = current_user.organizer_profile
        if organizer is None:
            raise HTTPException(status_code=403, detail="Organizer profile not found")
        if application.event.organizer_id != organizer.id:
            raise HTTPException(status_code=403, detail="You can only view applications for your own events")
        return application

    raise HTTPException(status_code=403, detail="Access denied")

@app.patch("/applications/{application_id}",response_model=applicationsResponse)
def update_application(application_id: int,data: applicationsUpdate,current_organizer:OrganizerProfile=Depends(get_current_organizer),db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404,detail="Application not found")
    if current_organizer.id!=application.event.organizer_id:
        raise HTTPException(status_code=403,detail="you can only update status of your events")
    application.status = data.status

    db.commit()
    db.refresh(application)

    return application

@app.delete("/applications/{application_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int,current_artist:ArtistsProfile=Depends(get_current_artist),db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()

    if not application:
        raise HTTPException(status_code=404,detail="Application not found")
    if application.artist_id!=current_artist.id:
        raise HTTPException(status_code=403,detail="you can only delete your application")
    db.delete(application)
    db.commit()

@app.get("/auth/me",response_model=UserResponse)
def get_me(
    current_user:User=Depends(get_current_user)
):
    return current_user
