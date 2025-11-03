// Импортируем библиотеку React для создания компонентов
import React from 'react';
// Импортируем ReactDOM для рендеринга React-приложения в DOM (версия для React 18+)
import ReactDOM from 'react-dom/client';
// Импортируем глобальные стили приложения
import './index.css';
// Импортируем главный компонент приложения
import App from './App';

// Создаем корневой элемент React приложения
const root = ReactDOM.createRoot(
  // Находим HTML-элемент с id="root" и приводим его к типу HTMLElement
  document.getElementById('root') as HTMLElement
);

// Рендерим приложение в корневой элемент
root.render(
  // StrictMode - режим разработки для выявления потенциальных проблем
  <React.StrictMode>
    {/* Главный компонент приложения */}
    <App />
  </React.StrictMode>
);