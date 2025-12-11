import json
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from models_report import UserReport

class S3Client:
    def __init__(self, endpoint, access_key_id, secret_access_key, 
                 bucket_name, region="us-east-1", use_ssl=False):
        if endpoint.startswith('http://'):
            endpoint = endpoint[7:]
        elif endpoint.startswith('https://'):
            endpoint = endpoint[8:]
        
        self.client = Minio(
            endpoint,
            access_key=access_key_id,
            secret_key=secret_access_key,
            secure=use_ssl
        )
        self.bucket_name = bucket_name
        
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except Exception as e:
            print(f"Error creating bucket: {e}")
    
    def report_exists(self, user_id):
        file_name = f"report_{user_id}.json"
        try:
            self.client.stat_object(self.bucket_name, file_name)
            return True
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return False
            raise
    
    def get_report(self, user_id):
        file_name = f"report_{user_id}.json"
        try:
            response = self.client.get_object(self.bucket_name, file_name)
            data = json.loads(response.read().decode('utf-8'))
            response.close()
            response.release_conn()
            return UserReport.from_dict(data)
        except S3Error as e:
            if e.code == 'NoSuchKey':
                return None
            raise
    
    def store_report(self, user_id, report):
        file_name = f"report_{user_id}.json"
        try:
            report_data = report.to_dict()
            json_data = json.dumps(report_data, indent=2, ensure_ascii=False)
            self.client.put_object(
                self.bucket_name,
                file_name,
                data=BytesIO(json_data.encode('utf-8')),
                length=len(json_data),
                content_type='application/json'
            )
            return True
        except Exception as e:
            print(f"Error storing report: {e}")
            return False
    
    def generate_cdn_link(self, user_id, cdn_host):
        file_name = f"report_{user_id}.json"
        return f"http://{cdn_host}/{self.bucket_name}/{file_name}"