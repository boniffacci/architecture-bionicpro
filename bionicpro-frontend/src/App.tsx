// Импортируем React и хук useState для управления состоянием компонента
import React, { useState } from 'react'
// Импортируем хук для работы с Keycloak аутентификацией
import { useKeycloak } from '@react-keycloak/web'

// Интерфейс для ответа от бэкенда /reports
interface ReportsResponse {
  payload: any;
}

// Интерфейс для состояния ответа бэкенда
interface BackendResponse {
  status: number;
  data: ReportsResponse | null;
  error: string | null;
}

// Интерфейс для декодированного JWT токена
interface DecodedToken {
  exp: number;               // Время истечения токена (Unix timestamp)
  iat: number;               // Время выдачи токена (Unix timestamp)
  sub: string;               // Subject (идентификатор пользователя)
  preferred_username?: string; // Имя пользователя
  email?: string;            // Email пользователя
  name?: string;             // Полное имя пользователя
  realm_access?: {           // Роли уровня realm
    roles: string[];
  };
  [key: string]: any;        // Дополнительные поля
}

/**
 * Декодирует JWT токен без проверки подписи
 * ВНИМАНИЕ: Это только для отображения данных, не для проверки безопасности!
 * @param token - JWT токен
 * @returns декодированный payload токена
 */
function decodeJWT(token: string): DecodedToken {
  // JWT состоит из трех частей, разделенных точками: header.payload.signature
  const parts = token.split('.');
  
  if (parts.length !== 3) {
    throw new Error('Invalid JWT token format');
  }
  
  // Декодируем payload (вторая часть токена)
  const payload = parts[1];
  
  // Заменяем base64url символы на стандартные base64
  const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
  
  // Декодируем base64 и парсим JSON
  const jsonPayload = decodeURIComponent(
    atob(base64)
      .split('')
      .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join('')
  );
  
  return JSON.parse(jsonPayload);
}

