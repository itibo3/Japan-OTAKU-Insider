import argparse
import webbrowser
from pathlib import Path

from rss_manager.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Japan OTAKU Insider RSS Manager V2 (Phase A)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port number (default: 8080)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the management UI in a browser",
    )
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"

    if not args.no_browser:
        # ブラウザ起動は失敗しても致命的ではないので例外は握りつぶす
        try:
            webbrowser.open(url)
        except Exception:
            pass

    project_root = Path(__file__).resolve().parent
    run_server(
        host=args.host,
        port=args.port,
        project_root=project_root,
    )


if __name__ == "__main__":
    main()

