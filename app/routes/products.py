from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Path, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text  # Tambahkan import text
from app.database import SessionLocal
from app.services.products import create_product, get_product_by_id, update_product, save_images, check_product_exists, get_all_products, get_products_by_category, get_products_by_kab_kota, delete_product, get_nearby_products, get_top_rated_products_by_location
import logging
import os
from typing import List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def add_product(
    user_id: int = Form(...),
    category: str = Form(...),
    place_name: str = Form(...),
    rating: float = Form(...),
    price: float = Form(...),
    stock: int = Form(...),
    description: str = Form(...),
    open_time: str = Form(...),
    close_time: str = Form(...),
    location: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    kab_kota: str = Form(...),
    detail_images: List[UploadFile] = File(...),
    display_images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Menambahkan produk baru
    """
    try:
        logger.info(f"Menerima permintaan tambah produk: {place_name}")
        
        # Periksa apakah produk sudah ada sebelum menyimpan gambar
        exists = check_product_exists(db, category, place_name)
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Produk/Tempat sudah ada"
            )
        
        # Simpan file gambar
        detail_image_list = save_images(detail_images, "app/asset/detail_image")
        display_image_list = save_images(display_images, "app/asset/display_image")

        # Panggil service untuk menyimpan produk ke database
        product_id = create_product(
            db,
            user_id=user_id,
            category=category,
            place_name=place_name,
            rating=rating,
            price=price,
            stock=stock,
            description=description,
            open_time=open_time,
            close_time=close_time,
            location=location,
            latitude=latitude,
            longitude=longitude,
            kab_kota=kab_kota,
            detail_images=detail_image_list,
            display_images=display_image_list
        )

        if not product_id:
            logger.warning("Gagal membuat produk: Tidak ada ID yang dikembalikan.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gagal membuat produk, data tidak valid atau sudah ada."
            )

        logger.info(f"Produk berhasil dibuat dengan ID: {product_id}")
        return {
            "message": "Produk berhasil ditambahkan",
            "product_id": product_id
        }

    except HTTPException as e:
        # Jika produk sudah ada, kita tidak perlu rollback karena tidak ada transaksi yang dimulai
        logger.warning(f"HTTP Exception: {str(e)}")
        raise

    except ValueError as e:
        logger.warning(f"Validasi gagal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Terjadi kesalahan dalam sistem",
                "error": str(e)
            }
        )

@router.get("/{id_serial}", status_code=status.HTTP_200_OK)
async def get_product(
    request: Request,  # Pindahkan ke awal
    id_serial: str,
    db: Session = Depends(get_db),  # Default argument tetap di belakang
):
    """
    Mendapatkan detail produk berdasarkan ID
    """
    try:
        logger.info(f"Menerima permintaan untuk mendapatkan produk dengan ID: {id_serial}")

        base_url = str(request.base_url)  # Ambil base URL dari request
        product = get_product_by_id(db, id_serial, base_url)

        return {
            "message": "Produk berhasil ditemukan",
            "data": product
        }

    except ValueError as e:
        logger.warning(f"Produk tidak ditemukan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Terjadi kesalahan dalam sistem",
                "error": str(e)
            }
        )

@router.put("/{id_serial}", status_code=status.HTTP_200_OK)
async def update_product_endpoint(
    request: Request,  # ✅ Tambahkan request untuk mendapatkan base_url
    id_serial: str = Path(..., description="Product ID"),
    user_id: int = Form(...),
    category: str = Form(...),
    place_name: str = Form(...),
    rating: float = Form(...),
    price: float = Form(...),
    stock: int = Form(...),
    description: str = Form(...),
    open_time: str = Form(...),
    close_time: str = Form(...),
    location: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    kab_kota: str = Form(...),
    detail_images: List[UploadFile] = File(...),
    display_images: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Memperbarui produk berdasarkan ID Serial
    """
    try:
        base_url = str(request.base_url)  # ✅ Ambil base_url dari request
        logger.info(f"Menerima permintaan untuk memperbarui produk dengan ID: {id_serial}")

        # ✅ Tambahkan base_url saat memanggil get_product_by_id
        old_product = get_product_by_id(db, id_serial, base_url)

        if not old_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produk dengan ID {id_serial} tidak ditemukan"
            )

        # Kumpulkan path gambar lama
        old_detail_image_paths = [img["filename_path"] for img in old_product["detail_images"]]
        old_display_image_paths = [img["filename_path"] for img in old_product["display_images"]]
        
        # Simpan file gambar baru
        detail_image_list = save_images(detail_images, "app/asset/detail_image")
        display_image_list = save_images(display_images, "app/asset/display_image")

        # Perbarui produk
        success = update_product(
            db,
            id_serial=id_serial,
            user_id=user_id,
            category=category,
            place_name=place_name,
            rating=rating,
            price=price,
            stock=stock,
            description=description,
            open_time=open_time,
            close_time=close_time,
            location=location,
            latitude=latitude,
            longitude=longitude,
            kab_kota=kab_kota,
            detail_images=detail_image_list,
            display_images=display_image_list,
            old_detail_images=old_detail_image_paths,
            old_display_images=old_display_image_paths
        )

        if not success:
            logger.warning(f"Gagal memperbarui produk dengan ID: {id_serial}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Gagal memperbarui produk."
            )

        logger.info(f"Produk dengan ID: {id_serial} berhasil diperbarui")
        return {
            "message": "Produk berhasil diperbarui",
            "product_id": id_serial
        }

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Terjadi kesalahan dalam sistem",
                "error": str(e)
            }
        )

