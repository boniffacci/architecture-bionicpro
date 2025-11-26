import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

interface ReportItem {
  report_date: string;
  client_name: string;
  avg_battery_level: number;
  total_steps: number;
  max_muscle_voltage: number;
  errors_count: number;
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reports, setReports] = useState<ReportItem[]>([]);

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Запрос к нашему новому API
      const response = await fetch('http://localhost:8000/reports', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${keycloak.token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      setReports(data);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
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
    <div className="flex flex-col items-center min-h-screen bg-gray-100 p-8">
      <div className="w-full max-w-4xl bg-white rounded-lg shadow-md p-8">
        <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold">Usage Reports for {keycloak.tokenParsed?.preferred_username}</h1>
            <button onClick={() => keycloak.logout()} className="text-sm text-red-500 underline">Logout</button>
        </div>

        <button
          onClick={downloadReport}
          disabled={loading}
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 mb-6 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Loading Data...' : 'Get My Reports'}
        </button>

        {error && (
          <div className="mb-4 p-4 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        {reports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto border-collapse border border-gray-200">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border p-2">Date</th>
                  <th className="border p-2">Client</th>
                  <th className="border p-2">Avg Battery</th>
                  <th className="border p-2">Steps</th>
                  <th className="border p-2">Max Voltage</th>
                  <th className="border p-2">Errors</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r, idx) => (
                  <tr key={idx} className="text-center">
                    <td className="border p-2">{r.report_date}</td>
                    <td className="border p-2">{r.client_name}</td>
                    <td className="border p-2">{r.avg_battery_level.toFixed(1)}%</td>
                    <td className="border p-2">{r.total_steps}</td>
                    <td className="border p-2">{r.max_muscle_voltage.toFixed(2)}</td>
                    <td className="border p-2 text-red-500 font-bold">{r.errors_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
           <p className="text-gray-500">No reports loaded yet. Click the button above.</p>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
