using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using PharmaGo.UsersService.BusinessLogic;
using PharmaGo.DataAccess;
using PharmaGo.DataAccess.Repositories;
using PharmaGo.Domain.Entities;
using PharmaGo.UsersService.IBusinessLogic;
using PharmaGo.IDataAccess;
using InstrumentationInterface;
using Instrumentation;


namespace PharmaGo.UsersService.Factory
{
    public static class ServiceFactory
    {

        public static void RegisterBusinessLogicServices(this IServiceCollection serviceCollection, IConfiguration configuration)
        {
            serviceCollection.AddScoped<ILoginManager, LoginManager>();
            serviceCollection.AddScoped<IUsersManager, UsersManager>();
            serviceCollection.AddScoped<IInvitationManager, InvitationManager>();
            serviceCollection.AddScoped<IRoleManager, RoleManager>();
            
            serviceCollection.AddHttpClient<PharmaGo.UsersService.HttpClients.PharmacyServiceClient>(client =>
            {
                var serviceUrl = configuration["ServiceUrls:PharmacyService"] ?? "http://127.0.0.1:5002";
                client.BaseAddress = new Uri(serviceUrl);
                client.Timeout = TimeSpan.FromSeconds(30);
            });
        }

        public static void RegisterDataAccessServices(this IServiceCollection serviceCollection, IConfiguration configuration)
        {
            serviceCollection.AddScoped<IRepository<User>, UsersRepository>();
            serviceCollection.AddScoped<IRepository<Session>, SessionRepository>();
            serviceCollection.AddScoped<IRepository<Invitation>, InvitationRepository>();
            serviceCollection.AddScoped<IRepository<Role>, RoleRepository>();
            serviceCollection.AddScoped<IRepository<Pharmacy>, PharmacyRepository>();

            serviceCollection.AddDbContext<DbContext, PharmacyGoDbContext>(options =>
            {
                options.UseSqlServer(
                    configuration.GetConnectionString("DefaultConnection"),
                    sqlOptions => { sqlOptions.MigrationsAssembly("PharmaGo.DataAccess"); });
                options.ConfigureWarnings(w =>
                {
                    w.Ignore(RelationalEventId.CommandExecuted);
                    w.Ignore(RelationalEventId.CommandError);
                });
            });
            serviceCollection.AddSingleton<ICustomMetrics, CustomMetrics>();
            serviceCollection.AddSingleton<IStructuredLogger, StructuredLogger>();
        }

    }
}

