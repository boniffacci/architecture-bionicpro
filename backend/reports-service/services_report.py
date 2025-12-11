from models_report import UserReport

class ReportService:
    def __init__(self, clickhouse_client, s3_client, config):
        self.clickhouse = clickhouse_client
        self.s3 = s3_client
        self.config = config
    
    def get_user_report(self, user_id):
        if self.s3.report_exists(user_id):
            report = self.s3.get_report(user_id)
            if report:
                return report
        
        report = self.clickhouse.get_user_report(user_id)
        if report.has_data:
            self.s3.store_report(user_id, report)
        return report
    
    def generate_user_report(self, user_id):
        if self.s3.report_exists(user_id):
            return self.s3.generate_cdn_link(user_id, self.config.cdn.host)
        
        report = self.clickhouse.get_user_report(user_id)
        if not report.has_data:
            return None
        
        if self.s3.store_report(user_id, report):
            return self.s3.generate_cdn_link(user_id, self.config.cdn.host)
        
        return None