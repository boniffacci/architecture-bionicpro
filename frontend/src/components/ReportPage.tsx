// Импортируем React и хук useState для управления состоянием компонента
import React, { useState } from 'react';
// Импортируем хук для работы с Keycloak аутентификацией
import { useKeycloak } from '@react-keycloak/web';

// Определяем компонент страницы отчетов с типом React.FC
const ReportPage: React.FC = () => {
  // Получаем объект keycloak и флаг инициализации из хука useKeycloak
  const { keycloak, initialized } = useKeycloak();
  // Создаем состояние для отслеживания процесса загрузки (по умолчанию false)
  const [loading, setLoading] = useState(false);
  // Создаем состояние для хранения сообщения об ошибке (по умолчанию null)
  const [error, setError] = useState<string | null>(null);

  // Определяем асинхронную функцию для скачивания отчета
  const downloadReport = async () => {
    // Проверяем наличие токена аутентификации (optional chaining)
    if (!keycloak?.token) {
      // Если токена нет, устанавливаем ошибку
      setError('Not authenticated');
      // Прерываем выполнение функции
      return;
    }

    // Блок try для обработки возможных ошибок
    try {
      // Устанавливаем флаг загрузки в true
      setLoading(true);
      // Очищаем предыдущие ошибки
      setError(null);

      // Выполняем HTTP-запрос к API для получения отчета
      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports`, {
        // Устанавливаем заголовки запроса
        headers: {
          // Добавляем токен авторизации в формате Bearer
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      // Здесь должна быть обработка ответа (пока пусто)
      
    } catch (err) {
      // Обрабатываем ошибку: проверяем, является ли err объектом Error
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      // Блок finally выполняется всегда, сбрасываем флаг загрузки
      setLoading(false);
    }
  };

  // Проверяем, инициализирован ли Keycloak
  if (!initialized) {
    // Если нет, показываем индикатор загрузки
    return <div>Loading...</div>;
  }

  // Проверяем, аутентифицирован ли пользователь
  if (!keycloak.authenticated) {
    // Если нет, показываем экран входа
    return (
      // Контейнер с центрированием по вертикали и горизонтали, серый фон
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        {/* Кнопка входа */}
        <button
          // При клике вызываем метод login() из Keycloak
          onClick={() => keycloak.login()}
          // Стили кнопки: отступы, синий фон, белый текст, скругление, эффект при наведении
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Login
        </button>
      </div>
    );
  }

  // Если пользователь аутентифицирован, показываем главную страницу
  return (
    // Контейнер с центрированием и серым фоном на всю высоту экрана
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
      {/* Белая карточка с отступами, скруглением и тенью */}
      <div className="p-8 bg-white rounded-lg shadow-md">
        {/* Заголовок страницы: крупный, жирный шрифт, отступ снизу */}
        <h1 className="text-2xl font-bold mb-6">Usage Reports</h1>
        
        {/* Кнопка для скачивания отчета */}
        <button
          // При клике вызываем функцию downloadReport
          onClick={downloadReport}
          // Отключаем кнопку во время загрузки
          disabled={loading}
          // Динамические стили: если идет загрузка, добавляем прозрачность и запрет курсора
          className={`px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {/* Текст кнопки меняется в зависимости от состояния загрузки */}
          {loading ? 'Generating Report...' : 'Download Report'}
        </button>

        {/* Условный рендеринг: показываем блок ошибки только если error не null */}
        {error && (
          // Блок с красным фоном и текстом для отображения ошибки
          <div className="mt-4 p-4 bg-red-100 text-red-700 rounded">
            {/* Выводим текст ошибки */}
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

// Экспортируем компонент ReportPage как модуль по умолчанию
export default ReportPage;