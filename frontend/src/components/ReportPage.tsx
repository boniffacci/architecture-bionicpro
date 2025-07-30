import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);

  const downloadReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const reportData = await response.json();
      
      // Create and download JSON file
      const dataStr = JSON.stringify(reportData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      
      const url = window.URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `prosthetic-report-${reportData.username}-${new Date().toISOString().split('T')[0]}.json`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      window.URL.revokeObjectURL(url);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Load user profile on component mount
  React.useEffect(() => {
    const loadUserProfile = async () => {
      if (keycloak.authenticated && keycloak.token) {
        try {
          const response = await fetch(`${process.env.REACT_APP_API_URL}/user/profile`, {
            headers: {
              'Authorization': `Bearer ${keycloak.token}`,
              'Content-Type': 'application/json'
            }
          });
          
          if (response.ok) {
            const profile = await response.json();
            setUserProfile(profile);
          }
        } catch (err) {
          console.error('Failed to load user profile:', err);
        }
      }
    };

    loadUserProfile();
  }, [keycloak.authenticated, keycloak.token]);

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
      <div className="p-8 bg-white rounded-lg shadow-md max-w-md w-full">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Usage Reports</h1>
          <button
            onClick={() => keycloak.logout()}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Logout
          </button>
        </div>
        
        {userProfile && (
          <div className="mb-6 p-4 bg-gray-50 rounded">
            <p className="text-sm text-gray-600">Welcome, <strong>{userProfile.username}</strong></p>
            <p className="text-xs text-gray-500">{userProfile.email}</p>
            <div className="mt-2">
              <span className={`inline-block px-2 py-1 text-xs rounded ${
                userProfile.has_report_access 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {userProfile.has_report_access ? 'Report Access: Enabled' : 'Report Access: Disabled'}
              </span>
            </div>
          </div>
        )}
        
        <button
          onClick={downloadReport}
          disabled={loading || (userProfile && !userProfile.has_report_access)}
          className={`w-full px-4 py-3 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            (loading || (userProfile && !userProfile.has_report_access)) ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Generating Report...' : 'Download Prosthetic Usage Report'}
        </button>

        {userProfile && !userProfile.has_report_access && (
          <div className="mt-4 p-4 bg-yellow-100 text-yellow-700 rounded text-sm">
            <strong>Access Restricted:</strong> You need the 'prothetic_user' role to download reports.
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded text-sm">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;