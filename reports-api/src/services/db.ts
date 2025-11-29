import { Pool, PoolClient } from 'pg';

let pool: Pool | null = null;

export function getPool(): Pool {
  if (!pool) {
    pool = new Pool({
      host: process.env.DB_HOST || 'api_db',
      port: parseInt(process.env.DB_PORT || '5432'),
      database: process.env.DB_NAME || 'api_db',
      user: process.env.DB_USER || 'api_user',
      password: process.env.DB_PASSWORD || 'api_password',
    });

    pool.on('error', (err) => {
      console.error('Unexpected error on idle client', err);
    });
  }

  return pool;
}

export async function query<T = any>(text: string, params?: any[]): Promise<T[]> {
  const client = await getPool().connect();
  try {
    const result = await client.query(text, params);
    return result.rows;
  } finally {
    client.release();
  }
}

export async function getClient(): Promise<PoolClient> {
  return await getPool().connect();
}

