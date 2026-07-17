from typing import List, Optional, Tuple
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from . import models, schemas

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_item(db: Session, item_id: int):
    return db.query(models.Item).filter(models.Item.id == item_id).first()

def get_items(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    order: str = "asc",
) -> Tuple[int, List[models.Item]]:
    query = db.query(models.Item)

    if category:
        query = query.filter(models.Item.category == category)

    if min_price is not None:
        query = query.filter(models.Item.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Item.price <= max_price)

    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(models.Item.name).like(pattern),
                func.lower(models.Item.description).like(pattern)
            )
        )

    total = query.count()

    if sort_by:
        sort_columns = {
            "price": models.Item.price,
            "created_at": models.Item.created_at,
            "name": models.Item.name,
        }
        sort_column = sort_columns.get(sort_by)
        if sort_column is not None:
            if order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

    items = query.offset(skip).limit(limit).all()
    return total, items

def get_user_items(db: Session, user_id: int):
    return db.query(models.Item).filter(models.Item.user_id == user_id).all()

def create_item(db: Session, item: schemas.ItemCreate, user_id: int):
    db_item = models.Item(
        name=item.name,
        description=item.description,
        category=item.category,
        price=item.price,
        quantity=item.quantity,
        user_id=user_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update_item(db: Session, item_id: int, item_update: schemas.ItemUpdate):
    db_item = get_item(db, item_id)
    if not db_item:
        return None
    
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
        
    db.commit()
    db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int):
    db_item = get_item(db, item_id)
    if not db_item:
        return None
    db.delete(db_item)
    db.commit()
    return db_item
