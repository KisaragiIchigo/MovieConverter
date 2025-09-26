import sys
import os
from pathlib import Path
import shutil

_WHITELIST_COPY = {"ffmpeg.exe"}  # 展開許可ファイル

def get_resource_path(relative_path: str, extraction_dir: Path) -> Path | None:
    """
    relative_path: 例) 'ffmpeg.exe'
    extraction_dir: 展開先（通常は exe と同じフォルダ）
    戻り値: 利用すべき実パス / 見つからなければ None
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundle_dir = Path(sys._MEIPASS)
        source_path = bundle_dir / relative_path
        dest_path = extraction_dir / relative_path

        # ▼ ホワイトリストにあるものだけコピー（ffmpeg.exe）
        if relative_path.lower() in _WHITELIST_COPY and source_path.exists():
            if not dest_path.exists():
                try:
                    print(f"Copying '{relative_path}' to '{dest_path}' for portable use.")
                    shutil.copy2(source_path, dest_path)
                except Exception as e:
                    print(f"Failed to copy '{relative_path}': {e}")
                    return None
            return dest_path

        # ▼ ホワイトリスト外はコピーしない
        #    既にユーザーが手動配置していればそれを返し、無ければ None
        return dest_path if dest_path.exists() else None

    # 通常のスクリプト実行時
    base_path = Path(os.path.abspath("."))
    candidate = base_path / relative_path
    return candidate if candidate.exists() else None
