package com.bionicpro.reports.repository;

import com.bionicpro.reports.model.DailyReport;
import com.bionicpro.reports.model.MetricData;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Repository
@RequiredArgsConstructor
public class ClickHouseReportRepository {

    private final JdbcTemplate jdbcTemplate;

    public List<DailyReport> findUserReports(String userId, LocalDate dateFrom, LocalDate dateTo) {
        String sql = """
            SELECT 
                user_id,
                report_date,
                metrics.name,
                metrics.events_count,
                metrics.value_sum,
                metrics.value_avg,
                metrics.value_min,
                metrics.value_max,
                region,
                prosthetic_model,
                generated_at
            FROM mart_report_user_daily
            WHERE user_id = ?
              AND report_date >= ?
              AND report_date <= ?
            ORDER BY report_date DESC
            """;

        log.debug("Executing query for user: {}, dateFrom: {}, dateTo: {}", userId, dateFrom, dateTo);
        
        return jdbcTemplate.query(sql, new DailyReportRowMapper(), userId, dateFrom, dateTo);
    }

    public List<DailyReport> findUserReportsByRegion(String userId, LocalDate dateFrom, LocalDate dateTo, String region) {
        String sql = """
            SELECT 
                user_id,
                report_date,
                metrics.name,
                metrics.events_count,
                metrics.value_sum,
                metrics.value_avg,
                metrics.value_min,
                metrics.value_max,
                region,
                prosthetic_model,
                generated_at
            FROM mart_report_user_daily
            WHERE user_id = ?
              AND report_date >= ?
              AND report_date <= ?
              AND region = ?
            ORDER BY report_date DESC
            """;

        return jdbcTemplate.query(sql, new DailyReportRowMapper(), userId, dateFrom, dateTo, region);
    }

    private static class DailyReportRowMapper implements RowMapper<DailyReport> {
        
        @Override
        public DailyReport mapRow(ResultSet rs, int rowNum) throws SQLException {
            Array namesArray = rs.getArray("metrics.name");
            Array countsArray = rs.getArray("metrics.events_count");
            Array sumsArray = rs.getArray("metrics.value_sum");
            Array avgsArray = rs.getArray("metrics.value_avg");
            Array minsArray = rs.getArray("metrics.value_min");
            Array maxsArray = rs.getArray("metrics.value_max");

            String[] names = (String[]) namesArray.getArray();
            
            Object countsObj = countsArray.getArray();
            Long[] counts = countsObj instanceof long[] ? 
                java.util.Arrays.stream((long[]) countsObj).boxed().toArray(Long[]::new) : 
                (Long[]) countsObj;
            
            Object sumsObj = sumsArray.getArray();
            Double[] sums = sumsObj instanceof double[] ? 
                java.util.Arrays.stream((double[]) sumsObj).boxed().toArray(Double[]::new) : 
                (Double[]) sumsObj;
            
            Object avgsObj = avgsArray.getArray();
            Double[] avgs = avgsObj instanceof double[] ? 
                java.util.Arrays.stream((double[]) avgsObj).boxed().toArray(Double[]::new) : 
                (Double[]) avgsObj;
            
            Object minsObj = minsArray.getArray();
            Double[] mins = minsObj instanceof double[] ? 
                java.util.Arrays.stream((double[]) minsObj).boxed().toArray(Double[]::new) : 
                (Double[]) minsObj;
            
            Object maxsObj = maxsArray.getArray();
            Double[] maxs = maxsObj instanceof double[] ? 
                java.util.Arrays.stream((double[]) maxsObj).boxed().toArray(Double[]::new) : 
                (Double[]) maxsObj;

            List<MetricData> metrics = new ArrayList<>();
            for (int i = 0; i < names.length; i++) {
                metrics.add(MetricData.builder()
                    .name(names[i])
                    .eventsCount(counts[i])
                    .valueSum(sums[i])
                    .valueAvg(avgs[i])
                    .valueMin(mins[i])
                    .valueMax(maxs[i])
                    .build());
            }

            return DailyReport.builder()
                .userId(rs.getString("user_id"))
                .reportDate(rs.getDate("report_date").toLocalDate())
                .metrics(metrics)
                .region(rs.getString("region"))
                .prostheticModel(rs.getString("prosthetic_model"))
                .generatedAt(rs.getTimestamp("generated_at").toLocalDateTime())
                .build();
        }
    }

}



