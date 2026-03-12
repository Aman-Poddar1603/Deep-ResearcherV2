import threading
import time
import urllib.request
import logging
import sys

URL = "http://localhost:8000/health"

sent = 0
success = 0
failed = 0
active = 0

lock = threading.Lock()

# -------------------------------------------------
# Logging setup
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("concurrency-tester")


def make_request():
    global sent, success, failed, active

    with lock:
        sent += 1
        active += 1

    try:
        with urllib.request.urlopen(URL, timeout=10) as r:
            r.read()

        with lock:
            success += 1

    except Exception:
        with lock:
            failed += 1

    finally:
        with lock:
            active -= 1


def monitor():
    """Print live stats every second"""
    while True:
        time.sleep(1)

        with lock:
            s = sent
            sc = success
            f = failed
            a = active

        logger.info(
            f"Live Stats → Sent: {s} | Success: {sc} | Failed: {f} | Active: {a}"
        )

        if a == 0 and s > 0:
            break


def run_test(concurrent_requests):
    threads = []

    logger.info(f"Starting concurrency test")
    logger.info(f"Target: {URL}")
    logger.info(f"Concurrent Requests: {concurrent_requests}")

    start = time.time()

    # start monitor thread
    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.start()

    for _ in range(concurrent_requests):
        t = threading.Thread(target=make_request)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    monitor_thread.join()

    total_time = time.time() - start

    logger.info("----------- FINAL RESULT -----------")
    logger.info(f"Total Sent: {sent}")
    logger.info(f"Successful: {success}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total Time: {total_time:.2f}s")

    if total_time > 0:
        logger.info(f"Requests/sec: {sent/total_time:.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python stress_test.py <concurrent_requests>")
        sys.exit(1)

    run_test(int(sys.argv[1]))
