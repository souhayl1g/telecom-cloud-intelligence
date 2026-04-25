"""Pipeline-worker entry point."""
import time
from worker.config import RUN_MODE, CYCLE_SECONDS
from worker.pipeline import run_once


def main() -> None:
    if RUN_MODE == "daemon":
        print("pipeline-worker: starting in continuous daemon mode")
        while True:
            print("\n" + "=" * 50)
            print("pipeline-worker: executing scheduled cycle...")
            try:
                run_once()
                print(f"pipeline-worker: cycle complete. Sleeping {CYCLE_SECONDS}s...")
            except Exception as e:
                print(f"pipeline-worker: error: {e}")
                print(f"pipeline-worker: will retry in {CYCLE_SECONDS}s...")
            time.sleep(CYCLE_SECONDS)
    else:
        print("pipeline-worker: starting single execution (oneshot)")
        run_once()
        print("pipeline-worker: execution complete")


if __name__ == "__main__":
    main()
