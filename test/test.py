import tempfile
import os
from summarizer.summarizer import analyze_photo  # 你已有的分析函数
from client.photoprism_client import Client  # 你手写的 REST 客户端

def analyze_photo_from_photoprism(uid: str, client: Client) -> dict:
    """
    下载 PhotoPrism 中指定 uid 的原图，分析后返回 AI 结果。
    自动使用临时文件，分析完即清除。
    """
    print(f"Downloading photo {uid}...")
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
        client.download_photo(uid, tmp_path)
    print(f"Analyzing photo {uid}...")
    try:
        return analyze_photo(tmp_path)
    finally:
        os.remove(tmp_path)

if __name__ == "__main__":
    client = Client(username="yueyong", password="Liang19991108@", domain="http://dx4800-25d3.local:2342")

    photos = client.get_photos()
    print("✅ 获取 PhotoPrism 中的图片列表成功！")
    print("图片列表长度：", len(photos))
    photo = photos[0]
    print(photo)
    uid = photo["UID"]

    result = analyze_photo_from_photoprism(uid, client)
    print("🧠 分析结果：", result)