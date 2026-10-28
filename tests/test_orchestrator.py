import unittest

from fixie.models import CandidatePatch, Issue
from fixie.orchestrator import FixieOrchestrator
from fixie.providers import FakePullRequestProvider, FakeSandboxProvider
from fixie.server import run_issue


class FixieOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.issue = Issue(1, "Broken parser", "details", "acme/repo")
        self.orchestrator = FixieOrchestrator(FakeSandboxProvider(), FakePullRequestProvider())

    def test_passing_candidate_wins_and_produces_draft(self):
        failing = CandidatePatch("failing", "broken", "try one")
        passing = CandidatePatch("passing", "FIXIE_PASS", "try two")
        report = self.orchestrator.run(self.issue, [failing, passing])
        self.assertEqual("passing", report.winner.candidate.name)
        self.assertTrue(report.winner.verification.passed)
        self.assertEqual("draft", report.pull_request["status"])

    def test_candidates_are_evaluated_in_isolated_forks(self):
        patches = [CandidatePatch("one", "FIXIE_PASS", "one"), CandidatePatch("two", "FIXIE_PASS", "two")]
        report = self.orchestrator.run(self.issue, patches)
        self.assertEqual(2, len({item.sandbox_id for item in report.evaluations}))
        self.assertTrue(all(item.sandbox_id.startswith("fake-1:") for item in report.evaluations))

    def test_empty_candidate_list_is_rejected(self):
        with self.assertRaises(ValueError):
            self.orchestrator.run(self.issue, [])

    def test_issue_payload_runs_with_fake_providers(self):
        report = run_issue({"number": 8, "title": "Bad state", "repository": "acme/repo"})
        self.assertEqual("minimal", report["winner"]["candidate"]["name"])
        self.assertEqual("fake", report["pull_request"]["mode"])


if __name__ == "__main__":
    unittest.main()
