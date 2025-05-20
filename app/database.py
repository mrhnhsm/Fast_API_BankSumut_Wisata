import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL YANG DIGUNAKAN:", DATABASE_URL)

# Make sure to use the synchronous PostgreSQL driver
# If your DATABASE_URL starts with postgresql+asyncpg://, change it to postgresql://
if DATABASE_URL and DATABASE_URL.startswith('postgresql+asyncpg://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')

# Create the engine without attempting connection at startup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)