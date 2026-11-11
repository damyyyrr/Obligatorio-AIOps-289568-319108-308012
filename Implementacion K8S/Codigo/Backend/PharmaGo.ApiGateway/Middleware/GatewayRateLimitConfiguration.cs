using AspNetCoreRateLimit;
using Microsoft.Extensions.Options;

namespace PharmaGo.ApiGateway.Middleware
{
    /// <summary>
    /// Por defecto AspNetCoreRateLimit (con EnableEndpointRateLimiting) cuenta por verbo + ruta
    /// concreta, de modo que la regla "*" otorgaba 100/min a CADA ruta distinta
    /// (/api/drug/1, /api/drug/2, ...). Con <see cref="EndpointCounterKeyBuilder"/> el contador
    /// se agrupa por la regla: "*" es un total por IP y "POST:/api/login" conserva su propio límite.
    /// </summary>
    public sealed class GatewayRateLimitConfiguration : RateLimitConfiguration
    {
        public GatewayRateLimitConfiguration(
            IOptions<IpRateLimitOptions> ipOptions,
            IOptions<ClientRateLimitOptions> clientOptions)
            : base(ipOptions, clientOptions)
        {
        }

        public override ICounterKeyBuilder EndpointCounterKeyBuilder { get; } = new EndpointCounterKeyBuilder();

        /// <summary>
        /// La librería agrega por defecto un resolvedor que lee la IP de "X-Real-IP" (aunque no
        /// figure en appsettings), lo que permitía rotar ese header para evadir el límite.
        /// Solo se usa la IP de la conexión; si hay un proxy confiable, <c>UseForwardedHeaders</c>
        /// ya la reemplazó antes de llegar aquí.
        /// </summary>
        public override void RegisterResolvers()
        {
            IpResolvers.Add(new IpConnectionResolveContributor());
        }
    }
}
