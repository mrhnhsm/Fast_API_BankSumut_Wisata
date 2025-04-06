from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from app.routes import user, products  # Import router auth dan produk

app = FastAPI(
    title="FastAPI Authentication Aplikasi Wisata Bank Sumut",
    description="API untuk Data Wisata dengan PostgreSQL",
    version="1.0.0"
)

# Menyajikan folder assets sebagai file statis
app.mount("/static", StaticFiles(directory="app/asset"), name="static")

# Daftarkan router
app.include_router(user.router, prefix="/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/products", tags=["Products"])

# Root Endpoint
@app.get("/")
def home():
    return {"message": "Welcome To API Bank Sumut"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
