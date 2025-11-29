import { Request, Response, NextFunction } from 'express';
import { verifyToken } from '../services/keycloak';

export interface AuthRequest extends Request {
  user?: {
    email: string;
    sub: string;
  };
}

export async function authMiddleware(
  req: AuthRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const authHeader = req.headers.authorization;

    console.log('authHeader', authHeader);

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({ error: 'Missing or invalid Authorization header' });
      return;
    }

    const token = authHeader.substring(7);

    console.log('token', token);

    try {
      const decoded = await verifyToken(token);

      console.log('decoded', decoded);

      if (!decoded.email) {
        res.status(401).json({ error: 'Token does not contain email' });
        return;
      }

      req.user = {
        email: decoded.email,
        sub: decoded.sub,
      };

      next();
    } catch (error) {
      console.error('Token verification error:', error);
      res.status(401).json({ error: 'Invalid or expired token' });
      return;
    }
  } catch (error) {
    console.error('Auth middleware error:', error);
    res.status(500).json({ error: 'Internal server error' });
    return;
  }
}

