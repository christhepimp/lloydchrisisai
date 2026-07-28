"""
Lloyd - Entry Point
===================
Run this to talk to Lloyd in the terminal for now.
Mobile interface coming next.
"""

from lloyd.agent import Lloyd

def main():
    lloyd = Lloyd()
    print("\nType something to Lloyd (or 'quit' to exit)\n")

    while True:
        try:
            user = input("You > ").strip()
            if user.lower() in {"quit", "exit", "bye"}:
                print("Lloyd > aight peace")
                break
            if not user:
                continue

            reply = lloyd.think(user)
            print(f"Lloyd > {reply}")

        except KeyboardInterrupt:
            print("\nLloyd > aight peace")
            break

if __name__ == "__main__":
    main()
