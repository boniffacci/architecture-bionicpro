using ClickHouse.Driver.ADO;
using Dapper;
using ReportApi.Models;
using System.Collections.Generic;
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

        public async Task<IEnumerable<Report>> GetDataAsync(string userEmail)
        {
            using var connection = new ClickHouseConnection(_connectionString);
            await connection.OpenAsync();
            var result = await connection.QueryAsync<Report>("SELECT * FROM report WHERE user_email = @userEmail", new { userEmail });

            return result;
        }
    }
}
