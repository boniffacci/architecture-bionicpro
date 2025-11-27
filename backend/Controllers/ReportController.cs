using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Microsoft.IdentityModel.Tokens;
using ReportApi.Extensions;
using ReportApi.Models;
using ReportApi.Repositories;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;

namespace ReportApi.Controllers
{
    [ApiController]
    [Route("reports")]
    public class ReportController(ILogger<ReportController> logger, ReportRepository reportRepository) : ControllerBase
    {
        private readonly ILogger<ReportController> _logger = logger;
        private readonly ReportRepository _reportRepository = reportRepository;

        [HttpGet]
        [Authorize]
        public async Task<IEnumerable<Report>> Get()
        {
            var currentUserEmail = User.GetUserEmail();
            _logger.LogWarning($"UserEmail: {currentUserEmail}");

            return await _reportRepository.GetDataAsync(currentUserEmail);
        }

        [HttpGet]
        [Route("test")]
        public async Task Test()
        {
            var client = new HttpClient();
            var keyUri = "http://localhost:8088/realms/reports-realm/protocol/openid-connect/certs";
            var response = await client.GetAsync(keyUri);
            var keys = new JsonWebKeySet(await response.Content.ReadAsStringAsync());
        }
    }
}
