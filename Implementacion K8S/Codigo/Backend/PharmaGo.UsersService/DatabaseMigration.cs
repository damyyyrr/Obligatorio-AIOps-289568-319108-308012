using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Storage;
using PharmaGo.UsersService.Factory;
using System.Data;
using Instrumentation;

namespace PharmaGo.UsersService;

internal static class DatabaseMigration
{
    private const string LockResource = "PharmaGo.SchemaMigration";
    private const int LockTimeoutSeconds = 120;

    public static int Run(string[] args)
    {
        ILogger? log = null;
        try
        {
            using var host = Host.CreateDefaultBuilder(args)
                .ConfigureLogging(logging => logging.SuppressEfAndSqlClientLogs())
                .ConfigureServices((context, services) => services.RegisterDataAccessServices(context.Configuration))
                .Build();
            // Logger JSON de la aplicación (issue #12): la salida del Job también se centraliza.
            log = host.Services.GetRequiredService<ILoggerFactory>().CreateLogger("PharmaGo.DatabaseMigration");
            using var scope = host.Services.CreateScope();
            var database = scope.ServiceProvider.GetRequiredService<DbContext>();
            Migrate(database, log);
            return 0;
        }
        catch (SqlException error)
        {
            Report(log, $"SQL migration failed (SQL error {error.Number}).");
        }
        catch (InvalidOperationException error)
        {
            // Only messages from our own validation can be printed safely.
            Report(log, error is MigrationRejected ? error.Message : "SQL migration failed (invalid operation).");
        }
        catch (Exception error)
        {
            Report(log, $"SQL migration failed ({error.GetType().Name}).");
        }
        return 1;
    }

    private static void Report(ILogger? log, string message)
    {
        // Sin host (falló la configuración) no hay logger: se mantiene stderr.
        if (log is null) Console.Error.WriteLine(message);
        else log.LogError("{MigrationMessage}", message);
    }

    private static void Migrate(DbContext database, ILogger log)
    {
        var settings = new SqlConnectionStringBuilder(database.Database.GetConnectionString());
        var catalog = settings.InitialCatalog;
        if (string.IsNullOrWhiteSpace(catalog) ||
            new[] { "master", "model", "msdb", "tempdb" }.Contains(catalog, StringComparer.OrdinalIgnoreCase))
        {
            throw new MigrationRejected("Specify an application database in DefaultConnection.");
        }

        settings.InitialCatalog = "master";
        settings.Pooling = false;
        settings.ConnectRetryCount = 0;
        using var connection = new SqlConnection(settings.ConnectionString);
        connection.Open();

        // Master exists even on a fresh instance. Use the same SQL session for EF's schema changes.
        using (var command = connection.CreateCommand())
        {
            command.CommandTimeout = LockTimeoutSeconds + 5;
            command.CommandText = "DECLARE @status int; EXEC @status = sys.sp_getapplock " +
                "@Resource = @resource, @LockMode = 'Exclusive', @LockOwner = 'Session', @LockTimeout = @timeout; SELECT @status;";
            command.Parameters.Add("@resource", SqlDbType.NVarChar, 255).Value = LockResource;
            command.Parameters.Add("@timeout", SqlDbType.Int).Value = LockTimeoutSeconds * 1000;
            log.LogInformation("Waiting for the SQL migration lock.");
            var status = (int)command.ExecuteScalar()!;
            if (status < 0)
            {
                throw new MigrationRejected($"SQL migration lock could not be acquired (status {status}).");
            }
            log.LogInformation("SQL migration lock acquired (status {LockStatus}).", status);
        }

        // Let the EF SQL Server provider provision a fresh catalog with its normal settings.
        var creator = database.GetService<IRelationalDatabaseCreator>();
        if (!creator.Exists())
        {
            creator.Create();
        }
        connection.ChangeDatabase(catalog);
        database.Database.SetDbConnection(connection);

        var known = database.Database.GetMigrations().ToArray();
        var applied = database.Database.GetAppliedMigrations().ToArray();
        if (known.Length == 0 || !applied.SequenceEqual(known.Take(applied.Length)))
        {
            throw new MigrationRejected("This image cannot migrate the database history. Use the matching migration image.");
        }

        // El DbContext de la aplicación limita cada comando a 8 s (SqlResilience); una migración puede tardar más.
        database.Database.SetCommandTimeout(TimeSpan.FromMinutes(10));

        var pending = known.Length - applied.Length;
        log.LogInformation("Pending EF migrations: {PendingMigrations}.", pending);
        if (pending > 0)
        {
            database.Database.Migrate();
        }
        log.LogInformation("SQL migration completed.");
    }

    private sealed class MigrationRejected : InvalidOperationException
    {
        public MigrationRejected(string message) : base(message) { }
    }
}
