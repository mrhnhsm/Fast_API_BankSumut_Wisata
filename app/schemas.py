from pydantic import BaseModel
from typing import List

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    roles: str = "user"

class ProductCreate(BaseModel):
    user_id: int
    category: str
    place_name: str
    rating: float
    price: float
    stock: int
    description: str
    open_time: str
    close_time: str
    location: str
    latitude: float
    longitude: float
    kab_kota: str
