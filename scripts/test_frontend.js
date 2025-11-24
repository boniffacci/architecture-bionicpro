// Простой тест для проверки фронтенда
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  // Слушаем консольные сообщения
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  
  // Слушаем ошибки
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  
  // Переходим на страницу
  console.log('Открываем http://localhost:3000/');
  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle2', timeout: 10000 });
  
  // Ждём 2 секунды
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  // Получаем текст страницы
  const bodyText = await page.evaluate(() => document.body.innerText);
  console.log('Текст страницы:', bodyText);
  
  // Получаем URL
  const url = page.url();
  console.log('Текущий URL:', url);
  
  await browser.close();
})();
