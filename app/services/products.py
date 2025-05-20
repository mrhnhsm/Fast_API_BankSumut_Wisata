from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import uuid
import json
import shutil
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_product_exists(db: Session, category: str, place_name: str) -> bool:
    """
    Memeriksa apakah produk dengan kategori dan nama tempat tertentu sudah ada
    """
    try:
        query = text("SELECT check_product_exists(:category, :place_name)")
        result = db.execute(query, {"category": category, "place_name": place_name})
        return result.scalar()
    except Exception as e:
        logger.error(f"Error saat memeriksa keberadaan produk: {str(e)}")
        raise

def save_images(image_files, folder: str) -> List[Dict[str, str]]:
    """
    Menyimpan file gambar ke dalam folder yang ditentukan dan mengembalikan daftar informasi gambar.
    """
    # Pastikan folder ada
    os.makedirs(folder, exist_ok=True)
    
    image_list = []
    for image in image_files:
        timestamp = datetime.utcnow().timestamp()
        unique_code = uuid.uuid4().hex[:8]
        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{timestamp}_{unique_code}{file_extension}"  # Format file unik
        filepath = os.path.join(folder, unique_filename)
        try:
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_list.append({"filename": image.filename, "filename_path": filepath})
        except Exception as e:
            logger.error(f"Gagal menyimpan gambar {image.filename}: {str(e)}")
            raise
    return image_list

def create_product(
    db: Session, 
    user_id: int, 
    category: str, 
    place_name: str, 
    rating: float, 
    price: float, 
    stock: int, 
    description: str, 
    open_time: str, 
    close_time: str, 
    location: str, 
    latitude: float, 
    longitude: float,
    kab_kota: str,  # Tambahan kolom
    detail_images: List[Dict[str, str]],
    display_images: List[Dict[str, str]]
) -> str:
    """
    Membuat produk baru di dalam database.
    """
    try:
        logger.info("Memeriksa apakah produk sudah ada...")

        # Cek apakah produk sudah ada
        exists = check_product_exists(db, category, place_name)
        if exists:
            logger.warning(f"Produk dengan kategori '{category}' dan nama '{place_name}' sudah ada.")
            raise ValueError("Produk/Tempat sudah ada")

        logger.info("Memulai proses penambahan produk...")

        # Eksekusi fungsi stored procedure
        query = text("""
        SELECT insert_product(
            :user_id, :category, :place_name, :rating, :price, :stock, :description, 
            :open_time, :close_time, :location, :latitude, :longitude, :kab_kota, :detail_images, :display_images
        )
        """)

        result = db.execute(
            query,
            {
                "user_id": user_id,
                "category": category,
                "place_name": place_name,
                "rating": rating,
                "price": price,
                "stock": stock,
                "description": description,
                "open_time": open_time,
                "close_time": close_time,
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "kab_kota": kab_kota,  # Tambahkan parameter ini
                "detail_images": json.dumps(detail_images),
                "display_images": json.dumps(display_images)
            }
        )

        product_id = result.scalar()

        if product_id:
            db.commit()
            logger.info(f"Produk berhasil ditambahkan dengan ID: {product_id}")
            return product_id
        else:
            db.rollback()
            logger.error("Gagal mendapatkan ID produk dari fungsi insert_product.")
            raise Exception("Gagal menyimpan produk.")

    except ValueError as e:
        db.rollback()
        logger.warning(f"Validasi gagal: {str(e)}")
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Kesalahan database saat menambahkan produk: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Terjadi kesalahan tidak terduga: {str(e)}")
        raise

