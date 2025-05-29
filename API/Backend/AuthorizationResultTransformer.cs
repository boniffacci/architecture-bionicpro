using Keycloak.AuthServices.Authorization.Requirements;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Authorization.Policy;
using System.Net;

namespace Backend
{
	/// <summary>
	/// Класс понадобился для изменения кода ответа с 403 на 401 согласно заданию
	/// </summary>
	public class AuthorizationResultTransformer: IAuthorizationMiddlewareResultHandler
	{
		private readonly IAuthorizationMiddlewareResultHandler _handler;

		public AuthorizationResultTransformer()
		{
			_handler = new AuthorizationMiddlewareResultHandler();
		}

		public async Task HandleAsync(
			RequestDelegate requestDelegate,
			HttpContext httpContext,
			AuthorizationPolicy authorizationPolicy,
			PolicyAuthorizationResult policyAuthorizationResult)
		{
			if (policyAuthorizationResult.Forbidden && policyAuthorizationResult.AuthorizationFailure != null)
			{
				if (policyAuthorizationResult.AuthorizationFailure.FailedRequirements.Any(requirement => requirement is RealmAccessRequirement))
				{
					httpContext.Response.StatusCode = (int)HttpStatusCode.Unauthorized;
					return;
				}
			}

			await _handler.HandleAsync(requestDelegate, httpContext, authorizationPolicy, policyAuthorizationResult);
		}
	}
}
