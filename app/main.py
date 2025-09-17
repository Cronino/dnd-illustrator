from ui.streamlit_app import run
from dotenv import load_dotenv


def main() -> None:
    # Load environment variables from a local .env file if present
    load_dotenv()
    run()


if __name__ == "__main__":
    main()


