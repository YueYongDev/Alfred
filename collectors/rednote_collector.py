import json
import os
import tempfile
from datetime import datetime
from typing import Optional, Dict

from tqdm import tqdm

from client.immich_client import ImmichClient
from summarizer.summarizer import summarize_photo_file


def analyze_immich_photos(client: ImmichClient, output_file: str = "immich_analysis.json"):
    """
    分析 Immich 中的所有照片并保存结果到 JSON 文件
    """
    try:
        # 获取所有图片
        photos = client.get_all_assets(asset_type='IMAGE')
        print(f"✅ 获取 Immich 中的图片列表成功！共 {len(photos)} 张照片")

    except Exception as e:
        print(f"❌ 获取 Immich 资产失败: {e}")
        return

    results = []
    count_analyzed = 0

    for asset_data in tqdm(photos, desc="分析 Immich 照片", unit="photo"):
        try:
            asset_id = asset_data['id']
            original_filename = asset_data.get('originalFileName', '')
            original_path = asset_data.get('originalPath', '')

            # 分析照片
            analysis_result = _analyze_single_photo(client, asset_id)

            if analysis_result:
                # 组合结果
                photo_result = {
                    'asset_id': asset_id,
                    'filename': original_filename,
                    'path': original_path,
                    'file_created_at': asset_data.get('fileCreatedAt'),
                    'ai_summary': analysis_result['summary'],
                    'ai_tags': analysis_result['tags'],
                    'analyzed_at': datetime.now().isoformat()
                }

                # 获取详细信息（EXIF等）
                try:
                    asset_info = client.get_asset_info(asset_id)
                    exif_info = asset_info.get('exifInfo', {})
                    if exif_info:
                        photo_result['camera_make'] = exif_info.get('make')
                        photo_result['camera_model'] = exif_info.get('model')
                        photo_result['gps_lat'] = exif_info.get('latitude')
                        photo_result['gps_lng'] = exif_info.get('longitude')
                except Exception as e:
                    print(f"[⚠️] 获取 EXIF 信息失败: {asset_id} - {e}")

                results.append(photo_result)
                count_analyzed += 1

                # 实时显示分析结果
                print(f"📷 {original_filename}")
                print(f"   摘要: {analysis_result['summary'][:100]}...")
                print(f"   标签: {', '.join(analysis_result['tags'][:5])}")
                print()

        except Exception as e:
            print(f"[⚠️] 分析照片失败: {asset_data.get('id', 'unknown')} - {e}")
            continue

    # 保存结果到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 分析完成！共分析 {count_analyzed} 张照片")
    print(f"📄 结果已保存到: {output_file}")

    return results


def _analyze_single_photo(client: ImmichClient, asset_id: str) -> Optional[Dict]:
    """
    分析单张照片
    """
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 下载缩略图进行分析
            client.download_asset_thumbnail(asset_id, tmp_path)

            # 调用你的 AI 分析函数
            ai_summary, ai_tags = summarize_photo_file(tmp_path)

            return {
                'summary': ai_summary,
                'tags': ai_tags
            }

        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        print(f"[⚠️] 分析失败: {asset_id} - {e}")
        return None


def main():
    # 创建 Immich 客户端
    client = ImmichClient(
        base_url='http://localhost:2283',
        api_key='cXoes49a109rpmEFDmxY4RG4ObY2aXBvVeDkhTHXE'  # 你的实际 API key
    )

    # 测试连接
    try:
        assets = client.get_all_assets(asset_type='IMAGE')
        print(f"连接成功！找到 {len(assets)} 张图片")
    except Exception as e:
        print(f"连接失败: {e}")
        return

    # 分析所有照片
    results = analyze_immich_photos(client, "immich_analysis.json")
    

if __name__ == "__main__":
    main()
