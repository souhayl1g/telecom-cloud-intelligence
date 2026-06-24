"""Pipeline-worker entry point."""

import signal
import sys
import time
from worker.config import RUN_MODE, CYCLE_SECONDS
from worker.pipeline import run_once

_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    print(f"pipeline-worker: received signal {signum}, shutting down gracefully...")
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def main() -> None:
    if RUN_MODE == "daemon":
        print("pipeline-worker: starting in continuous daemon mode")
        while not _shutdown_requested:
            print("\n" + "=" * 50)
            print("pipeline-worker: executing scheduled cycle...")
            try:
                run_once()
                print(f"pipeline-worker: cycle complete. Sleeping {CYCLE_SECONDS}s...")
            except Exception as e:
                print(f"pipeline-worker: error: {e}")
                print(f"pipeline-worker: will retry in {CYCLE_SECONDS}s...")
            # Sleep in short chunks so shutdown is responsive
            for _ in range(CYCLE_SECONDS):
                if _shutdown_requested:
                    break
                time.sleep(1)
        print("pipeline-worker: daemon stopped.")
        sys.exit(0)
    else:
        print("pipeline-worker: starting single execution (oneshot)")
        run_once()
        print("pipeline-worker: execution complete")


if __name__ == "__main__":
    main()
