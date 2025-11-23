import { useEffect, useState } from 'react'

// URL auth_proxy сервиса (теперь используем относительный путь, так как фронтенд работает через auth_proxy)
const AUTH_PROXY_URL = ''  // Пустая строка означает текущий домен (localhost:3002)

// Интерфейс для информации о пользователе
interface UserInfo {
  has_session_cookie: boolean
  is_authorized: boolean
  username?: string
  email?: string
  first_name?: string
  last_name?: string
  realm_roles?: string[]
  permissions?: any
  sub?: string
}

// Интерфейс для ответа от reports_api/jwt
interface JwtResponse {
  jwt: any | null
  error?: string
}

// Интерфейс для ответа от reports_api/reports
interface ReportResponse {
  user_name: string
  user_email: string
  total_events: number
  total_duration: number
  prosthesis_stats: Array<{
    prosthesis_type: string
    events_count: number
    total_duration: number
    avg_amplitude: number
    avg_frequency: number
  }>
  error?: string
}

export default function App() {
  // Состояние: информация о пользователе
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  
  // Состояние: загружается ли информация о пользователе
  const [loadingUserInfo, setLoadingUserInfo] = useState(true)
  
  // Состояние: ответ от reports_api/jwt
  const [jwtResponse, setJwtResponse] = useState<JwtResponse | null>(null)
  
  // Состояние: загружается ли запрос к reports_api/jwt
  const [loadingJwt, setLoadingJwt] = useState(false)
  
  // Состояние: ответ от reports_api/reports
  const [reportResponse, setReportResponse] = useState<ReportResponse | null>(null)
  
  // Состояние: загружается ли запрос к reports_api/reports
  const [loadingReport, setLoadingReport] = useState(false)
  
  // Состояние: происходит ли редирект
  const [isRedirecting, setIsRedirecting] = useState(false)

  // Загрузка информации о пользователе при монтировании компонента
  useEffect(() => {
    // Проверяем, не вернулись ли мы с callback
    const urlParams = new URLSearchParams(window.location.search)
    const hasError = urlParams.has('error')
    
    if (hasError) {
      console.error('Auth error:', urlParams.get('error'))
      setLoadingUserInfo(false)
      return
    }
    
    fetchUserInfo()
  }, [])

  // Функция для получения информации о пользователе
  const fetchUserInfo = async () => {
    // Если уже происходит редирект, не делаем запрос
    if (isRedirecting) {
      return
    }
    
    setLoadingUserInfo(true)
    
    try {
      const response = await fetch(`${AUTH_PROXY_URL}/user_info`, {
        method: 'GET',
        credentials: 'include', // Включаем отправку cookies
      })
      
      if (response.ok) {
        const data: UserInfo = await response.json()
        setUserInfo(data)
        
        // Если пользователь не авторизован, редиректим на страницу входа
        if (!data.is_authorized) {
          // Устанавливаем флаг редиректа
          setIsRedirecting(true)
          console.log('User not authorized, redirecting to sign_in...')
          
          // Очищаем query параметры перед редиректом
          const cleanUrl = window.location.origin + window.location.pathname
          window.location.href = `${AUTH_PROXY_URL}/sign_in?redirect_to=${encodeURIComponent(cleanUrl)}`
          return // Прерываем выполнение
        }
        
        // Пользователь авторизован
        setLoadingUserInfo(false)
      } else {
        console.error('Failed to fetch user info:', response.statusText)
        setLoadingUserInfo(false)
      }
    } catch (error) {
      console.error('Error fetching user info:', error)
      setLoadingUserInfo(false)
    }
  }

  // Функция для выхода из системы
  const handleSignOut = async () => {
    try {
      const response = await fetch(`${AUTH_PROXY_URL}/sign_out`, {
        method: 'POST',
        credentials: 'include',
      })
      
      console.log('Sign out response:', response.status)
      
      // Редиректим на /sign_in (это перенаправит на Keycloak)
      // Используем window.location.replace для принудительного редиректа
      window.location.replace(`/sign_in?redirect_to=${encodeURIComponent(window.location.origin)}`)
    } catch (error) {
      console.error('Error signing out:', error)
      // Все равно редиректим
      window.location.replace(`/sign_in?redirect_to=${encodeURIComponent(window.location.origin)}`)
    }
  }

  // Функция для получения JWT от reports_api через auth_proxy
  const fetchReportsJwt = async () => {
    setLoadingJwt(true)
    setJwtResponse(null)
    
    try {
      // Проксируем запрос через auth_proxy (GET с query параметрами)
      const upstream_uri = encodeURIComponent('http://localhost:3003/jwt')
      const response = await fetch(`${AUTH_PROXY_URL}/proxy?upstream_uri=${upstream_uri}&redirect_to_sign_in=false`, {
        method: 'GET',
        credentials: 'include',
      })
      
      if (response.ok) {
        const data: JwtResponse = await response.json()
        setJwtResponse(data)
      } else {
        console.error('Failed to fetch JWT:', response.statusText)
        setJwtResponse({ jwt: null, error: `HTTP ${response.status}: ${response.statusText}` })
      }
    } catch (error) {
      console.error('Error fetching JWT:', error)
      setJwtResponse({ jwt: null, error: String(error) })
    } finally {
      setLoadingJwt(false)
    }
  }

  // Функция для создания отчёта
  const generateReport = async (schema: 'default' | 'debezium') => {
    setLoadingReport(true)
    setReportResponse(null)
    
    try {
      // Вычисляем end_ts: 00:00 и 1 число текущего месяца по UTC
      const now = new Date()
      const firstDayOfMonth = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 0, 0))
      const end_ts = firstDayOfMonth.toISOString()
      
      // Формируем тело запроса
      const requestBody = {
        start_ts: null,
        end_ts: end_ts,
        schema: schema
      }
      
      // Проксируем запрос через auth_proxy
      const upstream_uri = encodeURIComponent('http://localhost:3003/reports')
      const response = await fetch(`${AUTH_PROXY_URL}/proxy?upstream_uri=${upstream_uri}&redirect_to_sign_in=false`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      })
      
      if (response.ok) {
        const data: ReportResponse = await response.json()
        setReportResponse(data)
      } else {
        const errorText = await response.text()
        console.error('Failed to generate report:', response.statusText, errorText)
        setReportResponse({ 
          user_name: '',
          user_email: '',
          total_events: 0,
          total_duration: 0,
          prosthesis_stats: [],
          error: `HTTP ${response.status}: ${errorText}` 
        })
      }
    } catch (error) {
      console.error('Error generating report:', error)
      setReportResponse({ 
        user_name: '',
        user_email: '',
        total_events: 0,
        total_duration: 0,
        prosthesis_stats: [],
        error: String(error) 
      })
    } finally {
      setLoadingReport(false)
    }
  }

  // Показываем индикатор загрузки, пока проверяем авторизацию
  if (loadingUserInfo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-xl">Загрузка...</div>
      </div>
    )
  }

  // Если пользователь не авторизован, показываем сообщение (редирект произойдет автоматически)
  if (!userInfo || !userInfo.is_authorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-xl">Перенаправление на страницу входа...</div>
      </div>
    )
  }

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
              onClick={handleSignOut}
              className="bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition"
            >
              Выйти
            </button>
          </div>
        </div>

        {/* Блок с информацией о пользователе */}
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-xl font-bold mb-4">Информация о пользователе</h2>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="font-semibold">Пользователь:</div>
              <div>{userInfo.username || 'N/A'}</div>
              
              <div className="font-semibold">Email:</div>
              <div>{userInfo.email || 'N/A'}</div>
              
              <div className="font-semibold">Имя:</div>
              <div>{userInfo.first_name || 'N/A'}</div>
              
              <div className="font-semibold">Фамилия:</div>
              <div>{userInfo.last_name || 'N/A'}</div>
              
              <div className="font-semibold">Subject (ID):</div>
              <div className="break-all">{userInfo.sub || 'N/A'}</div>
              
              <div className="font-semibold">Роли:</div>
              <div>{userInfo.realm_roles?.join(', ') || 'N/A'}</div>
            </div>
            
            {/* Полный JSON user_info */}
            <details className="mt-4">
              <summary className="cursor-pointer font-semibold text-blue-600 hover:text-blue-800">
                Показать полный user_info (JSON)
              </summary>
              <pre className="mt-2 p-4 bg-gray-100 rounded-lg overflow-auto text-xs">
                {JSON.stringify(userInfo, null, 2)}
              </pre>
            </details>
          </div>
        </div>

        {/* Блок для вызова reports_api/jwt */}
        <div className="bg-white rounded-2xl shadow p-6">
          <h2 className="text-xl font-bold mb-4">Запросы к reports_api</h2>
          
          {/* Кнопки для вызова различных эндпоинтов */}
          <div className="flex flex-wrap gap-3 mb-4">
            <button
              onClick={fetchReportsJwt}
              disabled={loadingJwt}
              className="bg-blue-600 text-white py-2 px-6 rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loadingJwt ? 'Загрузка...' : 'Посмотреть JWT'}
            </button>
            
            <button
              onClick={() => generateReport('default')}
              disabled={loadingReport}
              className="bg-green-600 text-white py-2 px-6 rounded-lg hover:bg-green-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loadingReport ? 'Загрузка...' : 'Отчёт (default)'}
            </button>
            
            <button
              onClick={() => generateReport('debezium')}
              disabled={loadingReport}
              className="bg-purple-600 text-white py-2 px-6 rounded-lg hover:bg-purple-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loadingReport ? 'Загрузка...' : 'Отчёт (debezium)'}
            </button>
          </div>

          {/* Отображение результата запроса JWT */}
          {jwtResponse && (
            <div className="mt-4">
              {jwtResponse.jwt ? (
                <div>
                  <div className="font-semibold mb-2 text-green-600">✓ JWT получен от reports_api:</div>
                  <pre className="p-4 bg-gray-100 rounded-lg overflow-auto text-sm">
                    {JSON.stringify(jwtResponse.jwt, null, 2)}
                  </pre>
                </div>
              ) : (
                <div>
                  <div className="font-semibold mb-2 text-orange-600">⚠ JWT не найден</div>
                  {jwtResponse.error && (
                    <pre className="p-4 bg-orange-50 rounded-lg overflow-auto text-sm text-orange-800">
                      {jwtResponse.error}
                    </pre>
                  )}
                </div>
              )}
            </div>
          )}
          
          {/* Отображение результата запроса отчёта */}
          {reportResponse && (
            <div className="mt-4">
              {reportResponse.error ? (
                <div>
                  <div className="font-semibold mb-2 text-red-600">✗ Ошибка при создании отчёта</div>
                  <pre className="p-4 bg-red-50 rounded-lg overflow-auto text-sm text-red-800">
                    {reportResponse.error}
                  </pre>
                </div>
              ) : (
                <div>
                  <div className="font-semibold mb-2 text-green-600">✓ Отчёт создан успешно:</div>
                  <div className="p-4 bg-gray-100 rounded-lg">
                    <div className="grid grid-cols-2 gap-2 text-sm mb-4">
                      <div className="font-semibold">Пользователь:</div>
                      <div>{reportResponse.user_name}</div>
                      
                      <div className="font-semibold">Email:</div>
                      <div>{reportResponse.user_email}</div>
                      
                      <div className="font-semibold">Всего событий:</div>
                      <div>{reportResponse.total_events}</div>
                      
                      <div className="font-semibold">Общая длительность:</div>
                      <div>{reportResponse.total_duration} мс</div>
                    </div>
                    
                    {reportResponse.prosthesis_stats.length > 0 && (
                      <div>
                        <div className="font-semibold mb-2">Статистика по протезам:</div>
                        <div className="space-y-2">
                          {reportResponse.prosthesis_stats.map((stat, idx) => (
                            <div key={idx} className="bg-white p-3 rounded border">
                              <div className="font-semibold">{stat.prosthesis_type}</div>
                              <div className="text-xs text-gray-600 mt-1">
                                События: {stat.events_count} | 
                                Длительность: {stat.total_duration} мс | 
                                Ср. амплитуда: {stat.avg_amplitude.toFixed(2)} | 
                                Ср. частота: {stat.avg_frequency.toFixed(2)} Гц
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <details className="mt-4">
                      <summary className="cursor-pointer font-semibold text-blue-600 hover:text-blue-800">
                        Показать полный JSON
                      </summary>
                      <pre className="mt-2 p-4 bg-white rounded-lg overflow-auto text-xs">
                        {JSON.stringify(reportResponse, null, 2)}
                      </pre>
                    </details>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
