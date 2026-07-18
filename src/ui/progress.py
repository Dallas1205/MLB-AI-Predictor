import sys
import time


def progress_bar(current, total, label="", width=30):
    if total <= 0:
        total = 1

    percent = current / total
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)

    sys.stdout.write(
        f"\r{label} |{bar}| {percent * 100:5.1f}% ({current}/{total})"
    )
    sys.stdout.flush()

    if current >= total:
        print()


def step(message, delay=0.15):
    print(f"{message}...", end="", flush=True)
    time.sleep(delay)
    print(" ✓")