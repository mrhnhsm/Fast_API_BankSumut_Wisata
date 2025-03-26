from fastapi import FastAPI
from app.routes import user  # Import router auth

app = FastAPI(
    title="FastAPI Authentication Aplikasi Wisata Bank Sumut",
    description="API untuk Data Wisata dengan PostgreSQL",
    version="1.0.0"
)

# Daftarkan router
app.include_router(user.router, prefix="/auth", tags=["Authentication"])

# Root Endpoint
@app.get("/")
def home():
    return {"message": "Welcome To API Bank Sumut"}
