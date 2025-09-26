from __future__ import annotations

import os
import sys
from pathlib import Path
import shutil
import importlib.util

import customtkinter as ctk

# 自前モジュール
import utils
from gui import App

# ====== 依存モジュールの存在チェック（natsort） ======
def _ensure_dependency(module_name: str, import_hint: str = "") -> None:
    """
    指定モジュールが見つからない場合、分かりやすいメッセージを出して安全終了。
    PyInstaller 実行時は欠品に気づきにくいのでここで弾く。
    """
    if importlib.util.find_spec(module_name) is None:
        msg = [
            f"[ERROR] 必要なモジュールが見つかりません: {module_name}",
            "Python 環境での実行なら以下を実行してね：",
            f"    pip install {module_name}",
        ]
        if import_hint:
            msg.append(import_hint)
        # なるべくコンソール無し --noconsole でも伝わるよう、print と最後の input を併用
        print("\n".join(msg))
        try:
            # GUIがある環境なら簡易ダイアログを出す（失敗してもOK）
            import tkinter as _tk
            from tkinter import messagebox as _mb
            root = _tk.Tk(); root.withdraw()
            _mb.showerror("依存モジュールが不足しています",
                          f"必要なモジュールが見つかりません: {module_name}\n\n"
                          f"コマンド例: pip install {module_name}")
            root.destroy()
        except Exception:
            pass
        # コンソールがあれば一瞬で閉じないよう停止
        try:
            input("\nEnter を押すと終了します...")
        except Exception:
            pass
        sys.exit(1)

# processor.py が import する natsort を先に確認
_ensure_dependency("natsort", import_hint="PyInstaller なら spec で hiddenimports に 'natsort' を入れてもOK。")


# ====== ライブラリ展開（tkinterdnd2 / tkdnd2.x） ======
def setup_library_modules(base_path: Path) -> None:
    """
    PyInstaller --onefile で _MEIPASS 内に同梱した DnD 関連ライブラリを
    実行フォルダへコピー（未存在のときのみ）。
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print("Checking for bundled libraries to extract...")
        # tkdnd は 2.8 / 2.9 が環境で揺れるので両方ケア
        required_modules = ["tkinterdnd2", "tkdnd2.8", "tkdnd2.9"]

        for module_name in required_modules:
            dest_path = base_path / module_name
            source_path = Path(sys._MEIPASS) / module_name
            if not dest_path.exists() and source_path.exists():
                print(f"Extracting bundled library '{module_name}' to '{dest_path}'...")
                try:
                    shutil.copytree(source_path, dest_path)
                except Exception as e:
                    print(f"Failed to extract library '{module_name}': {e}")


# ====== 外部リソースの解決＆用意 ======
def resource_extraction(base_path: Path) -> tuple[Path | None, Path, Path]:
    """
    - ffmpeg.exe を展開許可リストに従ってコピー（utils.get_resource_path）
    - config ディレクトリを作成
    - 設定JSON/プリセットJSONを未存在なら "{}" で作成
    """
    # ▼ ffmpeg はホワイトリストでコピー対象
    ffmpeg_path = utils.get_resource_path("ffmpeg.exe", base_path)

    # 設定フォルダ
    config_dir = base_path / "config"
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "[config]MovieConverter_config.json"
    presets_file = config_dir / "[config]MovieConverter_presets.json"

    # 未存在なら空JSONで作成（読み込み側が安心）
    for p in (config_file, presets_file):
        if not p.exists():
            try:
                p.write_text("{}", encoding="utf-8")
            except Exception as e:
                print(f"Failed to initialize config file '{p.name}': {e}")

    return ffmpeg_path, config_file, presets_file


# ====== ffmpeg 実体の最終決定 ======
def _resolve_ffmpeg(ffmpeg_path: Path | None) -> str:
    if ffmpeg_path and ffmpeg_path.exists():
        return str(ffmpeg_path)

    # PATH の ffmpeg を試す
    candidate = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    print("[WARN] 同梱 ffmpeg.exe が見つからないため、PATH の ffmpeg を使用します。")
    return candidate


# ====== エントリーポイント ======
if __name__ == "__main__":
    # 実行ベースディレクトリ（--onefile でもここが exe の置き場所になる）
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(os.path.abspath("."))

    # 1) DnD系の同梱ライブラリを展開
    setup_library_modules(base_path)

    # 2) 外部ファイル（ffmpeg / config系）の用意
    _ffmpeg_path, CONFIG_FILE, PRESETS_FILE = resource_extraction(base_path)
    FFMPEG_PATH_STR = _resolve_ffmpeg(_ffmpeg_path)

    # 3) customtkinter のテーマ設定
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # 4) GUI 起動
    app = App(
        ffmpeg_path=FFMPEG_PATH_STR,
        icon_path=None,              # いまはBase64アイコンをgui.py側で使ってる
        config_file=CONFIG_FILE,
        presets_file=PRESETS_FILE
    )
    app.mainloop()