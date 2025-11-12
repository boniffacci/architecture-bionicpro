using Microsoft.AspNetCore.Authentication;
using System.Security.Claims;

public class ClaimsTransformer : IClaimsTransformation
{
  public Task<ClaimsPrincipal> TransformAsync(ClaimsPrincipal principal)
  {
    ClaimsIdentity claimsIdentity = (ClaimsIdentity)principal.Identity;

    // flatten realm_access because Microsoft identity model doesn't support nested claims
    // by map it to Microsoft identity model, because automatic JWT bearer token mapping already processed here
    if (claimsIdentity.IsAuthenticated && claimsIdentity.HasClaim((claim) => claim.Type == "realm_access"))
    {
      var realmAccessClaim = claimsIdentity.FindFirst((claim) => claim.Type == "realm_access");
      var realmAccessAsDict = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, string[]>>(realmAccessClaim.Value);
      if (realmAccessAsDict["roles"] != null)
      {
        foreach (var role in realmAccessAsDict["roles"])
        {
          claimsIdentity.AddClaim(new Claim(ClaimTypes.Role, role));
        }
      }
    }

    return Task.FromResult(principal);
  }
}
