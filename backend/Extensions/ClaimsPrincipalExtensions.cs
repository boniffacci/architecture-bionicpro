using System;
using System.Security.Claims;

namespace ReportApi.Extensions
{
    public static class ClaimsPrincipalExtensions
    {
        public static TId GetUserId<TId>(this ClaimsPrincipal user)
        {
            var idClaim = user?.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrWhiteSpace(idClaim))
            {
                idClaim = "0";
            }
            var userId = (TId)Convert.ChangeType(idClaim, typeof(TId));
            return userId;
        }
    }
}