export default function App() {
  // Получаем объект keycloak и флаг инициализации из хука useKeycloak
  const { keycloak, initialized } = useKeycloak();
  
  // Состояние: ответ от бэкенда /reports
  const [backendResponse, setBackendResponse] = useState<BackendResponse | null>(null);
  
  // Состояние: загружается ли запрос к бэкенду
  const [loadingBackend, setLoadingBackend] = useState(false);

  // Функция для вызова бэкенда /reports
  const fetchReports = async () => {
    // Проверяем наличие токена аутентификации
    if (!keycloak.token) {
      alert('Токен не найден');
      return;
    }

    // Устанавливаем состояние загрузки
    setLoadingBackend(true);
    setBackendResponse(null);

    try {
      // Выполняем GET запрос к бэкенду
      const response = await fetch('http://localhost:3001/reports', {
        method: 'GET',
        headers: {
          // Передаем JWT токен в заголовке Authorization
          'Authorization': `Bearer ${keycloak.token}`,
          'Content-Type': 'application/json',
        },
      });

      // Получаем HTTP статус код
      const status = response.status;
      
      // Пытаемся распарсить JSON ответ
      let data = null;
      let error = null;
      
      if (response.ok) {
        // Если запрос успешен - парсим JSON
        data = await response.json();
      } else {
        // Если ошибка - сохраняем текст ошибки
        error = await response.text();
      }

      // Сохраняем результат в состояние
      setBackendResponse({ status, data, error });
    } catch (err) {
      // Обрабатываем ошибки сети или парсинга
      console.error('Backend request failed:', err);
      setBackendResponse({
        status: 0,
        data: null,
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      // Завершаем состояние загрузки
      setLoadingBackend(false);
    }
  };

  // Проверяем, инициализирован ли Keycloak
  if (!initialized) {
    // Если нет, показываем индикатор загрузки
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-xl">Загрузка...</div>
      </div>
    );
  }

  // Проверяем, аутентифицирован ли пользователь
  if (!keycloak.authenticated) {
    // Если нет, показываем экран входа
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-8 bg-white rounded-2xl shadow">
          <h1 className="text-2xl font-bold mb-4">Вход в систему</h1>
          <p className="mb-6 text-gray-600">
            Для доступа к приложению необходимо авторизоваться через Keycloak
          </p>
          <button
            // При клике вызываем метод login() из Keycloak с явным указанием PKCE
            onClick={() => keycloak.login({
              // Явно указываем использование PKCE (Proof Key for Code Exchange)
              pkceMethod: 'S256'
            })}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 transition"
          >
            Войти через Keycloak
          </button>
          <button
            // Позволяет принудительно завершить сессию Keycloak при необходимости
            onClick={() => keycloak.logout({ redirectUri: window.location.origin })}
            className="w-full mt-3 border border-red-500 text-red-600 py-3 px-4 rounded-lg hover:bg-red-50 transition"
          >
            Разлогиниться
          </button>
          <p className="mt-4 text-sm text-gray-500">
            Используется протокол OAuth 2.0 с PKCE (Proof Key for Code Exchange)
          </p>
        </div>
      </div>
    );
  }

  // Декодируем JWT токен для отображения
  const decodedToken = keycloak.token ? decodeJWT(keycloak.token) : null;

  // Пользователь авторизован - показываем главную страницу
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 space-y-6">
        {/* Заголовок и кнопка выхода */}
        <div className="bg-white rounded-2xl shadow p-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-green-600">
              ✓ Вы авторизованы!
            </h1>
            <button
              // При клике вызываем метод logout() из Keycloak
              onClick={() => keycloak.logout({ redirectUri: window.location.origin })}
              className="bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition"
            >
              Выйти
            </button>
          </div>
        </div>

        {/* Блок с информацией о JWT токене */}
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-xl font-bold mb-4">Информация из JWT токена</h2>
          {decodedToken && (
            <div className="space-y-2">
              {/* Отображаем основные поля токена */}
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="font-semibold">Пользователь:</div>
                <div>{decodedToken.preferred_username || 'N/A'}</div>
                
                <div className="font-semibold">Email:</div>
                <div>{decodedToken.email || 'N/A'}</div>
                
                <div className="font-semibold">Имя:</div>
                <div>{decodedToken.name || 'N/A'}</div>
                
                <div className="font-semibold">Subject (ID):</div>
                <div className="break-all">{decodedToken.sub}</div>
                
                <div className="font-semibold">Роли:</div>
                <div>{decodedToken.realm_access?.roles.join(', ') || 'N/A'}</div>
                
                <div className="font-semibold">Выдан:</div>
                <div>{new Date(decodedToken.iat * 1000).toLocaleString('ru-RU')}</div>
                
                <div className="font-semibold">Истекает:</div>
                <div>{new Date(decodedToken.exp * 1000).toLocaleString('ru-RU')}</div>
              </div>
              
              {/* Полный JSON токена */}
              <details className="mt-4">
                <summary className="cursor-pointer font-semibold text-blue-600 hover:text-blue-800">
                  Показать полный JWT payload (JSON)
                </summary>
                <pre className="mt-2 p-4 bg-gray-100 rounded-lg overflow-auto text-xs">
                  {JSON.stringify(decodedToken, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>

        {/* Блок для вызова бэкенда */}
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-xl font-bold mb-4">Запрос к бэкенду</h2>
          
          {/* Кнопка для вызова /reports */}
          <button
            onClick={fetchReports}
            disabled={loadingBackend}
            className="bg-blue-600 text-white py-2 px-6 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loadingBackend ? 'Загрузка...' : 'Вызвать GET /reports'}
          </button>

          {/* Отображение результата запроса */}
          {backendResponse && (
            <div className="mt-4">
              {/* HTTP статус код */}
              <div className="mb-2">
                <span className="font-semibold">HTTP статус код: </span>
                <span className={`font-mono ${
                  backendResponse.status >= 200 && backendResponse.status < 300
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}>
                  {backendResponse.status}
                </span>
              </div>

              {/* Данные ответа или ошибка */}
              {backendResponse.data ? (
                <div>
                  <div className="font-semibold mb-2">Ответ от сервера:</div>
                  <pre className="p-4 bg-gray-100 rounded-lg overflow-auto text-sm">
                    {JSON.stringify(backendResponse.data, null, 2)}
                  </pre>
                </div>
              ) : backendResponse.error ? (
                <div>
                  <div className="font-semibold mb-2 text-red-600">Ошибка:</div>
                  <pre className="p-4 bg-red-50 rounded-lg overflow-auto text-sm text-red-800">
                    {backendResponse.error}
                  </pre>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}