using System.Globalization;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Options;

namespace PharmaGo.ApiGateway.Middleware
{
    /// <summary>
    /// Límites del modo "User". Se leen de la sección <c>RateLimiting</c>.
    /// </summary>
    public sealed class UserRateLimitOptions
    {
        public const string SectionName = "RateLimiting";

        /// <summary>Límite por sesión (token completo) o, sin token, por IP.</summary>
        public int MaxRequestsPerMinute { get; set; } = 100;
        public int MaxRequestsPerHour { get; set; } = 1000;

        /// <summary>
        /// Techo agregado por IP de conexión, aplicado a TODA solicitud (con o sin token).
        /// Impide evadir el límite rotando valores de Authorization y permite que varios
        /// usuarios legítimos compartan una IP (NAT) con un margen mayor.
        /// </summary>
        public int IpMaxRequestsPerMinute { get; set; } = 300;
        public int IpMaxRequestsPerHour { get; set; } = 3000;
    }

    /// <summary>
    /// Rate limiting por sesión e IP.
    /// La identidad NO se toma de headers controlados por el cliente (X-User-Id,
    /// X-Forwarded-For, X-Real-IP): la IP es <see cref="ConnectionInfo.RemoteIpAddress"/>,
    /// que solo cambia si <c>UseForwardedHeaders</c> recibió la solicitud de un proxy
    /// configurado como confiable. El token se usa completo y hasheado.
    /// </summary>
    public class UserRateLimitMiddleware
    {
        private readonly RequestDelegate _next;
        private readonly FixedWindowRateLimiter _limiter;
        private readonly UserRateLimitOptions _options;
        private readonly ILogger<UserRateLimitMiddleware> _logger;
        private readonly Func<DateTimeOffset> _clock;

        public UserRateLimitMiddleware(
            RequestDelegate next,
            FixedWindowRateLimiter limiter,
            IOptions<UserRateLimitOptions> options,
            ILogger<UserRateLimitMiddleware> logger)
            : this(next, limiter, options, logger, () => DateTimeOffset.UtcNow)
        {
        }

        public UserRateLimitMiddleware(
            RequestDelegate next,
            FixedWindowRateLimiter limiter,
            IOptions<UserRateLimitOptions> options,
            ILogger<UserRateLimitMiddleware> logger,
            Func<DateTimeOffset> clock)
        {
            _next = next;
            _limiter = limiter;
            _options = options.Value;
            _logger = logger;
            _clock = clock;
        }

        public async Task InvokeAsync(HttpContext context)
        {
            var ip = GetClientIp(context);
            var session = GetSessionKey(context);
            var decision = _limiter.TryAcquire(BuildRules(ip, session), _clock());

            if (!decision.Allowed)
            {
                var retryAfterSeconds = Math.Max(1, (int)Math.Ceiling(decision.RetryAfter.TotalSeconds));
                _logger.LogWarning(
                    "Rate limit exceeded for {Subject} from {ClientIp}: {Reason}",
                    session ?? "anonymous", ip, decision.Reason);

                context.Response.StatusCode = (int)HttpStatusCode.TooManyRequests;
                context.Response.Headers["Retry-After"] = retryAfterSeconds.ToString(CultureInfo.InvariantCulture);
                context.Response.Headers["X-RateLimit-Reason"] = decision.Reason;
                await context.Response.WriteAsJsonAsync(new
                {
                    error = "Too many requests",
                    message = decision.Reason,
                    retryAfter = $"{retryAfterSeconds} seconds",
                });
                return;
            }

            await _next(context);
        }

        internal IReadOnlyList<RateLimitRule> BuildRules(string ip, string? session)
        {
            var subject = session ?? $"ip:{ip}";
            return new[]
            {
                new RateLimitRule($"ip-total:{ip}", _options.IpMaxRequestsPerMinute, TimeSpan.FromMinutes(1)),
                new RateLimitRule($"ip-total:{ip}", _options.IpMaxRequestsPerHour, TimeSpan.FromHours(1)),
                new RateLimitRule(subject, _options.MaxRequestsPerMinute, TimeSpan.FromMinutes(1)),
                new RateLimitRule(subject, _options.MaxRequestsPerHour, TimeSpan.FromHours(1)),
            };
        }

        internal static string GetClientIp(HttpContext context)
        {
            var address = context.Connection.RemoteIpAddress;
            if (address is null)
            {
                return "unknown";
            }

            return (address.IsIPv4MappedToIPv6 ? address.MapToIPv4() : address).ToString();
        }

        /// <summary>
        /// Clave de sesión derivada del valor completo de Authorization (SHA-256 truncado).
        /// No se registran ni guardan tokens en claro.
        /// </summary>
        internal static string? GetSessionKey(HttpContext context)
        {
            var raw = context.Request.Headers.Authorization.ToString();
            if (raw.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
            {
                raw = raw[7..];
            }

            raw = raw.Trim();
            if (raw.Length == 0)
            {
                return null;
            }

            var hash = SHA256.HashData(Encoding.UTF8.GetBytes(raw));
            return $"session:{Convert.ToHexString(hash, 0, 8).ToLowerInvariant()}";
        }
    }

    public static class UserRateLimitMiddlewareExtensions
    {
        public static IApplicationBuilder UseUserRateLimit(this IApplicationBuilder builder)
        {
            return builder.UseMiddleware<UserRateLimitMiddleware>();
        }
    }
}
