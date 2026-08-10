from __future__ import annotations

import argparse
import sys
import time

from . import APP_NAME, __version__, config


def banner() -> None:
    print()
    print("   ♪  \033[1;38;5;83mT E R M I F Y\033[0m  ·  spotify, minus the app")
    print()


def pause(msg: str = "press enter to continue…") -> None:
    try:
        input(f"  {msg}")
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def run_demo(cfg, shot: str | None = None) -> None:
    from .app import App
    from .demo_engine import DemoEngine

    engine = DemoEngine(cfg)
    app = App(engine, cfg, demo=True)
    if shot:
        make_shot(app, shot)
        return
    app.run()


def make_shot(app, path: str) -> None:
    """Render the demo UI a few times and save the final frame as SVG."""
    from rich.console import Console

    app.snap = app.engine.snapshot()
    app.rows["playlists"] = app.engine.get_playlists()
    W, H = 118, 37
    # warm the album-art cache (async in real life, forced here)
    for _ in range(10):
        app.render(W, H)
        time.sleep(0.05)
    console = Console(record=True, width=W, height=H)
    app._t0 -= 3.5  # mid-animation phase, prettier frame
    console.print(app.render(W, H))
    try:
        console.save_svg(path, title="Termify")
    except TypeError:
        console.export_svg(path)
    print(f"saved {path}")


def ensure_client(cfg) -> None:
    from . import auth

    if not cfg.get("client_id"):
        banner()
        cfg["client_id"] = auth.prompt_client_id()
        if not cfg["client_id"]:
            print("  no client id - can't continue.")
            sys.exit(1)
        config.save_config(cfg)


def build_engine(cfg, args):
    from . import auth
    from .audio_sink import PCMRing, pick_sink
    from .demo_engine import DemoEngine  # noqa: F401  (kept for --demo reuse)
    from .remote_engine import RemoteEngine
    from .stream_engine import StreamEngine

    print("  connecting to spotify web api…")
    sp = auth.build_spotify_client(cfg, interactive=sys.stdin.isatty())

    core = None
    want_stream = not args.remote and cfg.get("mode", "auto") != "remote"
    if want_stream and not args.force_remote:
        core = auth.CoreSession(cfg)
        have_creds = config.LIBCRED_FILE.exists()
        if not have_creds:
            banner()
            print("  Termify can play audio right here in the terminal,")
            print("  entirely replacing the desktop app. This needs a")
            print("  one-time browser login so Spotify trusts this device.")
            print()
            ans = input("  set up in-terminal audio now? [Y/n] ").strip().lower()
            if ans in ("n", "no"):
                core = None
            else:
                print()
        if core is not None:
            try:
                core.build_blocking(timeout=180)
            except auth.CoreError as exc:
                print(f"  audio core unavailable: {exc}")
                print("  falling back to remote-control mode.")
                pause()
                core = None

    engine = None
    if core is not None and not args.force_remote:
        try:
            pick_sink(PCMRing(), "auto")
            engine = StreamEngine(sp, cfg, core)
            print("  → embedded audio mode (this terminal IS the player)")
        except Exception as exc:  # noqa: BLE001
            print(f"  no audio output backend: {exc}")
            print("  → remote-control mode instead")
    if engine is None:
        engine = RemoteEngine(sp, cfg)
        print("  → remote-control mode (controls any spotify device)")
    time.sleep(0.8)
    return engine


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="termify",
        description="a terminal spotify client - replaces the heavy desktop app.",
    )
    parser.add_argument("--demo", action="store_true",
                        help="offline demo with fake music (no account needed)")
    parser.add_argument("--remote", action="store_true",
                        help="skip the embedded player; control other spotify devices")
    parser.add_argument("--force-remote", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--setup", action="store_true",
                        help="re-run the setup wizard (client id)")
    parser.add_argument("--theme", choices=config.ORDERED_THEMES,
                        help="color theme override")
    parser.add_argument("--shot", metavar="SVG", help=argparse.SUPPRESS)  # doc screenshots
    parser.add_argument("--version", action="version",
                        version=f"termify {__version__}")
    args = parser.parse_args()

    config.ensure_dirs()
    cfg = config.load_config()
    if args.theme:
        cfg["theme"] = args.theme

    if args.demo:
        if not args.shot:
            banner()
            print("  demo mode: fake music, no audio, no account needed.")
            print("  (controls are all real - run without --demo to connect)")
            time.sleep(1.6)
        run_demo(cfg, shot=args.shot)
        return

    try:
        if args.setup:
            cfg["client_id"] = ""
        ensure_client(cfg)
        engine = build_engine(cfg, args)
    except KeyboardInterrupt:
        print("\n  bye.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"\n  setup failed: {exc}")
        print("  try:  python -m termify --setup     to redo the connection")
        sys.exit(1)

    from .app import App

    App(engine, cfg).run()


if __name__ == "__main__":
    main()
