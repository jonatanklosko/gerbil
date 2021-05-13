import sys
import signal
from gerbil import Gerbil

def sigint_handler(sig, frame):
    gerbil.stop()
    print("\nBye 🐹")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        gerbil = Gerbil()

        print("Hola amigo, enjoy 🐹")

        while True:
            gerbil.step()

    except Exception as e:
        print(f"Error: {e}")
