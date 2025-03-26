from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.schemas import UserLogin
from app.schemas import UserRegister
from app.services.auth import user_login
from app.services.auth import user_register
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency untuk mendapatkan sesi database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login", status_code=status.HTTP_200_OK)
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        user_data = user_login(db, user)
        if not user_data:
            logger.warning(f"Login failed for user: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Username atau Password Salah"
            )
        
        return {
            # "status": "success",
            "message": "Login successful",
            # "data": user_data
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
            "message": "An error occurred",
            "error": str(e)
        }
        )

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, db: Session = Depends(get_db)):
    try:
        logger.info(f"Menerima permintaan registrasi untuk: {user.username}")
        user_data = user_register(db, user)
        
        if user_data == "USERNAME_EXISTS":
            logger.warning(f"Registrasi gagal: Username {user.username} sudah digunakan.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Registrasi gagal, username sudah digunakan"
            )

        if not user_data:
            logger.error(f"Registrasi gagal: Tidak ada data yang dikembalikan dari database.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Registrasi gagal, terjadi kesalahan dalam sistem"
            )

        # Add explicit commit here
        db.commit()
        
        logger.info(f"Registrasi sukses untuk: {user.username}")
        return {
            "message": "Registrasi User berhasil",
            "data": user_data
        }

    except HTTPException as e:
        db.rollback()  # Rollback on error
        logger.warning(f"HTTP Exception: {str(e)}")
        raise

    except Exception as e:
        db.rollback()  # Rollback on error
        logger.error(f"Error Tidak Terduga: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Terjadi kesalahan dalam sistem: {str(e)}"
        )


