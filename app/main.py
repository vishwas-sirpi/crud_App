from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .database import engine, Base, get_db
from . import crud, schemas

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI CRUD Items API",
    description="A backend-only RESTful CRUD API built with FastAPI, SQLAlchemy, SQLite, and Pydantic.",
    version="1.0.0"
)

@app.post("/items", response_model=schemas.ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """
    Create a new item in the database.
    - **name**: Must not be empty.
    - **price**: Must be strictly positive.
    - **quantity**: Must be non-negative.
    """
    return crud.create_item(db=db, item=item)

@app.get("/items", response_model=List[schemas.ItemResponse])
def read_items(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Retrieve a list of items with offset pagination.
    - **skip**: Number of items to skip (default: 0).
    - **limit**: Maximum number of items to return (default: 10).
    """
    return crud.get_items(db=db, skip=skip, limit=limit)

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
def update_item(item_id: int, item_update: schemas.ItemUpdate, db: Session = Depends(get_db)):
    """
    Update an existing item's fields by its ID.
    Raises 404 error if the item is not found.
    """
    db_item = crud.update_item(db=db, item_id=item_id, item_update=item_update)
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    return db_item

@app.delete("/items/{item_id}", response_model=schemas.ItemResponse)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """
    Delete an existing item by its ID.
    Raises 404 error if the item is not found.
    """
    db_item = crud.delete_item(db=db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    return db_item
