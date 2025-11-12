FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:8.0 AS build-stage
WORKDIR /app

COPY api.csproj api.csproj
RUN dotnet restore --verbosity minimal
COPY . .

RUN dotnet publish api.csproj -c Release -o out

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build-stage /app/out .

ENTRYPOINT ["dotnet", "api.dll"]
EXPOSE 8080