def get_product_by_id(db: Session, id_serial: str, base_url: str) -> Dict[str, Any]:
    """
    Mendapatkan detail produk berdasarkan ID Serial
    """
    try:
        logger.info(f"Mengambil data produk dengan ID Serial: {id_serial}")

        # Dapatkan data produk
        product_query = text("SELECT * FROM get_product_by_id(:id_serial)")
        product_result = db.execute(product_query, {"id_serial": id_serial}).fetchone()

        if not product_result:
            logger.warning(f"Produk dengan ID Serial {id_serial} tidak ditemukan")
            raise ValueError(f"Produk dengan ID Serial {id_serial} tidak ditemukan")

        # Konversi ke dictionary dengan aman
        product_dict = dict(product_result._mapping)

        # Dapatkan gambar detail
        detail_images_query = text("SELECT * FROM get_detail_images(:id_serial)")
        detail_images_result = db.execute(detail_images_query, {"id_serial": id_serial}).fetchall()
        detail_images = [
            {
                **dict(row._mapping),
                "file_url": f"{base_url}static/{row.filename_path.replace('app/asset/', '').replace('\\', '/')}"
            }
            for row in detail_images_result
        ]

        # Dapatkan gambar display
        display_images_query = text("SELECT * FROM get_display_images(:id_serial)")
        display_images_result = db.execute(display_images_query, {"id_serial": id_serial}).fetchall()
        display_images = [
            {
                **dict(row._mapping),
                "file_url": f"{base_url}static/{row.filename_path.replace('app/asset/', '').replace('\\', '/')}"
            }
            for row in display_images_result
        ]


        # Gabungkan data
        product_dict["detail_images"] = detail_images
        product_dict["display_images"] = display_images

        return product_dict

    except ValueError as e:
        logger.warning(f"Produk tidak ditemukan: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Terjadi kesalahan saat mengambil data produk: {str(e)}")
        raise

def remove_old_images(file_paths):
    """
    Menghapus file gambar lama
    """
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"File {path} berhasil dihapus")
        except Exception as e:
            logger.error(f"Gagal menghapus file {path}: {str(e)}")

def update_product(
    db: Session,
    id_serial: str,
    user_id: int, 
    category: str, 
    place_name: str, 
    rating: float, 
    price: float, 
    stock: int, 
    description: str, 
    open_time: str, 
    close_time: str, 
    location: str, 
    latitude: float, 
    longitude: float, 
    kab_kota: str,
    detail_images: List[Dict[str, str]],
    display_images: List[Dict[str, str]],
    old_detail_images: List[str] = None,
    old_display_images: List[str] = None
) -> bool:
    try:
        logger.info(f"Memulai proses update produk dengan ID: {id_serial}")
        
        # Hapus hanya gambar yang ditentukan untuk dihapus
        if old_detail_images:
            remove_old_images(old_detail_images)
        
        if old_display_images:
            remove_old_images(old_display_images)
        
        # Pastikan detail_images dan display_images bukan None sebelum konversi ke JSON
        safe_detail_images = detail_images if detail_images else []
        safe_display_images = display_images if display_images else []
        
        # Panggil prosedur PostgreSQL yang diupdate
        query = text("""
        SELECT update_product_with_image_preservation(
            :id_serial, :user_id, :category, :place_name, :rating, :price, :stock, :description, 
            :open_time, :close_time, :location, :latitude, :longitude, :kab_kota, :detail_images, :display_images
        )
        """)
        
        result = db.execute(
            query,
            {
                "id_serial": id_serial,
                "user_id": user_id,
                "category": category,
                "place_name": place_name,
                "rating": rating,
                "price": price,
                "stock": stock,
                "description": description,
                "open_time": open_time,
                "close_time": close_time,
                "location": location,
                "latitude": latitude,
                "longitude": longitude,
                "kab_kota": kab_kota,
                "detail_images": json.dumps(safe_detail_images),
                "display_images": json.dumps(safe_display_images)
            }
        )
        
        success = result.scalar()
        
        if success:
            db.commit()
            return True
        else:
            db.rollback()
            raise Exception("Gagal memperbarui produk.")
            
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemy error dalam update_product: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error dalam update_product: {str(e)}")
        raise

def get_all_products(db: Session, base_url: str) -> List[Dict[str, Any]]:
    """
    Mendapatkan semua produk
    """
    logger.info("Mengambil semua data produk")
    
    query = text("SELECT * FROM get_all_products()")
    results = db.execute(query).fetchall()

    products = []
    for row in results:
        product_dict = dict(row._mapping)

        # Ambil gambar detail
        detail_query = text("SELECT * FROM get_detail_images(:id_serial)")
        detail_results = db.execute(detail_query, {"id_serial": product_dict["id_serial"]}).fetchall()
        product_dict["detail_images"] = [
            {**dict(img._mapping), "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"}
            for img in detail_results
        ]

        # Ambil gambar display
        display_query = text("SELECT * FROM get_display_images(:id_serial)")
        display_results = db.execute(display_query, {"id_serial": product_dict["id_serial"]}).fetchall()
        product_dict["display_images"] = [
            {**dict(img._mapping), "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"}
            for img in display_results
        ]

        products.append(product_dict)

    return products

