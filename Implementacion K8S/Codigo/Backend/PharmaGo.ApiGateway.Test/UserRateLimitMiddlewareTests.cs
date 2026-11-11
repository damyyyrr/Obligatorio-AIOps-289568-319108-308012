using System.Net;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using PharmaGo.ApiGateway.Middleware;

namespace PharmaGo.ApiGateway.Test
{
    [TestClass]
    public class UserRateLimitMiddlewareTests
    {
        private static readonly DateTimeOffset T0 = new(2026, 11, 11, 12, 0, 5, TimeSpan.Zero);

        private DateTimeOffset _now;
        private FixedWindowRateLimiter _limiter = null!;
        private UserRateLimitMiddleware _middleware = null!;
        private int _forwarded;

        [TestInitialize]
        public void Setup()
        {
            _now = T0;
            _forwarded = 0;
            _limiter = new FixedWindowRateLimiter();
            var options = Options.Create(new UserRateLimitOptions
            {
                MaxRequestsPerMinute = 5,
                MaxRequestsPerHour = 50,
                IpMaxRequestsPerMinute = 12,
                IpMaxRequestsPerHour = 100,
            });
            _middleware = new UserRateLimitMiddleware(
                _ => { Interlocked.Increment(ref _forwarded); return Task.CompletedTask; },
                _limiter, options, NullLogger<UserRateLimitMiddleware>.Instance, () => _now);
        }

        private async Task<HttpContext> SendContext(string ip = "10.0.0.1", string? token = null, Action<HttpRequest>? extra = null)
        {
            var context = new DefaultHttpContext();
            context.Connection.RemoteIpAddress = IPAddress.Parse(ip);
            context.Response.Body = new MemoryStream();
            if (token is not null)
            {
                context.Request.Headers.Authorization = token;
            }
            extra?.Invoke(context.Request);
            await _middleware.InvokeAsync(context);
            return context;
        }

        private async Task<int> Send(string ip = "10.0.0.1", string? token = null, Action<HttpRequest>? extra = null)
            => (await SendContext(ip, token, extra)).Response.StatusCode;

        [TestMethod]
        public async Task AnonymousClient_IsLimitedPerIp_AndGets429WithRetryAfter()
        {
            for (var i = 0; i < 5; i++)
            {
                Assert.AreEqual(200, await Send());
            }

            var rejected = await SendContext();

            Assert.AreEqual(429, rejected.Response.StatusCode);
            Assert.AreEqual("55", rejected.Response.Headers["Retry-After"].ToString());
            Assert.AreEqual(5, _forwarded);
        }

        [TestMethod]
        public async Task SpoofedIdentityHeaders_DoNotCreateNewBuckets()
        {
            var statuses = new List<int>();
            for (var i = 0; i < 10; i++)
            {
                var n = i;
                statuses.Add(await Send(extra: request =>
                {
                    request.Headers["X-User-Id"] = $"victim-{n}";
                    request.Headers["X-Forwarded-For"] = $"203.0.113.{n}";
                    request.Headers["X-Real-IP"] = $"198.51.100.{n}";
                }));
            }

            Assert.AreEqual(5, statuses.Count(s => s == 200));
            Assert.AreEqual(5, statuses.Count(s => s == 429));
        }

        [TestMethod]
        public async Task RotatingTokens_AreCappedByAggregateIpLimit()
        {
            var accepted = 0;
            for (var i = 0; i < 30; i++)
            {
                if (await Send(token: $"Bearer {Guid.NewGuid()}") == 200)
                {
                    accepted++;
                }
            }

            Assert.AreEqual(12, accepted);
        }

        [TestMethod]
        public async Task TokensSharingPrefix_HaveIndependentLimits()
        {
            // El middleware anterior usaba solo los 8 primeros caracteres del token.
            const string tokenA = "Bearer 12345678-aaaa-4000-8000-000000000001";
            const string tokenB = "Bearer 12345678-bbbb-4000-8000-000000000002";

            for (var i = 0; i < 5; i++)
            {
                Assert.AreEqual(200, await Send(token: tokenA));
            }

            Assert.AreEqual(429, await Send(token: tokenA));
            Assert.AreEqual(200, await Send(token: tokenB));
        }

