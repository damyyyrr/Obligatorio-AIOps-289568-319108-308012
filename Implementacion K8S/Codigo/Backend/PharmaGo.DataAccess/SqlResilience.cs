using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Configuration;

namespace PharmaGo.DataAccess
{
    /// <summary>
    /// Límites de espera hacia SQL Server (issue #10 / RES-03).
    /// Orden de timeouts: conexión 5 s y comando 8 s, ambos por debajo del timeout del
    /// Gateway (10 s), para que el servicio responda su propio error antes de que el
    /// Gateway corte y libere el hilo. No se habilitan reintentos (EnableRetryOnFailure):
    /// aprobar compras o cambiar stock no es idempotente y un reintento podría duplicarlo.
    /// </summary>
    public static class SqlResilience
    {
        public const int DefaultConnectTimeoutSeconds = 5;
        public const int DefaultCommandTimeoutSeconds = 8;

        public static string ConnectionString(IConfiguration configuration)
        {
            var raw = configuration.GetConnectionString("DefaultConnection") ?? string.Empty;
            return ApplyConnectionLimits(raw, ConnectTimeoutSeconds(configuration));
        }

        /// <summary>
        /// Fija Connect Timeout y desactiva el bloqueo del pool tras un fallo
        /// (PoolBlockingPeriod=NeverBlock): con el valor por defecto, después de que SQL
        /// vuelve el pool puede seguir fallando de inmediato hasta 1 minuto.
        /// </summary>
        public static string ApplyConnectionLimits(string connectionString, int connectTimeoutSeconds)
        {
            if (string.IsNullOrWhiteSpace(connectionString))
            {
                return connectionString;
            }

            var builder = new SqlConnectionStringBuilder(connectionString)
            {
                ConnectTimeout = connectTimeoutSeconds,
                PoolBlockingPeriod = PoolBlockingPeriod.NeverBlock,
            };
            return builder.ConnectionString;
        }

        public static void ApplyCommandTimeout(SqlServerDbContextOptionsBuilder options, IConfiguration configuration)
        {
            options.CommandTimeout(CommandTimeoutSeconds(configuration));
        }

        public static int ConnectTimeoutSeconds(IConfiguration configuration)
            => Positive(configuration["Database:ConnectTimeoutSeconds"], DefaultConnectTimeoutSeconds);

        public static int CommandTimeoutSeconds(IConfiguration configuration)
            => Positive(configuration["Database:CommandTimeoutSeconds"], DefaultCommandTimeoutSeconds);

        private static int Positive(string? value, int fallback)
            => int.TryParse(value, out var parsed) && parsed > 0 ? parsed : fallback;
    }
}
