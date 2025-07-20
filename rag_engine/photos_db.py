import sqlite3
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
import pillow_heif

pillow_heif.register_heif_opener()

DB_PATH = "storage/photos_metadata.db"
PHOTOS_DIR = "data/photos"

# --- Database Management ---

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化或升级数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 检查表是否存在及结构是否最新
    cursor.execute("PRAGMA table_info(photos)")
    columns = [row['name'] for row in cursor.fetchall()]
    
    required_columns = [
        'file_path', 'file_name', 'file_type', 'file_size', 'creation_date', 
        'last_modified', 'indexed', 'camera_model', 'f_number', 'exposure_time', 
        'iso', 'latitude', 'longitude', 'ai_description', 'ai_tags'
    ]

    if 'photos' in [row['name'] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")] and all(col in columns for col in required_columns):
        conn.close()
        return

    print("▶️ 数据库表结构需要初始化或更新...")
    # 为了简单起见，我们直接重建表。在生产环境中，可能需要更复杂的迁移策略。
    cursor.execute("DROP TABLE IF EXISTS photos")
    cursor.execute("""
    CREATE TABLE photos (
        file_path TEXT PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        creation_date TEXT,
        last_modified REAL NOT NULL,
        indexed INTEGER DEFAULT 0,
        camera_model TEXT,
        f_number REAL,
        exposure_time TEXT,
        iso INTEGER,
        latitude REAL,
        longitude REAL,
        ai_description TEXT,
        ai_tags TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("✅ 数据库表结构初始化/更新完成。")

# --- EXIF Data Extraction ---

def _dms_to_decimal(dms, ref):
    """将DMS（度分秒）格式的GPS坐标转换为十进制度数"""
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    decimal = degrees + minutes + seconds
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

def extract_exif_data(image_path):
    """从图片中提取详细的EXIF元数据"""
    exif_data = {}
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        if not exif:
            return exif_data

        for tag, value in exif.items():
            tag_name = TAGS.get(tag, tag)
            exif_data[tag_name] = value

        # 解析GPS信息
        if 'GPSInfo' in exif_data:
            gps_info = {}
            for key in exif_data['GPSInfo']:
                decode = GPSTAGS.get(key, key)
                gps_info[decode] = exif_data['GPSInfo'][key]
            
            if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                exif_data['latitude'] = _dms_to_decimal(gps_info['GPSLatitude'], gps_info.get('GPSLatitudeRef'))
                exif_data['longitude'] = _dms_to_decimal(gps_info['GPSLongitude'], gps_info.get('GPSLongitudeRef'))

    except Exception:
        return {} # 忽略无法解析的图片

    # 格式化并返回我们需要的数据
    creation_date = exif_data.get('DateTimeOriginal')
    if creation_date:
        try:
            creation_date = datetime.strptime(creation_date, '%Y:%m:%d %H:%M:%S').isoformat()
        except (ValueError, TypeError):
            creation_date = None

    return {
        'creation_date': creation_date,
        'camera_model': exif_data.get('Model', '').strip(),
        'f_number': float(exif_data.get('FNumber')) if exif_data.get('FNumber') else None,
        'exposure_time': str(exif_data.get('ExposureTime', '')),
        'iso': exif_data.get('ISOSpeedRatings'),
        'latitude': exif_data.get('latitude'),
        'longitude': exif_data.get('longitude'),
    }

# --- Core Functions ---

def scan_and_update_photos():
    """扫描照片目录，并更新数据库"""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    print(f"▶️ 开始扫描目录: {PHOTOS_DIR}")
    for root, _, files in os.walk(PHOTOS_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.heic')):
                file_path = os.path.join(root, file)
                try:
                    last_modified_time = os.path.getmtime(file_path)

                    cursor.execute("SELECT last_modified FROM photos WHERE file_path = ?", (file_path,))
                    result = cursor.fetchone()

                    if result and result['last_modified'] >= last_modified_time:
                        continue

                    print(f"  - 发现新文件或已更新: {file}")
                    file_size = os.path.getsize(file_path)
                    file_type = os.path.splitext(file)[1].upper().replace('.', '')
                    
                    exif = extract_exif_data(file_path)

                    # 准备插入或替换的数据
                    photo_data = {
                        'file_path': file_path,
                        'file_name': file,
                        'file_type': file_type,
                        'file_size': file_size,
                        'last_modified': last_modified_time,
                        'indexed': 0, # 每次更新都重置为未索引
                        **exif
                    }
                    
                    columns = ', '.join(photo_data.keys())
                    placeholders = ', '.join('?' for _ in photo_data)
                    sql = f"INSERT OR REPLACE INTO photos ({columns}) VALUES ({placeholders})"
                    cursor.execute(sql, tuple(photo_data.values()))
                    
                except Exception as e:
                    print(f"  - 处理文件失败 {file_path}: {e}")

    conn.commit()
    conn.close()
    print("✅ 照片信息扫描和更新完成。")

def get_unindexed_photos():
    """获取所有未被索引的照片"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM photos WHERE indexed = 0")
    photos = cursor.fetchall()
    conn.close()
    return [dict(photo) for photo in photos]

def mark_photo_as_indexed(file_path):
    """将指定照片标记为已索引"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE photos SET indexed = 1 WHERE file_path = ?", (file_path,))
    conn.commit()
    conn.close()

# --- Main Execution ---

if __name__ == '__main__':
    scan_and_update_photos()
    unindexed_photos = get_unindexed_photos()
    print(f"\n发现 {len(unindexed_photos)} 张未索引的照片:")
    for p in unindexed_photos:
        print(f"  - {p['file_path']} (相机: {p['camera_model'] or 'N/A'}, 地点: {('%.4f, %.4f' % (p['latitude'], p['longitude'])) if p['latitude'] and p['longitude'] else 'N/A'})")