        [TestMethod]
        public async Task LegitimateUsersBehindSameIp_KeepTheirOwnQuota()
        {
            for (var user = 0; user < 2; user++)
            {
                for (var i = 0; i < 5; i++)
                {
                    Assert.AreEqual(200, await Send(ip: "192.0.2.10", token: $"Bearer user-{user}-token"));
                }
            }

            Assert.AreEqual(10, _forwarded);
            Assert.AreEqual(200, await Send(ip: "192.0.2.99"));
        }

        [TestMethod]
        public async Task Window_ResetsAfterItExpires()
        {
            for (var i = 0; i < 5; i++)
            {
                await Send();
            }
            Assert.AreEqual(429, await Send());

            _now = T0.AddMinutes(1);
            Assert.AreEqual(200, await Send());
        }

        [TestMethod]
        public async Task HourlyLimit_AppliesAcrossMinuteWindows()
        {
            var accepted = 0;
            for (var minute = 0; minute < 15; minute++)
            {
                _now = new DateTimeOffset(2026, 11, 11, 12, minute, 0, TimeSpan.Zero);
                for (var i = 0; i < 5; i++)
                {
                    if (await Send(token: "Bearer steady-user") == 200)
                    {
                        accepted++;
                    }
                }
            }

            Assert.AreEqual(50, accepted);
        }

        [TestMethod]
        public async Task ConcurrentBurst_NeverExceedsLimit()
        {
            var results = await Task.WhenAll(Enumerable.Range(0, 200)
                .Select(_ => Task.Run(() => Send(token: "Bearer burst"))));

            Assert.AreEqual(5, results.Count(s => s == 200));
            Assert.AreEqual(195, results.Count(s => s == 429));
            Assert.AreEqual(5, _forwarded);
        }

        [TestMethod]
        public async Task RejectedRequests_DoNotConsumeAggregateQuota()
        {
            for (var i = 0; i < 20; i++)
            {
                await Send(token: "Bearer noisy");
            }

            // "noisy" consumió solo 5 del agregado de 12; quedan 7 para otro usuario, que tiene tope propio de 5.
            var accepted = 0;
            for (var i = 0; i < 10; i++)
            {
                if (await Send(token: "Bearer quiet") == 200)
                {
                    accepted++;
                }
            }

            Assert.AreEqual(5, accepted);
            Assert.AreEqual(200, await Send(token: "Bearer third"));
            Assert.AreEqual(200, await Send(token: "Bearer third"));
            Assert.AreEqual(429, await Send(token: "Bearer third"));
        }

        [TestMethod]
        public void SessionKey_IsHashed_AndNeverContainsToken()
        {
            var context = new DefaultHttpContext();
            context.Request.Headers.Authorization = "Bearer 0f8fad5b-d9cb-469f-a165-70867728950e";

            var key = UserRateLimitMiddleware.GetSessionKey(context);

            Assert.IsNotNull(key);
            StringAssert.StartsWith(key, "session:");
            Assert.IsFalse(key.Contains("0f8fad5b"));
        }

        [TestMethod]
        public void ClientIp_NormalizesIpv4MappedAddresses()
        {
            var context = new DefaultHttpContext();
            context.Connection.RemoteIpAddress = IPAddress.Parse("::ffff:10.1.2.3");

            Assert.AreEqual("10.1.2.3", UserRateLimitMiddleware.GetClientIp(context));
        }

        [TestMethod]
        public void ExpiredWindows_AreSwept()
        {
            _limiter.TryAcquire(new[] { new RateLimitRule("k", 1, TimeSpan.FromMinutes(1)) }, T0);
            Assert.AreEqual(1, _limiter.TrackedWindows);

            _limiter.TryAcquire(new[] { new RateLimitRule("other", 1, TimeSpan.FromMinutes(1)) }, T0.AddMinutes(3));
            Assert.AreEqual(1, _limiter.TrackedWindows);
        }
    }
}
