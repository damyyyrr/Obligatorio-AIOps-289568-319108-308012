using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace PharmaGo.DataAccess;

public sealed class SqlReadinessCheck : IHealthCheck
{
    private readonly DbContext _database;
    private readonly string _query;

    public SqlReadinessCheck(DbContext database, string query)
    {
        _database = database;
        _query = query;
    }

    public async Task<HealthCheckResult> CheckHealthAsync(HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await _database.Database.ExecuteSqlRawAsync(_query, cancellationToken);
            return HealthCheckResult.Healthy();
        }
        catch (SqlException)
        {
            return HealthCheckResult.Unhealthy("SQL or the required table is unavailable.");
        }
    }
}
