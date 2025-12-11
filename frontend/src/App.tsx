import React, { useState, useEffect } from 'react';

const BFF_URL = 'http://localhost:5001';

interface Report {
  user_id: number;
  username: string;
  email: string;
  total_sessions: number;
  total_signals: number;
  total_usage_time: number;
  average_session_time: number;
  muscle_groups: string;
  average_accuracy: number;
  last_activity: string;
  report_generated_at: string;
  has_data: boolean;
  message?: string;
}

const App: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<{ name: string; crm_user_id?: number } | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await fetch(`${BFF_URL}/api/auth/status`, {
        credentials: 'include'
      });
      const data = await res.json();
      
      if (data.isAuthenticated) {
        setAuthenticated(true);
        setUser({
          name: data.name || 'User',
          crm_user_id: data.crm_user_id
        });
      } else {
        setAuthenticated(false);
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      setAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const loadReport = async () => {
    if (!user?.crm_user_id) return;
    
    setReportLoading(true);
    try {
      const res = await fetch(`${BFF_URL}/api/reports`, {
        credentials: 'include'
      });
      
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      } else if (res.status === 404) {
        setReport(null);
      }
    } catch (error) {
      console.error('Failed to load report:', error);
      setReport(null);
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => {
    if (authenticated && user?.crm_user_id) {
      loadReport();
    }
  }, [authenticated, user?.crm_user_id]);

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#f9fafb'
      }}>
        <div>Checking authorization...</div>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#f9fafb',
        padding: '20px'
      }}>
        <h1 style={{ fontSize: '24px', marginBottom: '20px' }}>BionicPRO Reports</h1>
        <button
          onClick={() => window.location.href = `${BFF_URL}/login`}
          style={{
            padding: '12px 24px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '16px',
            cursor: 'pointer'
          }}
        >
          Login with Keycloak
        </button>
      </div>
    );
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#f9fafb',
      padding: '20px'
    }}>
      <div style={{ 
        maxWidth: '1200px', 
        margin: '0 auto'
      }}>
        {/* Шапка */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <div>
            <h1 style={{ fontSize: '24px', marginBottom: '4px' }}>BionicPRO Reports</h1>
            <p style={{ color: '#666' }}>
              User ID: {user?.crm_user_id || report?.user_id || 'N/A'}
            </p>
          </div>
          <a
            href={`${BFF_URL}/auth/logout`}
            style={{
              padding: '8px 16px',
              backgroundColor: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              textDecoration: 'none'
            }}
          >
            Logout
          </a>
        </div>

        {/* Отчет */}
        <div style={{ 
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          <h2 style={{ fontSize: '20px', marginBottom: '24px', color: '#1f2937' }}>
            Activity Report
          </h2>
          
          {reportLoading ? (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <div>Loading report data...</div>
            </div>
          ) : report ? (
            <div>
              {/* Статистические карточки */}
              <div style={{ 
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: '16px',
                marginBottom: '32px'
              }}>
                <div style={{ 
                  padding: '20px',
                  backgroundColor: '#eff6ff',
                  borderRadius: '8px',
                  borderLeft: '4px solid #3b82f6',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '14px', color: '#1e40af', marginBottom: '8px' }}>Total Sessions</div>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1e40af' }}>
                    {report.total_sessions}
                  </div>
                </div>
                
                <div style={{ 
                  padding: '20px',
                  backgroundColor: '#f0fdf4',
                  borderRadius: '8px',
                  borderLeft: '4px solid #10b981',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '14px', color: '#065f46', marginBottom: '8px' }}>Total Signals</div>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#065f46' }}>
                    {report.total_signals}
                  </div>
                </div>
                
                <div style={{ 
                  padding: '20px',
                  backgroundColor: '#fef3c7',
                  borderRadius: '8px',
                  borderLeft: '4px solid #f59e0b',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '14px', color: '#92400e', marginBottom: '8px' }}>Average Accuracy</div>
                  <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#92400e' }}>
                    {(report.average_accuracy * 100).toFixed(1)}%
                  </div>
                </div>
                
                <div style={{ 
                  padding: '20px',
                  backgroundColor: '#f5f3ff',
                  borderRadius: '8px',
                  borderLeft: '4px solid #8b5cf6',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '14px', color: '#5b21b6', marginBottom: '8px' }}>Total Usage</div>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#5b21b6' }}>
                    {formatDuration(report.total_usage_time)}
                  </div>
                </div>
              </div>

              {/* Детальная информация */}
              <div style={{ 
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: '24px'
              }}>
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px', color: '#374151' }}>
                    Activity Metrics
                  </h3>
                  <div style={{ 
                    backgroundColor: '#f9fafb',
                    padding: '20px',
                    borderRadius: '8px'
                  }}>
                    <div style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid #e5e7eb' }}>
                      <div style={{ color: '#6b7280', fontSize: '14px', marginBottom: '4px' }}>Last Activity</div>
                      <div style={{ fontWeight: '500', fontSize: '15px' }}>
                        {formatDate(report.last_activity)}
                      </div>
                    </div>
                    <div style={{ marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid #e5e7eb' }}>
                      <div style={{ color: '#6b7280', fontSize: '14px', marginBottom: '4px' }}>Average Session Time</div>
                      <div style={{ fontWeight: '500', fontSize: '15px' }}>
                        {formatDuration(report.average_session_time)}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: '#6b7280', fontSize: '14px', marginBottom: '4px' }}>Report Generated</div>
                      <div style={{ fontWeight: '500', fontSize: '15px' }}>
                        {formatDate(report.report_generated_at)}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px', color: '#374151' }}>
                    Muscle Groups
                  </h3>
                  <div style={{ 
                    backgroundColor: '#f9fafb',
                    padding: '20px',
                    borderRadius: '8px',
                    minHeight: '100%'
                  }}>
                    <div style={{ 
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '10px'
                    }}>
                      {report.muscle_groups.split(',').map((muscle: string, index: number) => (
                        <span 
                          key={index}
                          style={{
                            padding: '8px 16px',
                            backgroundColor: '#dbeafe',
                            color: '#1e40af',
                            borderRadius: '6px',
                            fontSize: '14px',
                            fontWeight: '500'
                          }}
                        >
                          {muscle.trim()}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#666' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
              <h3 style={{ fontSize: '18px', marginBottom: '8px' }}>No report available</h3>
              <p style={{ marginBottom: '20px' }}>
                Report data is not available for your account yet.
              </p>
              <button
                onClick={loadReport}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;