import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { getPool } from './services/db';
import reportsRouter from './routes/reports';
import { authMiddleware } from './middleware/auth';

const app = express();
const PORT = process.env.PORT || 8000;

app.use(express.json());

app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use('/reports', authMiddleware, reportsRouter);

app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Not found' });
});

app.listen(PORT, async () => {
  console.log(`Reports API server is running on port ${PORT}`);
  
  try {
    const pool = getPool();
    await pool.query('SELECT 1');
    console.log('Database connection established');
  } catch (error) {
    console.error('Failed to connect to database:', error);
  }
});

process.on('SIGTERM', async () => {
  console.log('SIGTERM signal received: closing HTTP server');
  const pool = getPool();
  await pool.end();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('SIGINT signal received: closing HTTP server');
  const pool = getPool();
  await pool.end();
  process.exit(0);
});

