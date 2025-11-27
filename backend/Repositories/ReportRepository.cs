using ClickHouse.Driver.ADO;
using Dapper;
using ReportApi.Models;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace ReportApi.Repositories
{
    public class ReportRepository
    {
        private readonly string _connectionString;

        public ReportRepository(string connectionString)
        {
            _connectionString = connectionString;
        }

        public async Task<IEnumerable<Report>> GetDataAsync(string userEmail, DateTimeOffset reportDate)
        {
            using var connection = new ClickHouseConnection(_connectionString);
            await connection.OpenAsync();
            var result = await connection.QueryAsync<Report>("SELECT * FROM report WHERE user_email = @userEmail and report_date > @reportDate", new { userEmail, reportDate });

            return result;
        }

        public async Task<ReportDate> GetReportDateAsync()
        {
            using var connection = new ClickHouseConnection(_connectionString);
            await connection.OpenAsync();
            var result = await connection.QueryAsync<ReportDate>("SELECT * FROM report_date");

            return result.FirstOrDefault();
        }
    }
}
