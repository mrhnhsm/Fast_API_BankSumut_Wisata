from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # Tambahkan import ini
import os
from fastapi.responses import JSONResponse
import urllib.request
from app.routes import user, products

app = FastAPI(
    title="FastAPI Authentication Aplikasi Wisata Bank Sumut",
    description="API untuk Data Wisata dengan PostgreSQL",
    version="1.0.0"
)

# Tambahkan middleware CORS setelah inisialisasi app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan domain spesifik di production
    allow_credentials=True,
    allow_methods=["*"],  # Izinkan semua metode HTTP
    allow_headers=["*"],
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

# ✅ Endpoint Cek Koneksi Internet 
@app.get("/cek-koneksi", tags=["Utils"])
def cek_koneksi():
    try:
        urllib.request.urlopen('https://www.google.com', timeout=5)
        return JSONResponse(content={"status": "connected", "message": "Internet aktif"})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "disconnected", "message": "Tidak ada koneksi internet", "error": str(e)}
        )

# Ini penting untuk Railway
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
