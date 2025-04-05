from sqlalchemy import Column, Integer, String, DateTime, Float, DECIMAL, Time, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    roles = Column(String, default="user")  # Tambah kolom roles
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Product(Base):
    __tablename__ = "products"

    id_serial = Column(String, primary_key=True)
    user_id = Column(Integer, nullable=False)
    place_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    rating = Column(Float, nullable=False)
    price = Column(DECIMAL, nullable=False)
    stock = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    open_time = Column(Time, nullable=False)
    close_time = Column(Time, nullable=False)
    location = Column(String, nullable=False)
    latitude = Column(DECIMAL, nullable=False)
    longitude = Column(DECIMAL, nullable=False)
    kab_kota = Column(String, nullable=False)

class DetailImage(Base):
    __tablename__ = "detail_image"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id_serial"), nullable=False)
    filename = Column(String, nullable=False)
    filename_path = Column(String, nullable=False)

class DisplayImage(Base):
    __tablename__ = "display_image"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id_serial"), nullable=False)
    filename = Column(String, nullable=False)
    filename_path = Column(String, nullable=False)