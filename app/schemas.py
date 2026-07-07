from pydantic import BaseModel, Field
from typing import Optional

# User schemas
class UserBase(BaseModel):
    email: str = Field(..., description="The user's email address")

class UserCreate(UserBase):
    password: str = Field(..., min_length=4)

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Item schemas
class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, description="The name of the item (cannot be empty)")
    description: Optional[str] = Field(None, description="An optional description of the item")
    price: float = Field(..., gt=0, description="The price of the item (must be positive)")
    quantity: int = Field(0, ge=0, description="The quantity of the item (must be non-negative)")

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="The name of the item (cannot be empty if provided)")
    description: Optional[str] = Field(None, description="An optional description of the item")
    price: Optional[float] = Field(None, gt=0, description="The price of the item (must be positive if provided)")
    quantity: Optional[int] = Field(None, ge=0, description="The quantity of the item (must be non-negative if provided)")

class ItemResponse(ItemBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
