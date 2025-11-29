import PDFDocument from 'pdfkit';

export interface DeviceReport {
  device_id: string;
  telemetry_sum: number | null;
  telemetry_avg: number | null;
  telemetry_min: number | null;
  telemetry_max: number | null;
  telemetry_count: number | null;
  last_telemetry_time: Date | null;
}

export function generatePDF(reports: DeviceReport[], userEmail: string): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    try {
      const doc = new PDFDocument({ margin: 50 });
      const chunks: Buffer[] = [];

      doc.on('data', (chunk) => chunks.push(chunk));
      doc.on('end', () => resolve(Buffer.concat(chunks)));
      doc.on('error', reject);

      // Header
      doc.fontSize(20).text('Device Telemetry Report', { align: 'center' });
      doc.moveDown();
      doc.fontSize(12).text(`User: ${userEmail}`, { align: 'center' });
      doc.text(`Generated: ${new Date().toLocaleString()}`, { align: 'center' });
      doc.moveDown(2);

      if (reports.length === 0) {
        doc.fontSize(14).text('No data available for this user.', { align: 'center' });
        doc.end();
        return;
      }

      // Table setup
      const tableTop = doc.y;
      const tableLeft = 50;
      const tableWidth = 500;
      const rowHeight = 30;
      const headerHeight = 40;
      const columnWidths = {
        device: 100,
        sum: 80,
        avg: 80,
        min: 80,
        max: 80,
        count: 80,
        time: 100,
      };

      // Table headers
      doc.fontSize(10).font('Helvetica-Bold');
      let x = tableLeft;
      
      doc.text('Device ID', x, tableTop, { width: columnWidths.device });
      x += columnWidths.device;
      doc.text('Sum', x, tableTop, { width: columnWidths.sum });
      x += columnWidths.sum;
      doc.text('Avg', x, tableTop, { width: columnWidths.avg });
      x += columnWidths.avg;
      doc.text('Min', x, tableTop, { width: columnWidths.min });
      x += columnWidths.min;
      doc.text('Max', x, tableTop, { width: columnWidths.max });
      x += columnWidths.max;
      doc.text('Count', x, tableTop, { width: columnWidths.count });
      x += columnWidths.count;
      doc.text('Last Time', x, tableTop, { width: columnWidths.time });

      // Draw header line
      doc.moveTo(tableLeft, tableTop + headerHeight)
         .lineTo(tableLeft + tableWidth, tableTop + headerHeight)
         .stroke();

      // Table rows
      doc.font('Helvetica').fontSize(9);
      let y = tableTop + headerHeight + 10;

      reports.forEach((report, index) => {
        if (y > 700) {
          // New page if needed
          doc.addPage();
          y = 50;
        }

        x = tableLeft;
        
        // Device ID
        doc.text(report.device_id || 'N/A', x, y, { width: columnWidths.device });
        x += columnWidths.device;
        
        // Sum
        doc.text(
          report.telemetry_sum !== null ? report.telemetry_sum.toFixed(2) : 'N/A',
          x,
          y,
          { width: columnWidths.sum }
        );
        x += columnWidths.sum;
        
        // Avg
        doc.text(
          report.telemetry_avg !== null ? report.telemetry_avg.toFixed(2) : 'N/A',
          x,
          y,
          { width: columnWidths.avg }
        );
        x += columnWidths.avg;
        
        // Min
        doc.text(
          report.telemetry_min !== null ? report.telemetry_min.toFixed(2) : 'N/A',
          x,
          y,
          { width: columnWidths.min }
        );
        x += columnWidths.min;
        
        // Max
        doc.text(
          report.telemetry_max !== null ? report.telemetry_max.toFixed(2) : 'N/A',
          x,
          y,
          { width: columnWidths.max }
        );
        x += columnWidths.max;
        
        // Count
        doc.text(
          report.telemetry_count !== null ? report.telemetry_count.toString() : 'N/A',
          x,
          y,
          { width: columnWidths.count }
        );
        x += columnWidths.count;
        
        // Last Time
        const timeStr = report.last_telemetry_time
          ? new Date(report.last_telemetry_time).toLocaleString()
          : 'N/A';
        doc.text(timeStr, x, y, { width: columnWidths.time });

        // Draw row separator
        y += rowHeight;
        doc.moveTo(tableLeft, y)
           .lineTo(tableLeft + tableWidth, y)
           .stroke();
      });

      doc.end();
    } catch (error) {
      reject(error);
    }
  });
}

