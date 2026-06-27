"""Command-line interface.

Examples
--------
List audio devices::

    python -m voicechanger --list-devices

Run headless with a preset and explicit devices::

    python -m voicechanger --no-gui --preset 年輕女聲 --in 1 --out 7 --monitor 5

Launch the GUI (default)::

    python -m voicechanger
"""
from __future__ import annotations

import argparse
import sys

from .engine import AudioEngine
from .presets import PRESET_ORDER


def _print_devices() -> None:
    ins, outs = AudioEngine.list_devices()
    print("輸入裝置 (inputs):")
    for i, n in ins:
        print(f"  [{i}] {n}")
    print("\n輸出裝置 (outputs):")
    for i, n in outs:
        print(f"  [{i}] {n}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voicechanger",
        description="即時變聲器 — real-time TD-PSOLA voice changer",
    )
    parser.add_argument("--list-devices", action="store_true",
                        help="列出音訊裝置後結束")
    parser.add_argument("--no-gui", action="store_true",
                        help="無介面模式（headless）")
    parser.add_argument("--preset", default="原聲 (Off)", choices=PRESET_ORDER,
                        help="起始預設")
    parser.add_argument("--in", dest="in_dev", type=int, default=None,
                        help="輸入裝置索引")
    parser.add_argument("--out", dest="out_dev", type=int, default=None,
                        help="輸出裝置索引（給 Discord，通常是 CABLE Input）")
    parser.add_argument("--monitor", dest="mon_dev", type=int, default=None,
                        help="監聽裝置索引（你的耳機）")
    parser.add_argument("--gate", type=float, default=1.0,
                        help="噪音門閾值百分比（預設 1.0）")
    args = parser.parse_args(argv)

    if args.list_devices:
        _print_devices()
        return 0

    if not args.no_gui:
        from .gui import launch_gui
        launch_gui(initial_preset=args.preset)
        return 0

    # headless mode
    engine = AudioEngine()
    engine.noise_gate = args.gate / 100
    engine.set_preset(args.preset)
    try:
        engine.start(args.in_dev, args.out_dev, args.mon_dev)
    except Exception as exc:  # pragma: no cover - hardware dependent
        print(f"啟動失敗: {exc}", file=sys.stderr)
        return 1

    print(f"執行中（預設：{args.preset}）。按 Ctrl+C 結束。")
    try:
        import time
        while True:
            time.sleep(0.5)
            print(f"\rCPU {engine.cpu_usage:4.1f}%  in {engine.input_level:.2f} "
                  f"out {engine.output_level:.2f}", end="", flush=True)
    except KeyboardInterrupt:
        print("\n停止中…")
    finally:
        engine.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