@router.get("/", status_code=status.HTTP_200_OK)
def get_all_products_route(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint untuk mendapatkan semua produk
    """
    try:
        logger.info("Menerima permintaan untuk mendapatkan semua produk")

        base_url = str(request.base_url)
        products = get_all_products(db, base_url)

        return {
            "message": "Berhasil mengambil semua produk",
            "data": products
        }

    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Terjadi kesalahan dalam sistem",
                "error": str(e)
            }
        )

@router.get("/kab_kota/{kab_kota}/{latitude},{longitude}", status_code=status.HTTP_200_OK)
def get_products_by_kab_kota_route(
    request: Request, 
    kab_kota: str, 
    latitude: float, 
    longitude: float, 
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk mendapatkan produk berdasarkan kabupaten/kota dengan jarak dari lokasi pengguna
    """
    try:
        logger.info(f"Menerima permintaan untuk mendapatkan produk di kabupaten/kota: {kab_kota} dari lokasi ({latitude}, {longitude})")

        base_url = str(request.base_url)
        products = get_products_by_kab_kota(db, kab_kota, latitude, longitude, base_url)

        if not products:
            logger.warning(f"Tidak ada produk ditemukan di kabupaten/kota: {kab_kota}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tidak ada produk ditemukan di kabupaten/kota: {kab_kota}"
            )

        return {
            "message": f"Berhasil mengambil produk di {kab_kota}",
            "data": products
        }

    except HTTPException as e:
        raise e  # Meneruskan error 404 jika tidak ditemukan

    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Terjadi kesalahan dalam sistem",
                "error": str(e)
            }
        )

@router.get("/category/{category}", status_code=status.HTTP_200_OK)
def get_products_by_category_route(request: Request, category: str, db: Session = Depends(get_db)):
    """
    Endpoint untuk mendapatkan produk berdasarkan kategori
    """
    try:
        logger.info(f"Menerima permintaan untuk mendapatkan produk dengan kategori: {category}")

        base_url = str(request.base_url)
        products = get_products_by_category(db, category, base_url)

        if not products:
            logger.warning(f"Tidak ada produk ditemukan untuk kategori: {category}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tidak ada produk ditemukan untuk kategori: {category}"
            )

        return {
            "message": f"Berhasil mengambil produk dengan kategori {category}",
            "data": products
        }

    except HTTPException as e:
        raise e  # Meneruskan error 404 jika tidak ditemukan

    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Terjadi kesalahan dalam sistem",
                "error": str(e)
            }
        )

