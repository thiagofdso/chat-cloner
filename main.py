"""
Main entry point for Clonechat.
"""
import sys
from cli import app


def main():
    """Main entry point for the Clonechat application."""
    try:
        app()
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 