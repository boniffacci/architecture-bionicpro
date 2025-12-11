from flask import jsonify, g

class ReportHandler:
    def __init__(self, report_service):
        self.report_service = report_service
    
    def get_reports(self):
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        try:
            report = self.report_service.get_user_report(user_id)
            return jsonify(report.to_dict()), 200
        except Exception as e:
            print(f"Error getting report: {e}")
            return jsonify({"error": "Failed to get report"}), 500
    
    def generate_reports(self):
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            return jsonify({"error": "User ID not found"}), 400
        
        try:
            url = self.report_service.generate_user_report(user_id)
            if not url:
                return jsonify({"error": "Данные для отчета пока не найдены"}), 404
            return jsonify({"url": url}), 200
        except Exception as e:
            print(f"Error generating report: {e}")
            return jsonify({"error": "Failed to generate report"}), 500