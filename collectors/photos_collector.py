import os
import pathlib
from datetime import datetime
import tempfile
import time

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from sqlalchemy.orm import Session
from sqlalchemy import or_
from tqdm import tqdm

import pillow_heif
import exifread
import rawpy
import imageio

from db.models import Photo  # 假设你已定义好 Photo 模型
from summarization_engine.summarizer import summarize_photo_file

pillow_heif.register_heif_opener()


def extract_exif_info(file_path: str):
    """优先用 exifread 解析 EXIF 信息，兼容 JPEG/HEIC，兜底用 PIL"""
    def exifread_gps(tags):
        def get_tag(name):
            return tags.get(name)
        def to_deg(val):
            # exifread 返回 Ratio 对象
            if val and hasattr(val, '__iter__') and len(val) == 3:
                d, m, s = val
                return float(d) + float(m) / 60 + float(s) / 3600
            return None
        lat = get_tag('GPS GPSLatitude')
        lat_ref = get_tag('GPS GPSLatitudeRef')
        lng = get_tag('GPS GPSLongitude')
        lng_ref = get_tag('GPS GPSLongitudeRef')
        gps_lat = gps_lng = None
        if lat and lat_ref:
            lat_deg = to_deg(lat.values)
            if lat_deg is not None:
                gps_lat = lat_deg if lat_ref.values[0] in ['N', b'N'] else -lat_deg
        if lng and lng_ref:
            lng_deg = to_deg(lng.values)
            if lng_deg is not None:
                gps_lng = lng_deg if lng_ref.values[0] in ['E', b'E'] else -lng_deg
        return gps_lat, gps_lng
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            camera_model = tags.get('Image Model')
            gps_lat, gps_lng = exifread_gps(tags)
            return str(camera_model) if camera_model else None, gps_lat, gps_lng
    except Exception:
        pass
    # 兜底用 PIL
    try:
        img = Image.open(file_path)
        exif_data = img.getexif()
        if not exif_data:
            return None, None, None
        exif = {TAGS.get(k): v for k, v in exif_data.items() if k in TAGS}
        camera_model = exif.get("Model")
        gps_info = exif.get("GPSInfo")
        gps_lat = gps_lng = None
        if gps_info:
            gps = {
                GPSTAGS.get(t): gps_info[t]
                for t in gps_info
                if t in GPSTAGS
            }
            def to_deg(val):
                if isinstance(val, (list, tuple)) and len(val) == 3:
                    def frac(x):
                        if isinstance(x, (list, tuple)) and len(x) == 2:
                            return x[0] / x[1]
                        try:
                            return float(x)
                        except Exception:
                            return 0.0
                    d, m, s = val
                    return frac(d) + frac(m) / 60 + frac(s) / 3600
                try:
                    return float(val)
                except Exception:
                    return None
            lat = gps.get("GPSLatitude")
            lng = gps.get("GPSLongitude")
            lat_ref = gps.get("GPSLatitudeRef")
            lng_ref = gps.get("GPSLongitudeRef")
            if lat is not None and lat_ref:
                lat_deg = to_deg(lat)
                if lat_deg is not None:
                    gps_lat = lat_deg if lat_ref == "N" else -lat_deg
            if lng is not None and lng_ref:
                lng_deg = to_deg(lng)
                if lng_deg is not None:
                    gps_lng = lng_deg if lng_ref == "E" else -lng_deg
        return camera_model, gps_lat, gps_lng
    except Exception as e:
        print(f"[⚠️] 解析 EXIF 失败: {file_path} - {e}")
        return None, None, None


def import_photo_from_directory(photo_dir: str, session: Session):
    # 支持常见RAW格式
    image_exts = [
        ".jpg", ".jpeg", ".png", ".webp", ".heic",
        ".cr2", ".nef", ".arw", ".dng", ".raf", ".rw2", ".orf", ".sr2", ".pef", ".cr3", ".raw"
    ]
    count_insert = 0
    count_update = 0
    photo_files = []
    for root, _, files in os.walk(photo_dir):
        for file in files:
            if pathlib.Path(file).suffix.lower() in image_exts:
                photo_files.append(os.path.join(root, file))
    use_tqdm = len(photo_files) > 10000
    iterator = tqdm(photo_files, desc="导入照片", unit="file") if use_tqdm else photo_files
    for file_path in iterator:
        try:
            stat = os.stat(file_path)
            taken_at = datetime.fromtimestamp(stat.st_mtime)
            camera_model, gps_lat, gps_lng = extract_exif_info(file_path)
            ext = pathlib.Path(file_path).suffix.lower()
            # 不再跳过任何图片，所有图片都插入/更新数据库
            existing_photo = session.query(Photo).filter_by(file_path=file_path).first()
            if existing_photo:
                existing_photo.caption = ""
                existing_photo.taken_at = taken_at
                existing_photo.location = None
                existing_photo.camera_model = camera_model
                existing_photo.gps_lat = gps_lat
                existing_photo.gps_lng = gps_lng
                existing_photo.tags = []
                count_update += 1
            else:
                photo = Photo(
                    file_path=file_path,
                    caption="",
                    taken_at=taken_at,
                    location=None,  # 如果你未来解析城市，可扩展此字段
                    camera_model=camera_model,
                    gps_lat=gps_lat,
                    gps_lng=gps_lng,
                    tags=[],
                )
                session.add(photo)
                count_insert += 1
        except Exception as e:
            ext = pathlib.Path(file_path).suffix.lower()
            if ext != ".png":
                print(f"[⚠️] 导入图片失败: {file_path} - {e}")
    session.commit()
    print(f"✅ 新增 {count_insert} 张照片，更新 {count_update} 张照片")


def summarize_photos(session: Session):
    photos = session.query(Photo).filter(or_(Photo.summary == None, Photo.summary == "", Photo.tags == None)).all()
    count = 0
    if not photos:
        print("没有需要总结的 Photo")
        return
    start_time = time.time()
    RAW_EXTS = [".cr2", ".nef", ".arw", ".dng", ".raf", ".rw2", ".orf", ".sr2", ".pef", ".cr3", ".raw"]
    for photo in tqdm(photos, desc="总结照片", unit="photo"):
        if not photo.file_path:
            continue
        try:
            file_path = photo.file_path
            ext = pathlib.Path(file_path).suffix.lower()
            if ext in [".heic", ".heif"]:
                # HEIC/HEIF 转 JPG
                with Image.open(file_path) as im:
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                        im.convert("RGB").save(tmp.name, format="JPEG")
                        tmp_jpg_path = tmp.name
                summary, tags = summarize_photo_file(tmp_jpg_path)
                os.remove(tmp_jpg_path)
            elif ext in RAW_EXTS:
                # RAW 转 JPG
                with rawpy.imread(file_path) as raw:
                    rgb = raw.postprocess()
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                        imageio.imsave(tmp.name, rgb)
                        tmp_jpg_path = tmp.name
                summary, tags = summarize_photo_file(tmp_jpg_path)
                os.remove(tmp_jpg_path)
            else:
                summary, tags = summarize_photo_file(file_path)
            photo.summary = summary
            photo.tags = tags
            photo.last_summarized_at = datetime.now()
            count += 1
        except Exception as e:
            print(f"[⚠️] 图片分析失败: {photo.file_path} - {e}")
    session.commit()
    elapsed = time.time() - start_time
    print(f"✅ Photo 总结完成，共处理 {count} 条，用时 {elapsed:.2f} 秒")
