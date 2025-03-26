from sqlalchemy.orm import Session
from sqlalchemy import text
from app.schemas import UserLogin
from app.schemas import UserRegister
import logging
import psycopg2

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def user_login(db: Session, login_data: UserLogin):
    try:
        # Panggil FUNCTION PostgreSQL
        stored_func = """
        SELECT * FROM user_login(:username, :password);
        """
        
        params = {
            "username": login_data.username,
            "password": login_data.password
        }

        logger.info(f"Menjalankan stored function untuk pengguna: {login_data.username}")
        result = db.execute(text(stored_func), params).fetchone()

        if result:
            logger.info(f"Login berhasil untuk pengguna: {result[1]}")
            return {"id": result[0], "username": result[1]}
        
        logger.info(f"Kredensial tidak valid untuk pengguna: {login_data.username}")
        return None
        
    except Exception as e:
        logger.error(f"Error database: {str(e)}")
        raise

def user_register(db: Session, register_data: UserRegister):
    try:
        stored_func = """
        SELECT * FROM user_register(:username, :password, :roles);
        """
        
        params = {
            "username": register_data.username,
            "password": register_data.password,
            "roles": register_data.roles
        }

        logger.info(f"Menjalankan stored function untuk register: {register_data.username}")
        result = db.execute(text(stored_func), params).fetchone()
        
        # Commit the transaction
        db.commit()

        if result:
            logger.info(f"Registrasi berhasil untuk user: {result[1]}")
            return {"id": result[0], "username": result[1], "roles": result[2], "created_at": result[3]}

        logger.error("Tidak ada data yang dikembalikan dari stored function.")
        return None

    except Exception as e:
        db.rollback()  # Rollback on error
        error_message = str(e)
        
        # Check if this is the specific username exists error
        if "USERNAME_EXISTS" in error_message:
            logger.warning(f"Username sudah ada: {register_data.username}")
            return "USERNAME_EXISTS"
        
        logger.error(f"Error database tidak terduga: {str(e)}")
        raise
