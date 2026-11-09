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
        try
        {
            using var host = Host.CreateDefaultBuilder(args)
                .ConfigureLogging(logging => logging.SuppressEfAndSqlClientLogs())
                .ConfigureServices((context, services) => services.RegisterDataAccessServices(context.Configuration))
                .Build();
            using var scope = host.Services.CreateScope();
            var database = scope.ServiceProvider.GetRequiredService<DbContext>();
            Migrate(database);
            return 0;
        }
        catch (SqlException error)
        {
            Console.Error.WriteLine($"SQL migration failed (SQL error {error.Number}).");
        }
        catch (InvalidOperationException error)
        {
            // Only messages from our own validation can be printed safely.
            Console.Error.WriteLine(error is MigrationRejected ? error.Message : "SQL migration failed (invalid operation).");
        }
        catch (Exception error)
        {
            Console.Error.WriteLine($"SQL migration failed ({error.GetType().Name}).");
        }
        return 1;
    }

    private static void Migrate(DbContext database)
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
            Console.WriteLine("Waiting for the SQL migration lock.");
            var status = (int)command.ExecuteScalar()!;
            if (status < 0)
            {
                throw new MigrationRejected($"SQL migration lock could not be acquired (status {status}).");
            }
            Console.WriteLine($"SQL migration lock acquired (status {status}).");
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

        var pending = known.Length - applied.Length;
        Console.WriteLine($"Pending EF migrations: {pending}.");
        if (pending > 0)
        {
            database.Database.Migrate();
        }
        Console.WriteLine("SQL migration completed.");
    }

    private sealed class MigrationRejected : InvalidOperationException
    {
        public MigrationRejected(string message) : base(message) { }
    }
}
