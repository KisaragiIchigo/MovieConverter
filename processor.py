import os
import subprocess
import time
import multiprocessing
from pathlib import Path
from natsort import natsorted
import winsound

def get_valid_files(paths):
    """
    入力されたパスリストから、有効な動画ファイル（またはフォルダ内の動画ファイル）のリストを返す。
    """
    valid_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
    files_to_process = []
    
    for p_str in paths:
        p = Path(p_str)
        if p.is_dir():
            # フォルダの場合、再帰的にファイルを探す
            for ext in valid_extensions:
                files_to_process.extend(list(p.rglob(f'*{ext}')))
        elif p.is_file() and p.suffix.lower() in valid_extensions:
            files_to_process.append(p)
            
    # 重複を削除し、自然順でソート
    return natsorted(list(set(files_to_process)))

def is_gpu_available():
    """NVIDIA GPU (nvidia-smi) が利用可能かチェックする"""
    try:
        # startupinfoを使ってコンソールウィンドウを非表示にする
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        
        subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, startupinfo=si)
        print("NVIDIA GPU is available.")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("NVIDIA GPU not found. Falling back to CPU.")
        return False

def get_codec_option(codec, gpu_available):
    """選択されたコーデックとGPUの有無に基づいてffmpegのコーデックオプションを返す"""
    if codec == "h.264":
        return "h264_nvenc" if gpu_available else "libx264"
    else: # MPEG-4
        return "mpeg4"

def get_thread_count(setting):
    """スレッド設定に基づいて使用するスレッド数を返す"""
    total_cores = multiprocessing.cpu_count()
    if setting == "MAX":
        return total_cores
    if setting == "MIDDLE":
        return max(1, total_cores // 2)
    # LOW
    return 1

def format_time(seconds):
    """秒を HH:MM:SS 形式の文字列に変換する"""
    if seconds < 0: return "00:00:00"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02}"

def process_videos(paths, settings, ffmpeg_path, progress_callback, file_callback, eta_callback, complete_callback):
    """
    動画ファイルのリストを受け取り、設定に基づいて変換処理を行う。
    進捗はコールバック関数を通じてGUIに通知される。
    """
    files_to_process = get_valid_files(paths)
    if not files_to_process:
        complete_callback("変換対象の動画ファイルが見つかりませんでした。")
        return

    total_files = len(files_to_process)
    start_time = time.time()
    gpu_available = is_gpu_available()

    for index, file_path in enumerate(files_to_process):
        # --- GUI更新 (ファイル名) ---
        file_callback(file_path.name)

        # --- 出力先ディレクトリの作成 ---
        output_dir = file_path.parent / "[MovieConverter]ResizedMovie"
        output_dir.mkdir(exist_ok=True)

        # --- ffmpegコマンドの構築 ---
        codec_option = get_codec_option(settings['codec'], gpu_available)
        threads = get_thread_count(settings['thread_count'])
        
        output_filename = file_path.stem + ".mp4"
        if settings['split_seconds']:
            # 分割する場合は連番をつける
            output_filename = file_path.stem + "_%03d.mp4"
        output_path = output_dir / output_filename

        command = [
            str(ffmpeg_path), '-y', '-i', str(file_path),
            '-c:v', codec_option,
            '-preset', 'fast' if gpu_available else 'medium',
            '-threads', str(threads),
            '-c:a', 'aac', '-b:a', '192k'
        ]

        if settings['bitrate'] != "auto" and settings['bitrate'].isdigit():
            command.extend(['-b:v', f"{settings['bitrate']}k"])

        if settings['width'].isdigit() and settings['height'].isdigit():
            command.extend(['-vf', f"scale={settings['width']}:{settings['height']}"])
            
        if settings['split_seconds'] and settings['split_seconds'].isdigit():
            split_duration = int(settings['split_seconds'])
            command.extend([
                '-f', 'segment',
                '-segment_time', str(split_duration),
                '-reset_timestamps', '1'
            ])

        command.append(str(output_path))
        
        # --- ffmpegの実行 ---
        try:
            # コンソールウィンドウを非表示で実行
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.run(command, check=True, startupinfo=si, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Successfully converted: {file_path.name}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to convert {file_path.name}. Error: {e.stderr.decode('utf-8', errors='ignore')}")
            # エラーが発生しても次のファイルへ
            continue
        finally:
            # --- GUI更新 (進捗) ---
            progress = ((index + 1) / total_files) * 100
            progress_callback(progress)
            
            # --- GUI更新 (ETA) ---
            elapsed_time = time.time() - start_time
            avg_time_per_file = elapsed_time / (index + 1)
            remaining_files = total_files - (index + 1)
            eta_seconds = avg_time_per_file * remaining_files
            eta_callback(format_time(eta_seconds))

    # --- 変換完了処理 ---
    winsound.Beep(1000, 500)
    complete_callback("すべての動画の変換が完了しました！")