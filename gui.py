import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD
from tkinter import filedialog, messagebox, Toplevel, Listbox
import tkinter as tk  # iconphoto用
import processor
import config
import threading

# ===== ウィンドウアイコン（Base64埋め込みPNG）=====
ICON_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4"
    "2mP8/x8AAwMCAO0h5nQAAAAASUVORK5CYII="
)

class App(ctk.CTk, TkinterDnD.Tk):
    def __init__(self, ffmpeg_path, icon_path, config_file, presets_file):

        ctk.CTk.__init__(self)
        TkinterDnD.Tk.__init__(self)

        # --- 基本設定 ---
        self.title("Movie🎦Converter ©️2025 KisaragiIchigo ")
        self.geometry("700x750")

        # ▼ ファイル不要のウィンドウアイコン設定（展開しない）
        try:
            self._icon_img = tk.PhotoImage(data=ICON_PNG_BASE64)  # GC防止で保持
            self.iconphoto(False, self._icon_img)
        except Exception as e:
            print(f"ウィンドウアイコン設定に失敗: {e}")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.font = ("メイリオ", 12)

        # --- 外部から渡されるパスを保持 ---
        self.ffmpeg_path = ffmpeg_path
        self.config_file = config_file
        self.presets_file = presets_file

        # --- GUIコンポーネントの初期化 ---
        self._create_widgets()

        # --- D&Dの有効化 ---
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_dnd)

        # --- 前回の設定とプリセットを読み込む ---
        self.load_all_settings()

        # ウィンドウを閉じる際のカスタム処理
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """安全に mainloop を停止"""
        self.quit()

    def _create_widgets(self):
        # --- タブビュー ---
        tab_view = ctk.CTkTabview(self)
        tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        tab_view._segmented_button.configure(font=self.font)

        tab_view.add("基本設定")
        tab_view.add("詳細設定")

        # --- 基本設定タブ ---
        self.setup_basic_tab(tab_view.tab("基本設定"))

        # --- 詳細設定タブ ---
        self.setup_advanced_tab(tab_view.tab("詳細設定"))

        # --- D&Dフレーム ---
        self.dnd_frame = ctk.CTkFrame(self, fg_color="#3b8ed0")
        self.dnd_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.dnd_frame.grid_rowconfigure(0, weight=1)
        self.dnd_frame.grid_columnconfigure(0, weight=1)

        dnd_label = ctk.CTkLabel(self.dnd_frame, text="ここにファイルまたはフォルダをドラッグ＆ドロップ",
                                 font=(self.font[0], 16, "bold"))
        dnd_label.grid(row=0, column=0)

        # --- 進行状況表示 ---
        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.overall_progress_bar = ctk.CTkProgressBar(progress_frame, orientation="horizontal", mode="determinate")
        self.overall_progress_bar.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.overall_progress_bar.set(0)

        self.current_file_label = ctk.CTkLabel(progress_frame, text="処理中: なし", font=self.font)
        self.current_file_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        self.estimated_time_label = ctk.CTkLabel(progress_frame, text="予想終了時間: ", font=self.font)
        self.estimated_time_label.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")

        # --- ボタン ---
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        button_frame.grid_columnconfigure((0, 1), weight=1)

        select_files_button = ctk.CTkButton(button_frame, text="動画ファイルを選択",
                                            command=self.select_files, font=self.font)
        select_files_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        select_folder_button = ctk.CTkButton(button_frame, text="フォルダを選択",
                                             command=self.select_folder, font=self.font)
        select_folder_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        readme_button = ctk.CTkButton(self, text="README", command=self.show_readme, font=self.font)
        readme_button.grid(row=4, column=0, padx=10, pady=(5, 10))

    def setup_basic_tab(self, tab):
        """基本設定タブの中身を作成する"""
        tab.grid_columnconfigure(0, weight=1)

        # --- スレッド設定 ---
        thread_frame = ctk.CTkFrame(tab)
        thread_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(thread_frame, text="スレッド設定:", font=self.font).pack(side="left", padx=5)

        self.thread_count_var = ctk.StringVar(value="MIDDLE")
        thread_menu = ctk.CTkOptionMenu(thread_frame, variable=self.thread_count_var,
                                        values=["MAX", "MIDDLE", "LOW"], font=self.font)
        thread_menu.pack(side="left", padx=5, fill="x", expand=True)

        # --- プリセット管理 ---
        preset_frame = ctk.CTkFrame(tab)
        preset_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        preset_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(preset_frame, text="プリセット管理", font=(self.font[0], 14, "bold")).grid(
            row=0, column=0, columnspan=2, pady=5
        )

        # customtkinterにListboxがないためtkinterのListboxを使用
        self.preset_list = Listbox(preset_frame, font=self.font, bg="#2b2b2b",
                                   fg="white", selectbackground="#3b8ed0", relief="sunken", borderwidth=0)
        self.preset_list.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        preset_btn_frame = ctk.CTkFrame(preset_frame)
        preset_btn_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        preset_btn_frame.grid_columnconfigure((0, 1), weight=1)

        apply_button = ctk.CTkButton(preset_btn_frame, text="プリセットを適用",
                                     command=self.apply_selected_preset, font=self.font)
        apply_button.grid(row=0, column=0, padx=5, sticky="ew")

        delete_button = ctk.CTkButton(preset_btn_frame, text="プリセットを削除",
                                      command=self.delete_selected_preset, font=self.font)
        delete_button.grid(row=0, column=1, padx=5, sticky="ew")

    def setup_advanced_tab(self, tab):
        """詳細設定タブの中身を作成する"""
        tab.grid_columnconfigure(1, weight=1)

        # --- コーデック ---
        ctk.CTkLabel(tab, text="コーデック:", font=self.font).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.codec_var = ctk.StringVar(value="h.264")
        codec_menu = ctk.CTkOptionMenu(tab, variable=self.codec_var, values=["h.264", "MPEG-4"], font=self.font)
        codec_menu.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # --- ビットレート ---
        ctk.CTkLabel(tab, text="ビットレート (kbps):", font=self.font).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.bitrate_var = ctk.StringVar(value="auto")
        bitrate_entry = ctk.CTkEntry(tab, textvariable=self.bitrate_var, font=self.font)
        bitrate_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # --- 解像度 ---
        ctk.CTkLabel(tab, text="解像度 (幅 x 高さ):", font=self.font).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        size_frame = ctk.CTkFrame(tab)
        size_frame.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        self.width_var = ctk.StringVar()
        self.height_var = ctk.StringVar()
        width_entry = ctk.CTkEntry(size_frame, textvariable=self.width_var, font=self.font, width=80)
        width_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(size_frame, text=" x ", font=self.font).pack(side="left")
        height_entry = ctk.CTkEntry(size_frame, textvariable=self.height_var, font=self.font, width=80)
        height_entry.pack(side="left", fill="x", expand=True)

        # --- 分割設定 ---
        ctk.CTkLabel(tab, text="分割秒数 (任意):", font=self.font).grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.split_seconds_var = ctk.StringVar()
        split_entry = ctk.CTkEntry(tab, textvariable=self.split_seconds_var, font=self.font)
        split_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        # --- プリセット保存 ---
        save_preset_frame = ctk.CTkFrame(tab)
        save_preset_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=20, sticky="ew")
        save_preset_frame.grid_columnconfigure(0, weight=1)

        self.preset_name_entry = ctk.CTkEntry(save_preset_frame, placeholder_text="プリセット名を入力", font=self.font)
        self.preset_name_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        save_button = ctk.CTkButton(save_preset_frame, text="現在の設定をプリセットとして保存",
                                    command=self.save_current_preset, font=self.font)
        save_button.grid(row=0, column=1, padx=(5, 0))

    def get_current_settings(self):
        """GUIから現在の設定値を取得して辞書として返す"""
        return {
            "codec": self.codec_var.get(),
            "bitrate": self.bitrate_var.get(),
            "width": self.width_var.get(),
            "height": self.height_var.get(),
            "split_seconds": self.split_seconds_var.get(),
            "thread_count": self.thread_count_var.get()
        }

    def apply_settings(self, settings):
        """辞書から設定をGUIに適用する"""
        self.codec_var.set(settings.get("codec", "h.264"))
        self.bitrate_var.set(settings.get("bitrate", "auto"))
        self.width_var.set(settings.get("width", ""))
        self.height_var.set(settings.get("height", ""))
        self.split_seconds_var.set(settings.get("split_seconds", ""))
        self.thread_count_var.set(settings.get("thread_count", "MIDDLE"))

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="動画ファイルを選択",
            filetypes=[("動画ファイル", "*.mp4;*.mov;*.avi;*.mkv;*.webm;*.flv;*.wmv")]
        )
        if files:
            self.start_conversion(list(files))

    def select_folder(self):
        folder = filedialog.askdirectory(title="フォルダを選択")
        if folder:
            self.start_conversion([folder])

    def handle_dnd(self, event):
        paths = self.tk.splitlist(event.data)
        if paths:
            self.start_conversion(paths)

    def start_conversion(self, paths):
        # 現在の設定を保存
        config.save_settings(self.config_file, self.get_current_settings())

        # 変換処理を別スレッドで実行
        conv_thread = threading.Thread(
            target=processor.process_videos,
            args=(
                paths,
                self.get_current_settings(),
                self.ffmpeg_path,
                self.update_progress,
                self.update_current_file,
                self.update_eta,
                self.on_conversion_complete
            ),
            daemon=True
        )
        conv_thread.start()

    # --- 別スレッドからのGUI更新用コールバック ---
    def update_progress(self, value):
        self.overall_progress_bar.set(value / 100)

    def update_current_file(self, text):
        self.current_file_label.configure(text=f"処理中: {text}")

    def update_eta(self, text):
        self.estimated_time_label.configure(text=f"予想終了時間: {text}")

    def on_conversion_complete(self, message):
        self.current_file_label.configure(text="処理完了！")
        self.estimated_time_label.configure(text="")
        self.overall_progress_bar.set(0)
        messagebox.showinfo("完了", message)

    # --- プリセット関連 ---
    def refresh_preset_list(self):
        self.preset_list.delete(0, 'end')
        presets = config.load_presets(self.presets_file)
        for name in presets:
            self.preset_list.insert('end', name)

    def save_current_preset(self):
        preset_name = self.preset_name_entry.get()
        if not preset_name:
            messagebox.showwarning("警告", "プリセット名を入力してください。")
            return
        settings = self.get_current_settings()
        config.save_preset(self.presets_file, preset_name, settings)
        self.refresh_preset_list()
        self.preset_name_entry.delete(0, 'end')
        messagebox.showinfo("成功", f"プリセット '{preset_name}' を保存しました。")

    def apply_selected_preset(self):
        selected_indices = self.preset_list.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "適用するプリセットをリストから選択してください。")
            return
        preset_name = self.preset_list.get(selected_indices[0])
        settings = config.apply_preset(self.presets_file, preset_name)
        if settings:
            self.apply_settings(settings)
            messagebox.showinfo("適用完了", f"プリセット '{preset_name}' を適用しました。")
        else:
            messagebox.showerror("エラー", "プリセットの読み込みに失敗しました。")

    def delete_selected_preset(self):
        selected_indices = self.preset_list.curselection()
        if not selected_indices:
            messagebox.showwarning("警告", "削除するプリセットをリストから選択してください。")
            return
        preset_name = self.preset_list.get(selected_indices[0])
        if messagebox.askyesno("確認", f"プリセット '{preset_name}' を本当に削除しますか？"):
            config.delete_preset(self.presets_file, preset_name)
            self.refresh_preset_list()
            messagebox.showinfo("削除完了", f"プリセット '{preset_name}' を削除しました。")

    def load_all_settings(self):
        settings = config.load_settings(self.config_file)
        self.apply_settings(settings)
        self.refresh_preset_list()

    def show_readme(self):
        readme_window = Toplevel(self)
        readme_window.title("README ©️2025 KisaragiIchigo")
        readme_window.geometry("800x600")

        readme_text = (
            "【ツール名】\n"
            "Movie🎦Converter（ムービーコンバーター）\n\n"
            "【概要】\n"
            "動画ファイルをまとめて MP4 に変換するシンプルなツールです。ffmpeg を内部で使用し、\n"
            "解像度／ビットレート／コーデック（h.264 / MPEG-4）の指定や、秒数での分割、\n"
            "よく使う設定のプリセット保存に対応します。\n\n"
            "【動作環境】\n"
            "- 追加インストール不要（Python不要／exe単体でOK）\n"
            "- GPU（NVENC）があれば高速化の可能性あり（環境により利用可否が異なります）\n\n"
            "【初回起動について】\n"
            "- 初回起動時、必要なライブラリと ffmpeg.exe を exe と同じフォルダに展開します。\n"
            "  （展開先に書き込み権限が必要です。Program Files 直下は避けるのがおすすめ）\n"
            "【できること（主な機能）】\n"
            "- ドラッグ＆ドロップで動画 or フォルダを投入\n"
            "- 変換形式：MP4 / コーデック：h.264 または MPEG-4\n"
            "- ビットレート（kbps）指定・自動（auto）\n"
            "- 解像度指定（幅×高さ）／未指定なら元解像度のまま\n"
            "- 秒数での自動分割（任意）\n"
            "- スレッド数の目安（MAX / MIDDLE / LOW）\n"
            "- プリセットの保存／適用／削除\n\n"
            "【基本の使い方（超かんたん）】\n"
            "1) 変換したい動画ファイルを、このウィンドウへドラッグ＆ドロップします。\n"
            "   もしくは「動画ファイルを選択」または「フォルダを選択」から指定します。\n"
            "2) 上部タブの「基本設定／詳細設定」で、コーデックや解像度などを必要に応じて調整。\n"
            "   - コーデック：h.264（互換性高め）／MPEG-4（軽め）\n"
            "   - ビットレート：数値（kbps）または auto（自動）\n"
            "   - 解像度：幅と高さを空欄にすると元のまま\n"
            "   - 分割：1ファイルを指定秒ごとに分けたい場合だけ秒数を入力\n"
            "   - スレッド数：PCの状況に合わせて目安を選択\n"
            "3) 変換を開始すると、進行状況バーと現在処理中のファイル名が表示されます。\n"
            "4) 完了後、出力ファイルは元動画のあるフォルダ直下に作成される\n"
            "   「[MovieConverter]ResizedMovie」フォルダに保存されます。\n\n"
            "【プリセットの活用】\n"
            "- よく使う設定は「プリセット名」を入力して［現在の設定をプリセットとして保存］\n"
            "- リストから選んで［プリセットを適用］で即呼び出し\n"
            "- 不要になったら［プリセットを削除］\n\n"
            "【ログ／設定ファイル】\n"
            "- 設定・プリセットは exe と同じ場所に保存されます。\n"
            "- 変換の進行やエラーはポップアップ・表示欄で確認できます。\n\n"
            "©️2025 KisaragiIchigo\n"
        )

        textbox = ctk.CTkTextbox(readme_window, font=self.font, wrap='word')
        textbox.pack(expand=True, fill='both', padx=10, pady=10)
        textbox.insert("1.0", readme_text)
        textbox.configure(state='disabled')
