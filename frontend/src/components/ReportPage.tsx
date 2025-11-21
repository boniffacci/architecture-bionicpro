import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<any[]>([]);

  const fetchReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setReportData(data);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) return <div>Loading...</div>;

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
    <div className="p-8 bg-white rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>

      <button
        onClick={fetchReport}
        disabled={loading}
        className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
          loading ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        {loading ? 'Loading...' : 'Load Report'}
      </button>

      {error && (
        <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
          {error}
        </div>
      )}

      {reportData.length > 0 && (
        <table className="mt-6 w-full border-collapse border border-gray-300">
          <thead>
            <tr className="bg-gray-200">
              <th className="border px-2 py-1">Customer ID</th>
              <th className="border px-2 py-1">Name</th>
              <th className="border px-2 py-1">Email</th>
              <th className="border px-2 py-1">Country</th>
              <th className="border px-2 py-1">Prosthesis Type</th>
              <th className="border px-2 py-1">Muscle Group</th>
              <th className="border px-2 py-1">Total Signals</th>
              <th className="border px-2 py-1">Avg Frequency</th>
              <th className="border px-2 py-1">Avg Duration</th>
              <th className="border px-2 py-1">Avg Amplitude</th>
              <th className="border px-2 py-1">Last Signal Time</th>
            </tr>
          </thead>
          <tbody>
            {reportData.map((row, idx) => (
              <tr key={idx}>
                <td className="border px-2 py-1">{row.customer_id}</td>
                <td className="border px-2 py-1">{row.name}</td>
                <td className="border px-2 py-1">{row.email}</td>
                <td className="border px-2 py-1">{row.country}</td>
                <td className="border px-2 py-1">{row.prosthesis_type}</td>
                <td className="border px-2 py-1">{row.muscle_group}</td>
                <td className="border px-2 py-1">{row.total_signals}</td>
                <td className="border px-2 py-1">{row.avg_frequency}</td>
                <td className="border px-2 py-1">{row.avg_duration}</td>
                <td className="border px-2 py-1">{row.avg_amplitude}</td>
                <td className="border px-2 py-1">{row.last_signal_time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default ReportPage;