.PHONY: test score-demo install lint

install:
	pip install -r requirements.txt

test:
	python3 -m pytest tests/ -q

# Run the FROZEN scoring battery end-to-end on synthetic data (no API keys).
score-demo:
	python3 -m src.scoring_frozen

# Show every open pre-lock item compiled from the code.
pending:
	@grep -rn "PENDING_SIGNOFF\|TBD" src/ config/ || true
