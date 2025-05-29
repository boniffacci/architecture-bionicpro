# syntax=docker/dockerfile:1-labs

# Установить базовый образ .NET SDK для сборки
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /build

COPY Backend/Program.cs .
COPY Backend/Backend.csproj .
COPY Backend/AuthorizationResultTransformer.cs .
COPY Backend/appsettings.json .

RUN dotnet publish Backend.csproj -c Release -r linux-x64 --no-self-contained -o /out

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS prod
WORKDIR /app
COPY --from=build /out .

CMD ["dotnet", "Backend.dll"]