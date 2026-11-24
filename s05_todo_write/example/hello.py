"""Minimal hello-world example for the ``s05_todo_write`` lesson.

The module only prints a single greeting line and is import-safe: nothing
happens unless it is executed as a script.
"""


def greet(name: str) -> None:
    """Print a greeting addressed to ``name``.

    Args:
        name: The person or thing to greet.

    Returns:
        None. The greeting is written to stdout.
    """
    message: str = "Hello, " + name
    print(message)


def main() -> None:
    """Run the example: greet the hard-coded default name."""
    greet("Claude")


if __name__ == "__main__":
    main()
