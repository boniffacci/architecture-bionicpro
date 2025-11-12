using Microsoft.AspNetCore.Authorization;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApiDocument(config =>
{
  config.DocumentName = "api";
  config.Title = "api v1";
  config.Version = "v1";
});
var keycloak = Environment.GetEnvironmentVariable("APP_KEYCLOAK_URL");
var realm = Environment.GetEnvironmentVariable("APP_KEYCLOAK_REALM");
var clientId = Environment.GetEnvironmentVariable("APP_KEYCLOAK_CLIENT_ID");
var secret = Environment.GetEnvironmentVariable("APP_KEYCLOAK_CLIENT_SECRET");

builder.Services.AddTransient<Microsoft.AspNetCore.Authentication.IClaimsTransformation, ClaimsTransformer>();

// https://dev.to/kayesislam/integrating-openid-connect-to-your-application-stack-25ch
builder.Services
    .AddAuthentication()
    .AddJwtBearer(x =>
    {
      x.RequireHttpsMetadata = false;
      x.MetadataAddress = $"{keycloak}/realms/{realm}/.well-known/openid-configuration";
      x.ClaimsIssuer = $"{keycloak}/realms/{realm}";
      x.TokenValidationParameters = new Microsoft.IdentityModel.Tokens.TokenValidationParameters
      {
        ValidateIssuer = true,
        ValidateAudience = false,
        ValidIssuers = new[] { $"{keycloak}/realms/{realm}" },
        // IDX10500: Signature validation failed. No security keys were provided to validate the signature on K8s
        SignatureValidator = delegate (string token, Microsoft.IdentityModel.Tokens.TokenValidationParameters parameters)
        {
          var jwt = new Microsoft.IdentityModel.JsonWebTokens.JsonWebToken(token);
          return jwt;
        }

      };
    });

builder.Services.AddAuthorization(x => x.AddPolicy("reports", y =>
{
  y.RequireRole("prothetic_user");
}));
builder.Services.AddCors();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.UseCors(x => x.AllowAnyMethod().AllowAnyHeader().AllowAnyOrigin());


app.MapGet("/reports", [Authorize("reports")] (HttpContext context) =>
{
  return Guid.NewGuid().ToString();
});
app.UseOpenApi();
app.UseSwaggerUi(config =>
{
  config.DocumentTitle = "api";
  config.Path = "/swagger";
  config.DocumentPath = "/swagger/{documentName}/swagger.json";
  config.DocExpansion = "list";
});


app.Run();