def get_products_by_kab_kota(
    db: Session, 
    kab_kota: str, 
    latitude: float, 
    longitude: float, 
    base_url: str
) -> List[Dict[str, Any]]:
    """
    Mendapatkan produk berdasarkan kabupaten/kota dengan informasi jarak dan waktu tempuh
    """
    logger.info(f"Mengambil produk di kabupaten/kota: {kab_kota} dengan posisi pengguna: ({latitude}, {longitude})")

    query = text("SELECT * FROM get_products_by_kab_kota(:kab_kota, :user_lat, :user_long)")
    results = db.execute(query, {
        "kab_kota": kab_kota,
        "user_lat": latitude,
        "user_long": longitude
    }).fetchall()

    products = []
    for row in results:
        product_dict = dict(row._mapping)

        # Ambil gambar detail
        detail_query = text("SELECT * FROM get_detail_images(:id_serial)")
        detail_results = db.execute(detail_query, {"id_serial": product_dict["id_serial"]}).fetchall()
        product_dict["detail_images"] = [
            {**dict(img._mapping), "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"}
            for img in detail_results
        ]

        # Ambil gambar display
        display_query = text("SELECT * FROM get_display_images(:id_serial)")
        display_results = db.execute(display_query, {"id_serial": product_dict["id_serial"]}).fetchall()
        product_dict["display_images"] = [
            {**dict(img._mapping), "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"}
            for img in display_results
        ]

        products.append(product_dict)

    return products

def get_products_by_category(
    db: Session, 
    category: str,
    latitude: float, 
    longitude: float,
    base_url: str,
    sortby: str = None,
    location: str = None) -> List[Dict[str, Any]]:
    """
    Mendapatkan produk berdasarkan kategori dengan informasi Jarak Tempuh dan Waktu Tempuh
    Dengan filter tambahan untuk pengurutan dan lokasi
    """
    logger.info(f"Mengambil produk dengan kategori: {category} dengan posisi pengguna: ({latitude}, {longitude})")
    if sortby:
        logger.info(f"Filter pengurutan: {sortby}")
    if location:
        logger.info(f"Filter lokasi: {location}")

    # Execute stored procedure with parameters
    params = {
        "category": category, 
        "user_lat": latitude,
        "user_long": longitude,
        "p_sortby": sortby,
        "p_location": location
    }
    
    query = text("SELECT * FROM get_products_by_category(:category, :user_lat, :user_long, :p_sortby, :p_location)")
    results = db.execute(query, params).fetchall()

    products = []
    for row in results:
        product_dict = dict(row._mapping)

        # Ambil gambar detail
        detail_query = text("SELECT * FROM get_detail_images(:id_serial)")
        detail_results = db.execute(detail_query, {"id_serial": product_dict["id_serial"]}).fetchall()
        product_dict["detail_images"] = [
            {**dict(img._mapping), "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"}
            for img in detail_results
        ]

        # Ambil gambar display
        display_query = text("SELECT * FROM get_display_images(:id_serial)")
        display_results = db.execute(display_query, {"id_serial": product_dict["id_serial"]}).fetchall()
        product_dict["display_images"] = [
            {**dict(img._mapping), "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"}
            for img in display_results
        ]

        products.append(product_dict)

    return products

def delete_product(db: Session, id_serial: str) -> bool:
    try:
        logger.info(f"Memulai proses penghapusan produk dengan ID: {id_serial}")

        # Ambil data gambar sebelum dihapus
        query_get_images = text("""
            SELECT jsonb_agg(detail_image.filename_path) AS detail_images,
                   jsonb_agg(display_image.filename_path) AS display_images
            FROM products
            LEFT JOIN detail_image ON products.id_serial = detail_image.product_id
            LEFT JOIN display_image ON products.id_serial = display_image.product_id
            WHERE products.id_serial = :id_serial;
        """)

        result = db.execute(query_get_images, {"id_serial": id_serial}).fetchone()
        
        # Gantilah akses ke result dengan indeks numerik
        detail_images = result[0] if result[0] else []  # Akses pertama adalah detail_images
        display_images = result[1] if result[1] else []  # Akses kedua adalah display_images

        # Hapus data dari database
        query_delete = text("SELECT delete_product_by_id_serial(:id_serial)")
        result_delete = db.execute(query_delete, {"id_serial": id_serial})
        
        success = result_delete.scalar()
        
        if success:
            db.commit()
            remove_old_images(detail_images)  # Menggunakan remove_old_images untuk menghapus file
            remove_old_images(display_images)  # Menggunakan remove_old_images untuk menghapus file
            return True
        else:
            db.rollback()
            raise Exception("Gagal menghapus produk.")
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemyError: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Exception: {str(e)}")
        raise

