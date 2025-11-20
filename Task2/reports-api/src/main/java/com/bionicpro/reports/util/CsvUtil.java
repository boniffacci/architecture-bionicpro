package com.bionicpro.reports.util;

import com.bionicpro.reports.model.DailyReport;
import com.bionicpro.reports.model.MetricData;
import com.bionicpro.reports.model.ReportResponse;

import java.util.stream.Collectors;

public class CsvUtil {

    private static final String CSV_HEADER = "user_id,report_date,metric_name,events_count,value_sum,value_avg,value_min,value_max,region,prosthetic_model\n";

    public static String toCsv(ReportResponse report) {
        StringBuilder csv = new StringBuilder(CSV_HEADER);

        for (DailyReport dailyReport : report.getDailyReports()) {
            for (MetricData metric : dailyReport.getMetrics()) {
                csv.append(String.format("%s,%s,%s,%d,%.2f,%.2f,%.2f,%.2f,%s,%s\n",
                    dailyReport.getUserId(),
                    dailyReport.getReportDate(),
                    metric.getName(),
                    metric.getEventsCount(),
                    metric.getValueSum(),
                    metric.getValueAvg(),
                    metric.getValueMin(),
                    metric.getValueMax(),
                    dailyReport.getRegion(),
                    dailyReport.getProstheticModel()
                ));
            }
        }

        return csv.toString();
    }

}



