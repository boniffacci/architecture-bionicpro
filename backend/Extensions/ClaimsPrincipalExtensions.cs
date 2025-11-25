using System.Security.Claims;

namespace ReportApi.Extensions
{
    public static class ClaimsPrincipalExtensions
    {
        public static string GetUserEmail(this ClaimsPrincipal user)
        {
            var emailClaim = user?.FindFirstValue(ClaimTypes.Email);
            if (string.IsNullOrWhiteSpace(emailClaim))
            {
                return "not found";
            }
            return emailClaim;
        }
    }
}