def get_nearby_products(db: Session, user_lat: float, user_long: float, max_distance_km: int, base_url: str) -> List[Dict[str, Any]]:
    """
    Mengambil produk yang berada dalam radius tertentu dari lokasi pengguna.
    """
    try:
        logger.info(f"Mengambil produk dalam radius {max_distance_km} km dari lokasi ({user_lat}, {user_long})")
        
        query = text("SELECT * FROM get_nearby_products(:user_lat, :user_long, :max_distance_km)")
        result = db.execute(query, {"user_lat": user_lat, "user_long": user_long, "max_distance_km": max_distance_km}).fetchall()
        
        products = []
        for row in result:
            product_dict = dict(row._mapping)
            
            # Mengambil gambar detail
            detail_images_query = text("SELECT * FROM get_detail_images(:id_serial)")
            detail_images_result = db.execute(detail_images_query, {"id_serial": product_dict["id_serial"]}).fetchall()
            detail_images = [
                {
                    **dict(img._mapping),
                    "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"
                }
                for img in detail_images_result
            ]
            
            # Mengambil gambar display
            display_images_query = text("SELECT * FROM get_display_images(:id_serial)")
            display_images_result = db.execute(display_images_query, {"id_serial": product_dict["id_serial"]}).fetchall()
            display_images = [
                {
                    **dict(img._mapping),
                    "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"
                }
                for img in display_images_result
            ]
            
            # Menambahkan gambar ke data produk
            product_dict["detail_images"] = detail_images
            product_dict["display_images"] = display_images
            
            products.append(product_dict)
        
        return products
    except Exception as e:
        logger.error(f"Terjadi kesalahan saat mengambil produk terdekat: {str(e)}")
        raise

def get_top_rated_products_by_location(
    db: Session, 
    user_lat: float, 
    user_long: float, 
    category: Optional[str], 
    limit: int, 
    base_url: str
) -> List[Dict[str, Any]]:
    """
    Mengambil produk dengan rating tertinggi berdasarkan lokasi pengguna,
    dengan perhitungan jarak dan estimasi waktu tempuh.
    """
    try:
        logger.info(f"Mengambil {limit} produk terbaik dekat lokasi [{user_lat}, {user_long}] dengan kategori: {category or 'Semua'}")
        
        query = text("SELECT * FROM get_top_rated_products_by_location(:user_lat, :user_long, :category, :limit);")
        result = db.execute(query, {
            "user_lat": user_lat, 
            "user_long": user_long, 
            "category": category, 
            "limit": limit
        }).fetchall()
        
        products = []
        for row in result:
            product_dict = dict(row._mapping)
            
            # Mengambil gambar detail
            detail_images_query = text("SELECT * FROM get_detail_images(:id_serial)")
            detail_images_result = db.execute(detail_images_query, {"id_serial": product_dict["id_serial"]}).fetchall()
            detail_images = [
                {
                    **dict(img._mapping),
                    "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"
                }
                for img in detail_images_result
            ]
            
            # Mengambil gambar display
            display_images_query = text("SELECT * FROM get_display_images(:id_serial)")
            display_images_result = db.execute(display_images_query, {"id_serial": product_dict["id_serial"]}).fetchall()
            display_images = [
                {
                    **dict(img._mapping),
                    "file_url": f"{base_url}static/{img.filename_path.replace('app/asset/', '').replace('\\', '/')}"
                }
                for img in display_images_result
            ]
            
            # Menambahkan gambar ke data produk
            product_dict["detail_images"] = detail_images
            product_dict["display_images"] = display_images
            
            products.append(product_dict)
        
        return products
    except Exception as e:
        logger.error(f"Terjadi kesalahan saat mengambil produk populer berdasarkan lokasi: {str(e)}")
        raise e
