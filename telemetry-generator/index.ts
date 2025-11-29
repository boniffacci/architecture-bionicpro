import { createClient } from '@clickhouse/client';

interface TelemetryRecord {
  Email: string;
  TelemetryData: number;
  DateTime: Date;
  DeviceId: string;
}

const CLICKHOUSE_HOST = process.env.CLICKHOUSE_HOST || 'clickhouse';
const CLICKHOUSE_PORT = process.env.CLICKHOUSE_PORT || '8123';
const CLICKHOUSE_USER = process.env.CLICKHOUSE_USER || 'default';
const CLICKHOUSE_PASSWORD = process.env.CLICKHOUSE_PASSWORD || 'default';
const CLICKHOUSE_DATABASE = process.env.CLICKHOUSE_DATABASE || 'default';

const TABLE_NAME = 'telemetry';

const USERS = ['user1@example.com', 'user2@example.com'];
const DEVICES_PER_USER = ['device1', 'device2'];

const GENERATION_INTERVAL_MS = 10000; // 10 секунд

// Создание клиента ClickHouse
const client = createClient({
  host: `http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}`,
  username: CLICKHOUSE_USER,
  password: CLICKHOUSE_PASSWORD,
  database: CLICKHOUSE_DATABASE,
});

// Функция для проверки существования таблицы
async function tableExists(): Promise<boolean> {
  try {
    const result = await client.query({
      query: `
        SELECT COUNT(*) as count
        FROM system.tables
        WHERE database = {database:String} AND name = {table:String}
      `,
      query_params: {
        database: CLICKHOUSE_DATABASE,
        table: TABLE_NAME,
      },
      format: 'JSONEachRow',
    });

    const data = await result.json();
    const rows = data as Array<{ count: string }>;
    return rows.length > 0 && parseInt(rows[0].count) > 0;
  } catch (error) {
    console.error('Ошибка при проверке существования таблицы:', error);
    return false;
  }
}

// Функция для создания таблицы
async function createTable(): Promise<void> {
  try {
    const exists = await tableExists();
    if (exists) {
      console.log(`Таблица ${TABLE_NAME} уже существует`);
      return;
    }

    await client.exec({
      query: `
        CREATE TABLE IF NOT EXISTS ${TABLE_NAME} (
          Email String,
          TelemetryData Float64,
          DateTime DateTime,
          DeviceId String
        ) ENGINE = MergeTree()
        ORDER BY (Email, DeviceId, DateTime)
      `,
    });

    console.log(`Таблица ${TABLE_NAME} успешно создана`);
  } catch (error) {
    console.error('Ошибка при создании таблицы:', error);
    throw error;
  }
}

// Функция для генерации случайного числа с плавающей точкой
function generateRandomFloat(): number {
  return Math.random() * 1000;
}

// Функция для генерации данных телеметрии
function generateTelemetryData(): TelemetryRecord[] {
  const records: TelemetryRecord[] = [];
  const now = new Date();

  for (let userIndex = 0; userIndex < USERS.length; userIndex++) {
    const user = USERS[userIndex];
    for (const device of DEVICES_PER_USER) {
      records.push({
        Email: user,
        TelemetryData: generateRandomFloat(),
        DateTime: now,
        DeviceId: `${userIndex + 1}-${device}`,
      });
    }
  }

  return records;
}

// Функция для вставки данных в ClickHouse
async function insertTelemetryData(records: TelemetryRecord[]): Promise<void> {
  try {
    await client.insert({
      table: TABLE_NAME,
      values: records.map((record) => ({
        Email: record.Email,
        TelemetryData: record.TelemetryData,
        DateTime: record.DateTime.toISOString().replace('T', ' ').substring(0, 19),
        DeviceId: record.DeviceId,
      })),
      format: 'JSONEachRow',
    });

    console.log(
      `Вставлено ${records.length} записей в ${new Date().toISOString()}`
    );
  } catch (error) {
    console.error('Ошибка при вставке данных:', error);
    throw error;
  }
}

// Основная функция
async function main(): Promise<void> {
  console.log('Запуск генератора телеметрических данных...');
  console.log(`Подключение к ClickHouse: ${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}`);

  try {
    // Проверка подключения
    await client.ping();
    console.log('Успешное подключение к ClickHouse');

    // Создание таблицы
    await createTable();

    // Генерация данных каждые 10 секунд
    console.log(
      `Начало генерации данных каждые ${GENERATION_INTERVAL_MS / 1000} секунд`
    );

    // Первая генерация сразу
    const initialData = generateTelemetryData();
    await insertTelemetryData(initialData);

    // Периодическая генерация
    setInterval(async () => {
      try {
        const data = generateTelemetryData();
        await insertTelemetryData(data);
      } catch (error) {
        console.error('Ошибка при генерации данных:', error);
      }
    }, GENERATION_INTERVAL_MS);
  } catch (error) {
    console.error('Критическая ошибка:', error);
    process.exit(1);
  }
}

// Обработка завершения процесса
process.on('SIGINT', async () => {
  console.log('\nЗавершение работы...');
  await client.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\nЗавершение работы...');
  await client.close();
  process.exit(0);
});

// Запуск приложения
main().catch((error) => {
  console.error('Необработанная ошибка:', error);
  process.exit(1);
});

