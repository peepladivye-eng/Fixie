# Fixtures contain deliberately failing visible tests and hidden graders. They are
# copied into a temporary sandbox by the agent and must not be collected here.
collect_ignore_glob = ["fixtures/*/repo/test_*.py", "fixtures/*/hidden_tests/test_*.py"]
