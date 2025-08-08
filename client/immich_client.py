import json
import os
from typing import List, Dict, Optional

import requests


class ImmichClient:
    """
    简化的 Immich API 客户端
    """

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'x-api-key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def get_all_assets(self, asset_type: Optional[str] = None) -> List[Dict]:
        """
        获取所有资产
        asset_type: 'IMAGE', 'VIDEO' 或 None (获取所有)
        """
        search_data = {}
        if asset_type:
            search_data['type'] = asset_type

        response = self.session.post(
            f"{self.base_url}/api/search/metadata",
            data=json.dumps(search_data)
        )
        response.raise_for_status()

        result = response.json()
        return result.get('assets', {}).get('items', [])

    def get_asset_info(self, asset_id: str) -> Dict:
        """获取单个资产的详细信息"""
        response = self.session.get(f"{self.base_url}/api/assets/{asset_id}")
        response.raise_for_status()
        return response.json()

    def download_asset_thumbnail(self, asset_id: str, save_path: str) -> str:
        """下载资产缩略图"""
        url = f"{self.base_url}/api/assets/{asset_id}/thumbnail"
        headers = {'x-api-key': self.api_key}

        response = self.session.get(url, headers=headers, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return save_path

    def download_asset_original(self, asset_id: str, save_path: str) -> str:
        """下载资产原始文件"""
        url = f"{self.base_url}/api/assets/{asset_id}/original"
        headers = {'x-api-key': self.api_key}

        response = self.session.get(url, headers=headers, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return save_path


def main():
    # 创建 Immich 客户端
    client = ImmichClient(
        base_url='http://localhost:2283',
        api_key='cXoes49a109rpmEFDmxY4RG4ObY2aXBvVeDkhTHXE'  # 你的实际 API key
    )

    # 测试连接
    try:
        image = client.get_all_assets(asset_type='IMAGE')
        video = client.get_all_assets(asset_type='VIDEO')
        print(f"连接成功！找到 {len(image)} 张图片")
        print(f"连接成功！找到 {len(video)} 个视频")
    except Exception as e:
        print(f"连接失败: {e}")
        return


if __name__ == "__main__":
    main()
