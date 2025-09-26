import json

def load_settings(config_file):
    """設定ファイルから設定を読み込む"""
    if not config_file:
        return {  # デフォルト
            "codec": "h.264",
            "bitrate": "auto",
            "width": "",
            "height": "",
            "split_seconds": "",
            "thread_count": "MIDDLE"
        }
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "codec": "h.264",
            "bitrate": "auto",
            "width": "",
            "height": "",
            "split_seconds": "",
            "thread_count": "MIDDLE"
        }
    
    
def save_settings(config_file, settings):
    """現在の設定を設定ファイルに保存する"""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"設定の保存に失敗しました: {e}")

def load_presets(presets_file):
    """プリセットファイルからすべてのプリセットを読み込む"""
    try:
        with open(presets_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_preset(presets_file, preset_name, settings):
    """指定された名前でプリセットを保存する"""
    presets = load_presets(presets_file)
    presets[preset_name] = settings
    try:
        with open(presets_file, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"プリセットの保存に失敗しました: {e}")

def apply_preset(presets_file, preset_name):
    """指定された名前のプリセットを読み込んで返す"""
    presets = load_presets(presets_file)
    return presets.get(preset_name)

def delete_preset(presets_file, preset_name):
    """指定された名前のプリセットを削除する"""
    presets = load_presets(presets_file)
    if preset_name in presets:
        del presets[preset_name]
        try:
            with open(presets_file, 'w', encoding='utf-8') as f:
                json.dump(presets, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"プリセットの削除に失敗しました: {e}")