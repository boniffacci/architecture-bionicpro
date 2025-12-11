import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ClickHouseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str

@dataclass
class S3Config:
    endpoint: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: str
    use_ssl: bool

@dataclass
class CDNConfig:
    host: str

@dataclass
class Config:
    clickhouse: ClickHouseConfig
    s3: S3Config
    cdn: CDNConfig

def load_config():
    return Config(
        clickhouse=ClickHouseConfig(
            host=os.getenv("CLICKHOUSE_HOST", "olap_db"),
            port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
            database=os.getenv("CLICKHOUSE_DATABASE", "default"),
            username=os.getenv("CLICKHOUSE_USERNAME", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        ),
        s3=S3Config(
            endpoint=os.getenv("S3_ENDPOINT", "minio:9000"),
            access_key_id=os.getenv("S3_ACCESS_KEY_ID", "minio_user"),
            secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", "minio_password"),
            bucket_name=os.getenv("S3_BUCKET_NAME", "reports"),
            region=os.getenv("S3_REGION", "us-east-1"),
            use_ssl=os.getenv("S3_USE_SSL", "false").lower() == "true",
        ),
        cdn=CDNConfig(
            host=os.getenv("CDN_HOST", "localhost:8888")
        )
    )