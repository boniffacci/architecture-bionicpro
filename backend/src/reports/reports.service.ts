import { Injectable } from '@nestjs/common';

@Injectable()
export class ReportsService {
  getReport() {
    return {
      generatedAt: new Date().toISOString(),
      usageStats: {
        users: 42,
        sessions: 87,
        reportsDownloaded: 13,
      },
    };
  }
}
