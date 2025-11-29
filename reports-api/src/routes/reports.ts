import { Router, Response } from 'express';
import { query } from '../services/db';
import { generatePDF, DeviceReport } from '../services/pdf';
import { AuthRequest } from '../middleware/auth';

const router = Router();

router.get('/', async (req: AuthRequest, res: Response) => {
  try {
    const userEmail = req.user?.email;

    if (!userEmail) {
      return res.status(401).json({ error: 'User email not found' });
    }

    const sql = `
      SELECT DISTINCT ON (device_id)
        device_id,
        telemetry_sum,
        telemetry_avg,
        telemetry_min,
        telemetry_max,
        telemetry_count,
        last_telemetry_time
      FROM reports
      WHERE customer_email = $1
      ORDER BY device_id, last_telemetry_time DESC NULLS LAST
    `;

    const rows = await query<DeviceReport>(sql, [userEmail]);

    const pdfBuffer = await generatePDF(rows, userEmail);

    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="report-${userEmail}-${Date.now()}.pdf"`
    );
    res.setHeader('Content-Length', pdfBuffer.length.toString());

    res.send(pdfBuffer);
  } catch (error) {
    console.error('Error generating report:', error);
    res.status(500).json({ error: 'Failed to generate report' });
  }
});

export default router;

