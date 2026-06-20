.PHONY: generate-traces grade playground

generate-traces:
	mkdir -p artifacts/traces
	uv run python tests/eval/generate_traces.py

grade:
	uv run python tests/eval/grade.py

playground:
	agents-cli playground --app ambient-expense-agent
