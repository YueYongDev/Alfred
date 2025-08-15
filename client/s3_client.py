import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    endpoint_url="http://192.168.100.132:9702",
    aws_access_key_id="yueyong",
    aws_secret_access_key="liang19991108",
    region_name="us-east-1",  # 可留可加
    config=Config(s3={"addressing_style": "path"})
)
print(s3.list_buckets())           # 顶层目录（photos、videos）会作为 buckets 返回
# print(s3.list_objects_v2(Bucket="photos").get("Contents", []))

url = s3.generate_presigned_url(
    ClientMethod="get_object",
    Params={"Bucket": "photos", "Key": "2024/01/15/133918.HEIC"},
    ExpiresIn=3600  # 有效期，秒
)
print("预签名 URL:", url)