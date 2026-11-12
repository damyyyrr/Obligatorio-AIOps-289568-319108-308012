"""Opt-in: ejecuta el agente real en un contenedor efímero, sin red ni datos.

PHARMAGO_AGENT_TEST_IMAGE=pharmago-baseline/pharmacy:local
No sustituye los seis ensayos integrales sobre PharmaGo/Kubernetes.
"""
import json
import os
from pathlib import Path
import subprocess
import time
import unittest
import uuid

SOURCE = Path(__file__).with_name("fault.sh").read_text(encoding="utf-8")


@unittest.skipUnless(os.environ.get("PHARMAGO_AGENT_TEST_IMAGE"), "Opt-in de agente Docker no habilitado")
class FaultAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "pharmago-agent-test-" + uuid.uuid4().hex[:12]
        cls.image = os.environ["PHARMAGO_AGENT_TEST_IMAGE"]
        subprocess.run(["docker", "run", "-d", "--name", cls.name, "--label", "pharmago.io/agent-regression=true",
                        "--network", "none", "--memory", "256m", "--cpus", "0.5", "--pids-limit", "64",
                        "--entrypoint", "sleep", cls.image, "300"], capture_output=True, check=True, timeout=40)

    @classmethod
    def tearDownClass(cls):
        # Solo el contenedor efímero cuyo nombre aleatorio acabamos de crear.
        subprocess.run(["docker", "rm", "-f", cls.name], capture_output=True, check=True, timeout=30)

    def command(self, mode, scenario, run_id, seconds=3, until=None):
        return ["docker", "exec", "-i", self.name, "sh", "-s", "--", mode, scenario, run_id,
                str(seconds), "4", str(until if until is not None else int(time.time()) + 30)]

    def agent(self, mode, scenario, run_id, **kwargs):
        completed = subprocess.run(self.command(mode, scenario, run_id, **kwargs), input=SOURCE.encode("utf-8"),
                                   capture_output=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", errors="replace"))
        return json.loads(completed.stdout)

    def assert_no_processes_or_payload(self, run_id):
        check = 'for f in /proc/[0-9]*/environ; do [ ! -r "$f" ] || ! tr "\\000" "\\n" < "$f" | grep -qx "PHARMAGO_CHAOS_RUNID=' + run_id + '" || exit 1; done; test ! -e /tmp/pharmago-chaos-' + run_id
        subprocess.run(["docker", "exec", self.name, "sh", "-c", check], capture_output=True, check=True, timeout=15)

    def test_cancel_before_start_blocks_all_three_resource_agents(self):
        for scenario in ("cpu", "ram", "storage"):
            with self.subTest(scenario=scenario):
                run_id = uuid.uuid4().hex
                self.agent("cleanup", scenario, run_id)
                result = self.agent("run", scenario, run_id)
                self.assertEqual(result, {"injected": False, "reason": "cancelled"})
                self.assert_no_processes_or_payload(run_id)
                self.agent("clear", scenario, run_id)

    def test_absolute_deadline_blocks_start_even_after_tombstone_was_removed(self):
        for scenario in ("cpu", "ram", "storage"):
            with self.subTest(scenario=scenario):
                run_id = uuid.uuid4().hex
                self.agent("cleanup", scenario, run_id)
                self.agent("clear", scenario, run_id)
                result = self.agent("run", scenario, run_id, until=int(time.time()) - 1)
                self.assertEqual(result, {"injected": False, "reason": "expired"})
                self.assert_no_processes_or_payload(run_id)
                self.agent("clear", scenario, run_id)

    def test_active_cpu_ram_and_storage_abort_without_remaining_processes(self):
        for scenario in ("cpu", "ram", "storage"):
            with self.subTest(scenario=scenario):
                run_id = uuid.uuid4().hex
                process = subprocess.Popen(self.command("run", scenario, run_id, seconds=8),
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                process.stdin.write(SOURCE.encode("utf-8"))
                process.stdin.close()
                process.stdin = None
                try:
                    deadline = time.monotonic() + 8
                    while time.monotonic() < deadline:
                        status = self.agent("status", scenario, run_id)
                        if status["active"]:
                            break
                        time.sleep(0.1)
                    else:
                        self.fail("El agente no llegó a estar activo")
                    if scenario == "storage":
                        self.assertEqual(status["bytes"], 4 * 1048576)
                    self.agent("cleanup", scenario, run_id)
                    output, error = process.communicate(timeout=15)
                    self.assertEqual(process.returncode, 0, error)
                    self.assertTrue(json.loads(output)["injected"])
                    self.assert_no_processes_or_payload(run_id)
                    self.assertFalse(self.agent("status", scenario, run_id)["active"])
                    self.agent("clear", scenario, run_id)
                finally:
                    if process.poll() is None:
                        self.agent("cleanup", scenario, run_id)
                        process.communicate(timeout=15)

    def test_foreign_control_is_preserved(self):
        run_id = uuid.uuid4().hex
        marker = "/tmp/pharmago-chaos-" + run_id + ".cancel"
        subprocess.run(["docker", "exec", self.name, "sh", "-c", 'printf foreign > "$1"', "sh", marker], check=True, timeout=10)
        result = subprocess.run(self.command("cleanup", "cpu", run_id), input=SOURCE.encode("utf-8"),
                                capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        value = subprocess.run(["docker", "exec", self.name, "cat", marker],
                               text=True, capture_output=True, check=True, timeout=10).stdout
        self.assertEqual(value, "foreign")


if __name__ == "__main__":
    unittest.main()
