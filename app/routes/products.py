from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Path, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text  # Tambahkan import text
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal
from app.services.products import create_product, get_product_by_id, update_product, save_images, check_product_exists, get_all_products, get_products_by_category, get_products_by_kab_kota, delete_product, get_nearby_products, get_top_rated_products_by_location
import logging
import os
from typing import List, Optional, Dict
import traceback
import json

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
    request: Request,
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
    existing_detail_images: str = Form(None),  # JSON string of existing images to keep
    existing_display_images: str = Form(None),  # JSON string of existing images to keep
    detail_images: List[UploadFile] = File(None),  # Now properly optional
    display_images: List[UploadFile] = File(None),  # Now properly optional
    db: Session = Depends(get_db)
):
    """
    Memperbarui produk berdasarkan ID Serial dengan fleksibilitas untuk gambar
    """
    try:
        base_url = str(request.base_url)
        logger.info(f"Menerima permintaan untuk memperbarui produk dengan ID: {id_serial}")

        # Dapatkan informasi produk lama
        old_product = get_product_by_id(db, id_serial, base_url)

        if not old_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Produk dengan ID {id_serial} tidak ditemukan"
            )

        # Mengelola gambar detail
        detail_image_list = []
        old_detail_image_paths_to_remove = []
        
        # Gambar detail yang akan dipertahankan
        existing_detail_urls = []
        if existing_detail_images:
            try:
                existing_detail_urls = json.loads(existing_detail_images)
                # Pastikan existing_detail_urls adalah list
                if not isinstance(existing_detail_urls, list):
                    existing_detail_urls = []
            except json.JSONDecodeError:
                logger.warning(f"Format JSON tidak valid untuk existing_detail_images: {existing_detail_images}")
                existing_detail_urls = []
        
        # Ambil semua path gambar detail lama
        all_old_detail_paths = [img["filename_path"] for img in old_product.get("detail_images", [])]
        
        # Path URL ke path file sistem
        url_to_path_map = {}
        for img in old_product.get("detail_images", []):
            # Pastikan bahwa gambar memiliki properti "file_url"
            if "file_url" in img:
                url_to_path_map[img["file_url"]] = img["filename_path"]
        
        # Tentukan gambar yang akan dihapus (yang tidak ada di existing_detail_urls)
        for path in all_old_detail_paths:
            # Cari URL yang sesuai dengan path ini
            url = None
            for img in old_product.get("detail_images", []):
                if img.get("filename_path") == path and "file_url" in img:
                    url = img["file_url"]
                    break
                    
            if url and url not in existing_detail_urls:
                old_detail_image_paths_to_remove.append(path)
        
        # Konversi URL yang dipertahankan menjadi objek untuk dipertahankan dalam database
        for url in existing_detail_urls:
            if url in url_to_path_map:
                # Temukan gambar detail dari produk lama berdasarkan URL
                old_img = None
                for img in old_product.get("detail_images", []):
                    if img.get("file_url") == url:
                        old_img = img
                        break
                
                if old_img:
                    # Salin data gambar lama untuk dipertahankan
                    detail_image_list.append({
                        "filename": old_img["filename"],
                        "filename_path": old_img["filename_path"]
                    })

        # Upload gambar baru jika ada
        if detail_images:
            # Pastikan detail_images tidak None dan filter gambar kosong
            valid_detail_images = [img for img in detail_images if img and img.filename]
            if valid_detail_images:
                new_detail_image_list = save_images(valid_detail_images, "app/asset/detail_image")
                detail_image_list.extend(new_detail_image_list)

        # Mengelola gambar display dengan cara yang sama
        display_image_list = []
        old_display_image_paths_to_remove = []
        
        # Gambar display yang akan dipertahankan
        existing_display_urls = []
        if existing_display_images:
            try:
                existing_display_urls = json.loads(existing_display_images)
                # Pastikan existing_display_urls adalah list
                if not isinstance(existing_display_urls, list):
                    existing_display_urls = []
            except json.JSONDecodeError:
                logger.warning(f"Format JSON tidak valid untuk existing_display_images: {existing_display_images}")
                existing_display_urls = []
        
        # Ambil semua path gambar display lama
        all_old_display_paths = [img["filename_path"] for img in old_product.get("display_images", [])]
        
        # Reset dan isi url_to_path_map untuk display images
        url_to_path_map = {}
        for img in old_product.get("display_images", []):
            # Pastikan bahwa gambar memiliki properti "file_url"
            if "file_url" in img:
                url_to_path_map[img["file_url"]] = img["filename_path"]

        # Tentukan gambar yang akan dihapus
        for path in all_old_display_paths:
            # Cari URL yang sesuai dengan path ini
            url = None
            for img in old_product.get("display_images", []):
                if img.get("filename_path") == path and "file_url" in img:
                    url = img["file_url"]
                    break
                    
            if url and url not in existing_display_urls:
                old_display_image_paths_to_remove.append(path)
        
        # Konversi URL yang dipertahankan menjadi objek
        for url in existing_display_urls:
            if url in url_to_path_map:
                old_img = None
                for img in old_product.get("display_images", []):
                    if img.get("file_url") == url:
                        old_img = img
                        break
                
                if old_img:
                    display_image_list.append({
                        "filename": old_img["filename"],
                        "filename_path": old_img["filename_path"]
                    })

        # Upload gambar display baru jika ada
        if display_images:
            # Pastikan display_images tidak None dan filter gambar kosong
            valid_display_images = [img for img in display_images if img and img.filename]
            if valid_display_images:
                new_display_image_list = save_images(valid_display_images, "app/asset/display_image")
                display_image_list.extend(new_display_image_list)

        # Validasi: tidak perlu error jika user mempertahankan gambar yang ada
        # Jika tidak ada upload baru dan tidak ada yang dipertahankan, baru error
        if not detail_image_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setidaknya satu gambar detail harus ada"
            )
            
        if not display_image_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setidaknya satu gambar display harus ada"
            )

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
            old_detail_images=old_detail_image_paths_to_remove,  # Hanya hapus gambar yang tidak dipertahankan
            old_display_images=old_display_image_paths_to_remove  # Hanya hapus gambar yang tidak dipertahankan
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
        logger.error(traceback.format_exc())  # Tambahkan traceback untuk debugging
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

