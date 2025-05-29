using Microsoft.AspNetCore.Authentication.JwtBearer;
using Keycloak.AuthServices.Authorization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.IdentityModel.Tokens;
using System.Security.Claims;
using System.IdentityModel.Tokens.Jwt;

namespace Backend
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var builder = WebApplication.CreateBuilder(args);

            // Add services to the container.
            builder.Services.AddAuthentication()
                .AddJwtBearer(JwtBearerDefaults.AuthenticationScheme, opt => 
                {
                    string keycloakURL = Environment.GetEnvironmentVariable("BACKEND_APP_KEYCLOAK_URL")
                        ?? throw new Exception("Не задана переменная окружения BACKEND_APP_KEYCLOAK_URL");

                    string keycloakRealm = Environment.GetEnvironmentVariable("BACKEND_APP_KEYCLOAK_REALM")
                        ?? throw new Exception("Не задана пременная окружения BACKEND_APP_KEYCLOAK_REALM");

					opt.Authority = $"{keycloakURL}/realms/{keycloakRealm}"; //TODO: сделать красиво
                    opt.RequireHttpsMetadata = false;
                    opt.MetadataAddress = $"{keycloakURL}/realms/{keycloakRealm}/.well-known/openid-configuration";
                    opt.IncludeErrorDetails = true;
                    opt.TokenValidationParameters = new Microsoft.IdentityModel.Tokens.TokenValidationParameters
                    {
                        NameClaimType = ClaimTypes.Name,
                        RoleClaimType = ClaimTypes.Role,
                        ValidateIssuer = true,
                        ValidIssuer = $"{keycloakURL}/realms/{keycloakRealm}",
                        ValidateAudience = false,
                        ValidateIssuerSigningKey = false,
						SignatureValidator = delegate (string token, TokenValidationParameters parameters)
						{
							return new Microsoft.IdentityModel.JsonWebTokens.JsonWebToken(token);
						},
					};
                });

            // Конфигурируем политику авторизации
			builder.Services
				.AddAuthorizationBuilder()
				.AddPolicy("ProtheticUser", (pb) =>
				{
					pb.RequireRealmRoles("prothetic_user"); // требуемая роль
				});
            // Подключаем "преобразователь" кода ответа
            builder.Services.AddSingleton<IAuthorizationMiddlewareResultHandler, AuthorizationResultTransformer>();

			builder.Services.AddKeycloakAuthorization( (opt) => 
            {
                opt.Realm = Environment.GetEnvironmentVariable("BACKEND_APP_KEYCLOAK_REALM")
                    ?? throw new Exception("Не задана пременная окружения BACKEND_APP_KEYCLOAK_REALM");
                opt.AuthServerUrl = Environment.GetEnvironmentVariable("BACKEND_APP_KEYCLOAK_URL")
                    ?? throw new Exception("Не задана переменная окружения BACKEND_APP_KEYCLOAK_URL");
                opt.VerifyTokenAudience = false;
                opt.SslRequired = "none";
                opt.Resource = Environment.GetEnvironmentVariable("BACKEND_APP_KEYCLOAK_CLIENT_ID")
                    ?? throw new Exception("Не задана пременная окружения BACKEND_APP_KEYCLOAK_CLIENT_ID");
			});

            builder.Services.AddCors(options =>
            {
                options.AddDefaultPolicy(policy => { policy.AllowAnyOrigin(); policy.AllowAnyHeader(); });
            });
            
            var app = builder.Build();

            app.UseAuthentication();
			app.UseAuthorization();
            app.UseCors();


            app.MapGet("/reports", (HttpContext context) =>
            {
                return "{\"hello\": 1}";
            }).RequireAuthorization("ProtheticUser");

            app.Run();
        }
    }
}
