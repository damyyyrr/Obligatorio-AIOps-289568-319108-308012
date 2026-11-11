using System.Diagnostics;
using Instrumentation;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Moq;

namespace PharmaGo.Test.WebApi.Test
{
    [TestClass]
    public class StructuredLoggerTraceTest
    {
        private sealed class ScopeCapture : ILogger<StructuredLogger>
        {
            public List<Dictionary<string, object>> Scopes { get; } = new();

            public IDisposable BeginScope<TState>(TState state)
            {
                if (state is Dictionary<string, object> data)
                {
                    Scopes.Add(new Dictionary<string, object>(data));
                }
                return new NoopDisposable();
            }

            public bool IsEnabled(LogLevel logLevel) => true;

            public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception,
                Func<TState, Exception?, string> formatter) { }

            private sealed class NoopDisposable : IDisposable { public void Dispose() { } }
        }

        private static (StructuredLogger Logger, ScopeCapture Capture) Create()
        {
            var capture = new ScopeCapture();
            var environment = new Mock<IHostEnvironment>();
            environment.Setup(e => e.ApplicationName).Returns("PharmaGo.Test");
            var accessor = new Mock<IHttpContextAccessor>();
            accessor.Setup(a => a.HttpContext).Returns((HttpContext?)null);
            return (new StructuredLogger(capture, environment.Object, accessor.Object), capture);
        }

        [TestMethod]
        public void InsideActivity_LogsTraceAndSpanIds()
        {
            var (logger, capture) = Create();
            using var activity = new Activity("test-operation");
            activity.SetIdFormat(ActivityIdFormat.W3C);
            activity.Start();

            logger.LogInformation("evento de prueba");

            var scope = capture.Scopes.Single();
            Assert.AreEqual(activity.TraceId.ToHexString(), scope["trace_id"]);
            Assert.AreEqual(activity.SpanId.ToHexString(), scope["span_id"]);
            Assert.AreEqual(32, ((string)scope["trace_id"]).Length);
        }

        [TestMethod]
        public void WithoutActivity_DoesNotInventTraceIds()
        {
            var (logger, capture) = Create();
            Assert.IsNull(Activity.Current);

            logger.LogWarning("sin traza");

            Assert.IsFalse(capture.Scopes.Single().ContainsKey("trace_id"));
        }
    }
}
