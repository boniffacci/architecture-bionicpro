import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reports, setReports] = useState<any[] | null>(null);

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      await keycloak.updateToken(10)

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      console.log(await keycloak.loadUserInfo())

      if (!response.ok) {
        let message = `Error ${response.status}`;
        try {
          const data = await response.json();
          message += `: ${data.detail || JSON.stringify(data)}`;
        } catch {
          const text = await response.text();
          message += `: ${text}`;
        }
        throw new Error(message);
      }

      const data = await response.json();
      setReports(data.reports || []);

      
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
    <div className="flex flex-col min-h-screen bg-gray-100">
      <div className="p-8 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>
        
        <button
          onClick={downloadReport}
          disabled={loading}
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Generating Report...' : 'Download Report'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
            {error}
          </div>
        )}

        {reports && (
          <table className="mt-6 table-auto border border-gray-300">
            <thead className="bg-gray-200">
              <tr>
                <th className="border px-4 py-2">user_name</th>
                <th className="border px-4 py-2">email</th>
                <th className="border px-4 py-2">prosthesis_model</th>
                <th className="border px-4 py-2">prosthesis_serial</th>
                <th className="border px-4 py-2">installation_date</th>
                <th className="border px-4 py-2">total_usage_minutes</th>
                <th className="border px-4 py-2">usage_date</th>
                <th className="border px-4 py-2">avg_battery_level</th>
                <th className="border px-4 py-2">avg_max_force</th>
                <th className="border px-4 py-2">last_active</th>
                <th className="border px-4 py-2">total_error_count</th>
                <th className="border px-4 py-2">total_sessions</th>
                <th className="border px-4 py-2">updated_at</th>
                <th className="border px-4 py-2">created_at</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r, i) => (
                <tr key={i}>
                  <td className="border px-4 py-2">{r.user_name}</td>
                  <td className="border px-4 py-2">{r.email}</td>
                  <td className="border px-4 py-2">{r.prosthesis_model}</td>
                  <td className="border px-4 py-2">{r.prosthesis_serial}</td>
                  <td className="border px-4 py-2">{r.installation_date}</td>
                  <td className="border px-4 py-2">{r.total_usage_minutes}</td>
                  <td className="border px-4 py-2">{r.usage_date}</td>
                  <td className="border px-4 py-2">{r.avg_battery_level}</td>
                  <td className="border px-4 py-2">{r.avg_max_force}</td>
                  <td className="border px-4 py-2">{r.last_active}</td>
                  <td className="border px-4 py-2">{r.total_error_count}</td>
                  <td className="border px-4 py-2">{r.total_sessions}</td>
                  <td className="border px-4 py-2">{r.updated_at}</td>
                  <td className="border px-4 py-2">{r.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}  

        <div className="flex justify-between items-center mb-4 mt-4">
          <button
            onClick={() => keycloak.logout({ redirectUri: window.location.origin })}
            className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Logout
          </button>
        </div>


      </div>
    </div>
  );
};

export default ReportPage;