from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from . import crud, schemas, auth, models

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI CRUD Items API",
    description="A backend-only RESTful CRUD API built with FastAPI, SQLAlchemy, SQLite, and Pydantic.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI CRUD API! Visit /docs for the API documentation."}

@app.post("/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = auth.get_password_hash(user.password)
    return crud.create_user(db=db, user=user, hashed_password=hashed_password)

@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/items", response_model=List[schemas.ItemResponse])
def read_user_items(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return crud.get_user_items(db=db, user_id=current_user.id)

@app.post("/items", response_model=schemas.ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: schemas.ItemCreate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Create a new item in the database.
    - **name**: Must not be empty.
    - **price**: Must be strictly positive.
    - **quantity**: Must be non-negative.
    """
    return crud.create_item(db=db, item=item, user_id=current_user.id)

@app.get("/items", response_model=schemas.PaginatedItems)
def read_items(
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: str = "asc",
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of items.
    - **skip**: Number of items to skip (default: 0)
    - **limit**: Maximum number of items to return (default: 10, max: 100)
    - **category**: Exact match filter on item category
    - **min_price** / **max_price**: Numeric range filters on price
    - **search**: Case-insensitive partial match on name or description
    - **sort_by**: Field to sort by (price, created_at, name)
    - **order**: asc or desc (default: asc)
    """
    if skip < 0 or limit < 0:
        raise HTTPException(status_code=422, detail="skip and limit must be non-negative")
    if limit > 100:
        raise HTTPException(status_code=422, detail="limit must not exceed 100")

    order_lower = order.lower()
    if order_lower not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="order must be 'asc' or 'desc'")

    allowed_sort_fields = {"price", "created_at", "name"}
    if sort_by is not None and sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=422,
            detail=f"sort_by must be one of: {', '.join(sorted(allowed_sort_fields))}",
        )

    total, items = crud.get_items(
        db=db,
        skip=skip,
        limit=limit,
        category=category,
        min_price=min_price,
        max_price=max_price,
        search=search,
        sort_by=sort_by,
        order=order_lower,
    )
    return {"total": total, "skip": skip, "limit": limit, "items": items}

@app.get("/items/{item_id}", response_model=schemas.ItemResponse)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single item by its ID.
    Raises 404 error if the item is not found.
    """
    db_item = crud.get_item(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    return db_item

@app.put("/items/{item_id}", response_model=schemas.ItemResponse)
def update_item(item_id: int, item_update: schemas.ItemUpdate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Update an existing item's fields by its ID.
    Raises 404 error if the item is not found.
    """
    db_item = crud.get_item(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    if db_item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this item")
    return crud.update_item(db=db, item_id=item_id, item_update=item_update)

@app.delete("/items/{item_id}", response_model=schemas.ItemResponse)
def delete_item(item_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Delete an existing item by its ID.
    Raises 404 error if the item is not found.
    """
    db_item = crud.get_item(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    if db_item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this item")
    return crud.delete_item(db=db, item_id=item_id)
