import React, { useState } from "react";
import { useKeycloak } from "@react-keycloak/web";

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<any>(null);

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError("Not authenticated");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setReportData(null);

      const response = await fetch(
        `${process.env.REACT_APP_API_URL || "http://localhost:8000"}/reports`,
        {
          headers: {
            Authorization: `Bearer ${keycloak.token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.error || `HTTP error! status: ${response.status}`
        );
      }

      const data = await response.json();
      setReportData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return <div>Loading...</div>;
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <button
          onClick={() => keycloak.login()}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

        <button
          onClick={downloadReport}
          disabled={loading}
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? "opacity-50 cursor-not-allowed" : ""
          }`}
        >
          {loading ? "Generating Report..." : "Download Report"}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        {reportData?.data?.length === 0 && (
          <p>
            <strong>Нет отчета для пользователя</strong>
          </p>
        )}

        {reportData && reportData.data && reportData.data.length > 0 && (
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded">
            <h3 className="text-lg font-semibold text-green-800 mb-3">
              Report Generated Successfully!
            </h3>
            <div className="space-y-2 text-sm">
              {reportData.data.map((report: any, index: number) => (
                <div
                  key={report.report_id || index}
                  className="border-b border-green-200 pb-2 mb-2"
                >
                  <p>
                    <strong>Customer ID:</strong> {report.customer_id}
                  </p>
                  <p>
                    <strong>Customer Name:</strong> {report.customer_name}
                  </p>
                  <p>
                    <strong>Prosthesis Type:</strong> {report.prosthesis_type}
                  </p>
                  <p>
                    <strong>Total Sessions:</strong> {report.total_sessions}
                  </p>
                  <p>
                    <strong>Average Muscle Signal:</strong>{" "}
                    {report.avg_muscle_signal}
                  </p>
                  <p>
                    <strong>Max Muscle Signal:</strong>{" "}
                    {report.max_muscle_signal}
                  </p>
                  <p>
                    <strong>Min Muscle Signal:</strong>{" "}
                    {report.min_muscle_signal}
                  </p>
                  <p>
                    <strong>Average Position:</strong>{" "}
                    {report.avg_position || "N/A"}
                  </p>
                  <p>
                    <strong>Total Activities:</strong> {report.total_activities}
                  </p>
                  <p>
                    <strong>Most Common Activity:</strong>{" "}
                    {report.most_common_activity}
                  </p>
                  <p>
                    <strong>Report Date:</strong>{" "}
                    {new Date(report.report_date).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
