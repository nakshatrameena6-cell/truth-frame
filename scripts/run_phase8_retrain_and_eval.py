"""Retrain PandaMIND detector on authenticated corpus, calibrate on validation set, and evaluate benchmark."""
from __future__ import annotations

from execute_phase8_acceptance import main as run_acceptance

def main() -> None:
    run_acceptance()

if __name__ == "__main__":
    main()
