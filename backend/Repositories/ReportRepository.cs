using ClickHouse.Client.ADO;
using Dapper;
using ReportApi.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace ReportApi.Repositories
{
    public class ReportRepository
    {
        private readonly ClickHouseConnection _connection;

        public ReportRepository(ClickHouseConnection connection)
        {
            _connection = connection;
        }

        public async Task<IEnumerable<Report>> GetDataAsync(long userId)
        {
            _connection.Open();
            var result = await _connection.QueryAsync<Report>("SELECT * FROM report WHERE userId = @userId", new { userId });

            return result;
        }
    }
}