@router.delete("/{id_serial}", status_code=status.HTTP_200_OK)
async def delete_product_endpoint(
    id_serial: str = Path(..., description="Product ID"),
    db: Session = Depends(get_db)
):
    """
    Menghapus produk berdasarkan ID Serial
    """
    try:
        success = delete_product(db, id_serial)

        if not success:
            logger.warning(f"Gagal menghapus produk dengan ID: {id_serial}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gagal menghapus produk dengan ID {id_serial}"
            )

        logger.info(f"Produk dengan ID: {id_serial} berhasil dihapus")
        return {
            "message": "Produk berhasil dihapus",
            "product_id": id_serial
        }

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Terjadi kesalahan dalam sistem", "error": str(e)}
        )

@router.get("/nearme/{latitude},{longitude}", status_code=status.HTTP_200_OK)
async def find_nearby_products(
    request: Request,
    latitude: float,
    longitude: float,
    max_distance: Optional[int] = Query(10, description="Maximum distance in kilometers"),
    db: Session = Depends(get_db),
):
    """
    Mendapatkan produk terdekat berdasarkan koordinat pengguna.
    """

    # Validasi input
    if not (-90 <= latitude <= 90):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Latitude harus berada di antara -90 hingga 90."}
        )
    
    if not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Longitude harus berada di antara -180 hingga 180."}
        )

    if max_distance is not None and max_distance <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Max distance harus lebih besar dari 0."}
        )

    try:
        logger.info(f"Menerima permintaan produk dalam radius {max_distance} km dari ({latitude}, {longitude})")
        base_url = str(request.base_url)
        products = get_nearby_products(db, latitude, longitude, max_distance, base_url)

        # Jika tidak ada produk yang ditemukan, kembalikan error 404
        if not products:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Tidak ditemukan produk apapun yang terdekat dalam radius tersebut."}
            )

        return {
            "message": "Produk berhasil ditemukan",
            "data": products
        }

    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Terjadi kesalahan dalam sistem", "error": str(e)}
        )

@router.get("/populer/{latitude},{longitude}", status_code=status.HTTP_200_OK)
async def get_popular_products_by_location(
    request: Request,
    latitude: float = Path(..., description="Latitude lokasi pengguna"),
    longitude: float = Path(..., description="Longitude lokasi pengguna"),
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Kategori produk (opsional)"),
    limit: int = Query(10, description="Jumlah produk yang ingin diambil")
):
    """
    Endpoint untuk mendapatkan produk dengan rating tertinggi berdasarkan lokasi pengguna.
    - `latitude` dan `longitude`: Koordinat lokasi pengguna
    - `category` (opsional): Menyaring berdasarkan kategori.
    - `limit` (default: 10): Menentukan jumlah produk yang diambil.
    
    Returns produk dengan perhitungan jarak dan estimasi waktu tempuh.
    """

    # Validasi input
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Limit harus lebih besar dari 0."}
        )

    # Validasi koordinat
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Koordinat latitude/longitude tidak valid."}
        )

    try:
        logger.info(f"Memproses permintaan produk populer berdasarkan lokasi [{latitude}, {longitude}]: limit={limit}, category={category or 'Semua'}")
        base_url = str(request.base_url)
        products = get_top_rated_products_by_location(db, latitude, longitude, category, limit, base_url)

        # Jika tidak ada produk yang ditemukan, kembalikan error 404
        if not products:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Tidak ditemukan produk populer di sekitar lokasi Anda."}
            )

        return {
            "message": "Produk populer di sekitar lokasi Anda berhasil ditemukan",
            "data": products
        }

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        logger.error(f"Terjadi kesalahan dalam sistem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Terjadi kesalahan dalam sistem", "error": str(e)}
        )