@router.get("/category/{category}/{latitude},{longitude}", status_code=status.HTTP_200_OK)
def get_products_by_category_route(
    request: Request, 
    category: str, 
    latitude: float, 
    longitude: float,
    sortby: str = None,
    location: str = None, 
    db: Session = Depends(get_db)):
    """
    Endpoint untuk mendapatkan produk berdasarkan kategori dengan jarak dari lokasi pengguna
    
    Query Parameters:
    - sortby: 'Distance', 'Price', 'Rating', atau 'Availability'
    - location: Filter berdasarkan kab_kota
    """
    try:
        logger.info(f"Menerima permintaan untuk mendapatkan produk dengan kategori: {category} dari lokasi ({latitude}, {longitude})")
        
        # Normalize sortby parameter to lowercase for consistency
        if sortby:
            sortby = sortby.lower()
            # Validate sortby parameter
            valid_sort_params = ['distance', 'price', 'rating', 'availability']
            if sortby not in valid_sort_params:
                logger.warning(f"Parameter pengurutan tidak valid: {sortby}. Menggunakan pengurutan default.")
                sortby = None
        
        # Get base URL for building image URLs
        base_url = str(request.base_url)
        
        # Call service to fetch products with filters
        products = get_products_by_category(
            db=db, 
            category=category, 
            latitude=latitude, 
            longitude=longitude,
            base_url=base_url,
            sortby=sortby,
            location=location
        )

        # Handle empty results
        if not products:
            logger.warning(f"Tidak ada produk ditemukan untuk kategori: {category}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tidak ada produk ditemukan untuk kategori: {category}"
            )

        # Build response with filter information
        filter_info = {}
        if sortby:
            filter_info["sortby"] = sortby
        if location:
            filter_info["location"] = location

        response = {
            "message": f"Berhasil mengambil produk dengan kategori {category}",
            "data": products
        }
        
        # Add filter info if any filters were applied
        if filter_info:
            response["filters_applied"] = filter_info

        return response

    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404)
        raise e

    except Exception as e:
        # Log and handle other exceptions
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

