import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

type ReportItem = {
  report_date: string;
  prosthesis_id: number;
  total_active_sec: number;
  avg_reaction_ms: number;
  movements_count: number;
  errors_count: number;
  battery_avg_pct: number;
  crm_country: string;
  crm_segment: string;
  crm_tariff: string;
};

type ReportResponse = {
  user_id: number;
  from_date: string;
  to_date: string;
  items: ReportItem[];
};

const API_BASE =
  process.env.REACT_APP_REPORTS_API_URL || 'http://localhost:8000';

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLoadReport = async () => {
    if (!initialized) return;

    // если пользователь не авторизован – отправляем логиниться в Keycloak
    if (!keycloak?.authenticated) {
      await keycloak.login();
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = keycloak.token;

      const resp = await fetch(`${API_BASE}/reports/me`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP error ${resp.status}`);
      }

      const data: ReportResponse = await resp.json();
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Ошибка при получении отчёта');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h1>Отчёт по работе протеза</h1>

      {/* КНОПКА ПОЛУЧЕНИЯ ОТЧЁТА */}
      <button onClick={handleLoadReport} disabled={loading}>
        {loading ? 'Загружаем…' : 'Получить отчёт'}
      </button>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {report && (
        <div style={{ marginTop: 24 }}>
          <h2>
            Пользователь #{report.user_id} (период{' '}
            {report.from_date} — {report.to_date})
          </h2>

          <table border={1} cellPadding={4} cellSpacing={0}>
            <thead>
              <tr>
                <th>Дата</th>
                <th>ID протеза</th>
                <th>Активность, сек</th>
                <th>Средняя реакция, мс</th>
                <th>Движения</th>
                <th>Ошибки</th>
                <th>Батарея, %</th>
                <th>Страна</th>
                <th>Сегмент</th>
                <th>Тариф</th>
              </tr>
            </thead>
            <tbody>
              {report.items.map((item, idx) => (
                <tr key={idx}>
                  <td>{item.report_date}</td>
                  <td>{item.prosthesis_id}</td>
                  <td>{item.total_active_sec}</td>
                  <td>{item.avg_reaction_ms.toFixed(1)}</td>
                  <td>{item.movements_count}</td>
                  <td>{item.errors_count}</td>
                  <td>{item.battery_avg_pct.toFixed(1)}</td>
                  <td>{item.crm_country}</td>
                  <td>{item.crm_segment}</td>
                  <td>{item.crm_tariff}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ReportPage;
