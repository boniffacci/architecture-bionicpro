using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.IdentityModel.Tokens;
using ReportApi.Repositories;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();

var issuingKeys = await GetIssuerSigningKey(
    $"{builder.Configuration["Authentication:Keycloak:Server"]}/realms/{builder.Configuration["Authentication:Keycloak:Realm"]}");

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
        .AddJwtBearer(options =>
        {
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidateIssuer = true,
                ValidIssuer =
                    $"{builder.Configuration["Authentication:Keycloak:Issuer"]}/realms/{builder.Configuration["Authentication:Keycloak:Realm"]}",

                ValidateAudience = false,

                ValidateIssuerSigningKey = true,
                ValidateLifetime = false,

                IssuerSigningKeyResolver = (token, securityToken, kid, parameters) => 
                {
                    return issuingKeys;
                }
            };

            options.RequireHttpsMetadata = false; // Only in develop environment
            options.SaveToken = true;
        });


builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll",
        builder =>
        {
            builder.AllowAnyOrigin()
                   .AllowAnyHeader()
                   .AllowAnyMethod();
        });
});

var connectionString = builder.Configuration.GetConnectionString("ClickHouseConnection");

builder.Services.AddScoped(x => new ReportRepository(connectionString));

builder.Services.AddAuthorization();

var app = builder.Build();

// Configure the HTTP request pipeline.

app.UseAuthentication();
app.UseAuthorization();
app.UseCors("AllowAll");
app.MapControllers();

app.Run("http://*:8000");

static async Task<IList<SecurityKey>> GetIssuerSigningKey(string server)
{
    var client = new HttpClient();
    var keyUri = $"{server}/protocol/openid-connect/certs";
    var response = await client.GetAsync(keyUri);
    var keys = new JsonWebKeySet(await response.Content.ReadAsStringAsync());

    return keys.GetSigningKeys();
}