import os
import json
import sqlite3
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import pyperclip

# --- 1. データベース管理クラス ---
class BdoDatabase:
    def __init__(self, db_name="bdo_diary.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """データベースとテーブルがなければ作成する"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                battle_lv TEXT, battle_exp TEXT,
                gathering_g TEXT, gathering_lv TEXT, gathering_exp TEXT,
                processing_g TEXT, processing_lv TEXT, processing_exp TEXT,
                fishing_g TEXT, fishing_lv TEXT, fishing_exp TEXT,
                hunting_g TEXT, hunting_lv TEXT, hunting_exp TEXT,
                cooking_g TEXT, cooking_lv TEXT, cooking_exp TEXT,
                alchemy_g TEXT, alchemy_lv TEXT, alchemy_exp TEXT,
                training_g TEXT, training_lv TEXT, training_exp TEXT,
                trade_g TEXT, trade_lv TEXT, trade_exp TEXT,
                farming_g TEXT, farming_lv TEXT, farming_exp TEXT,
                sailing_g TEXT, sailing_lv TEXT, sailing_exp TEXT,
                barter_g TEXT, barter_lv TEXT, barter_exp TEXT,
                eq_helm TEXT, eq_armor TEXT, eq_glove TEXT, eq_shoes TEXT,
                eq_main_wp TEXT, eq_sub_wp TEXT, eq_awk_wp TEXT,
                eq_necklace TEXT, eq_belt TEXT,
                eq_ring1 TEXT, eq_ring2 TEXT, eq_ear1 TEXT, eq_ear2 TEXT,
                eq_stone TEXT, eq_tool TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def get_latest_record(self):
        """前回の最新レコードを1件取得する"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM character_logs ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        return row

    def get_all_records(self):
        """全レコードを日付の古い順に取得する（ダッシュボード用）"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM character_logs ORDER BY date ASC')
        rows = cursor.fetchall()
        conn.close()
        return rows

    def save_record(self, data_dict):
        """現在の画面データをデータベースに新規保存する"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        columns = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?'] * len(data_dict))
        query = f"INSERT INTO character_logs ({columns}) VALUES ({placeholders})"
        cursor.execute(query, list(data_dict.values()))
        conn.commit()
        conn.close()


# --- 2. GUIアプリケーションクラス ---
class BdoDiaryApp:
    def __init__(self, root, db):
        self.root = root
        self.db = db
        self.root.title("黒い砂漠 成長日記帳 Pro (Dark Mode)")
        self.root.geometry("1000x900")
        
        # 🎨 カラーテーマ（ダークモード）の設定
        self.bg_dark = "#1e1e24"      # メイン背景
        self.bg_panel = "#2a2a35"     # 各種枠・パネル背景
        self.fg_light = "#e0e0e0"     # 基本文字
        self.fg_white = "#ffffff"     # 強調文字
        self.bg_input = "#3e3e4a"     # 入力欄背景
        
        self.root.configure(bg=self.bg_dark)

        # 🎨 ttkスタイルのカスタム（タブやコンボボックスのダーク化）
        self.style = ttk.Style()
        self.style.theme_use("default")
        
        # タブのスタイル設定
        self.style.configure("TNotebook", background=self.bg_dark, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=self.bg_panel, foreground=self.fg_light, borderwidth=1, padding=[10, 4])
        self.style.map("TNotebook.Tab", background=[("selected", self.bg_input)], foreground=[("selected", self.fg_white)])
        
        # コンボボックスのスタイル設定
        self.style.configure("TCombobox", fieldbackground=self.bg_input, background=self.bg_panel, foreground=self.fg_white)
        self.style.map("TCombobox", fieldbackground=[("readonly", self.bg_input)], foreground=[("readonly", self.fg_white)])

        self.grades = ["初級", "見習い", "熟練", "専門", "職人", "名匠", "道人"]
        
        self.skills_layout = [
            ("gathering", "採集"),  ("processing", "加工"),
            ("fishing", "釣り"),    ("hunting", "狩猟"),
            ("cooking", "料理"),    ("alchemy", "錬金"),
            ("training", "調教"),   ("trade", "貿易"),
            ("farming", "栽培"),    ("sailing", "航海"),
            ("barter", "交易")
        ]
        
        self.equip_slots = [
            ("helm", "頭防具"), ("armor", "体防具/服"), ("glove", "手防具"), ("shoes", "足防具"),
            ("main_wp", "メイン武器"), ("sub_wp", "補助武器"), ("awk_wp", "覚醒武器"),
            ("necklace", "ネックレス"), ("belt", "ベルト"),
            ("ring1", "リング1"), ("ring2", "リング2"),
            ("ear1", "イヤリング1"), ("ear2", "イヤリング2"),
            ("stone", "錬金石"), ("tool", "生活ツール")
        ]

        # --- UI構築 ---
        self.create_top_menu()
        
        frame_main = tk.Frame(root, bg=self.bg_dark)
        frame_main.pack(expand=True, fill="both", padx=10, pady=5)

        # 左側：タブエリア
        self.notebook = ttk.Notebook(frame_main)
        self.notebook.pack(side="left", expand=True, fill="both", padx=(0, 5))
        
        self.tab_status = tk.Frame(self.notebook, bg=self.bg_dark)
        self.tab_equip = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_status, text=" 戦闘・生活ステータス ")
        self.notebook.add(self.tab_equip, text=" 装備構成 ")

        self.create_status_tab()
        self.create_equip_tab()

        # 右側：ペーストエリア
        self.create_paste_area(frame_main)

        # 下部：D&Dエリア、日付指定エリア＆保存ボタン
        self.create_bottom_area()

        # 🔄 前回データのロード
        self.load_previous_data()

    def create_top_menu(self):
        frame_top = tk.Frame(self.root, bg=self.bg_dark)
        frame_top.pack(fill="x", padx=10, pady=5)
        
        btn_copy = tk.Button(
            frame_top, text="📋 ここ押してAIにペースト&画像貼る", 
            bg="#d87d00", fg="white", font=("Arial", 10, "bold"), relief="flat", activebackground="#f58600", activeforeground="white"
        )
        btn_copy.config(command=self.copy_prompt)
        btn_copy.pack(side="left", expand=True, fill="x", padx=2, ipady=5)

        btn_dashboard = tk.Button(
            frame_top, text="📊 ダッシュボードを開く", 
            bg="#00796b", fg="white", font=("Arial", 10, "bold"), relief="flat", activebackground="#009688", activeforeground="white"
        )
        btn_dashboard.config(command=self.open_dashboard)
        btn_dashboard.pack(side="left", expand=True, fill="x", padx=2, ipady=5)

    def create_status_tab(self):
        lbl_battle = tk.LabelFrame(self.tab_status, text="戦闘経験値", font=("Arial", 10, "bold"), fg="#8ab4f8", bg=self.bg_panel, bd=1)
        lbl_battle.pack(fill="x", padx=10, pady=5)
        
        tk.Label(lbl_battle, text="レベル:", fg=self.fg_light, bg=self.bg_panel).grid(row=0, column=0, padx=5, pady=8)
        self.ent_b_lv = tk.Entry(lbl_battle, width=6, bg=self.bg_input, fg=self.fg_white, insertbackground="white", bd=0)
        self.ent_b_lv.grid(row=0, column=1, padx=5)
        
        tk.Label(lbl_battle, text="経験値(％):", fg=self.fg_light, bg=self.bg_panel).grid(row=0, column=2, padx=5, pady=8)
        self.ent_b_exp = tk.Entry(lbl_battle, width=12, bg=self.bg_input, fg=self.fg_white, insertbackground="white", bd=0)
        self.ent_b_exp.grid(row=0, column=3, padx=5)

        lbl_life = tk.LabelFrame(self.tab_status, text="生活経験値（ゲーム内順）", font=("Arial", 10, "bold"), fg="#81c995", bg=self.bg_panel, bd=1)
        lbl_life.pack(expand=True, fill="both", padx=10, pady=5)

        self.life_inputs = {}
        for i, (key, name) in enumerate(self.skills_layout):
            is_bold = key in ["gathering", "processing"]
            tk.Label(lbl_life, text=f"{name}:", font=("Arial", 10, "bold" if is_bold else "normal"), fg=self.fg_white if is_bold else self.fg_light, bg=self.bg_panel).grid(row=i, column=0, sticky="w", padx=15, pady=4)
            
            combo = ttk.Combobox(lbl_life, values=self.grades, width=8, state="readonly")
            combo.grid(row=i, column=1, padx=5)
            
            ent_lv = tk.Entry(lbl_life, width=5, bg=self.bg_input, fg=self.fg_white, insertbackground="white", bd=0)
            ent_lv.grid(row=i, column=2, padx=5)
            tk.Label(lbl_life, text="Lv", fg=self.fg_light, bg=self.bg_panel).grid(row=i, column=3)
            
            ent_exp = tk.Entry(lbl_life, width=10, bg=self.bg_input, fg=self.fg_white, insertbackground="white", bd=0)
            ent_exp.grid(row=i, column=4, padx=5)
            tk.Label(lbl_life, text="％", fg=self.fg_light, bg=self.bg_panel).grid(row=i, column=5)
            
            self.life_inputs[key] = {"g": combo, "lv": ent_lv, "exp": ent_exp}

    def create_equip_tab(self):
        lbl_equip = tk.LabelFrame(self.tab_equip, text="現在の装備構成", font=("Arial", 10, "bold"), fg="#c5a5c5", bg=self.bg_panel, bd=1)
        lbl_equip.pack(expand=True, fill="both", padx=10, pady=5)

        self.equip_inputs = {}
        for i, (key, name) in enumerate(self.equip_slots):
            row_idx = i % 8
            col_idx = 0 if i < 8 else 3
            tk.Label(lbl_equip, text=f"{name}:", fg=self.fg_light, bg=self.bg_panel).grid(row=row_idx, column=col_idx, sticky="e", padx=5, pady=6)
            ent_eq = tk.Entry(lbl_equip, width=22, bg=self.bg_input, fg=self.fg_white, insertbackground="white", bd=0)
            ent_eq.grid(row=row_idx, column=col_idx+1, padx=5, pady=6)
            self.equip_inputs[key] = ent_eq

    def create_paste_area(self, parent):
        frame_right = tk.LabelFrame(parent, text=" 📝 Geminiのテキストを直接ペースト 📝 ", font=("Arial", 10, "bold"), fg=self.fg_white, bg=self.bg_panel, bd=1)
        frame_right.pack(side="right", fill="both", padx=(5, 0), ipadx=5)
        tk.Label(frame_right, text="JSONテキストをここに貼り付けて\n下の「反映」ボタンを押してください", bg=self.bg_panel, fg="#aaa", font=("Arial", 9)).pack(pady=5)
        
        self.txt_paste = tk.Text(frame_right, width=32, height=35, font=("Courier", 9), bg=self.bg_input, fg=self.fg_white, insertbackground="white", bd=0)
        self.txt_paste.pack(expand=True, fill="both", padx=5, pady=5)
        
        btn_apply_text = tk.Button(frame_right, text="⚡ テキスト入力を反映 ⚡", bg="#388e3c", fg="white", font=("Arial", 10, "bold"), relief="flat", activebackground="#4caf50", activeforeground="white")
        btn_apply_text.config(command=self.apply_pasted_text)
        btn_apply_text.pack(fill="x", padx=5, pady=5)

    def create_bottom_area(self):
        # 1. D&Dエリア
        self.dnd_frame = tk.LabelFrame(self.root, text=" 🌟 GeminiのJSONファイルをここにドロップ 🌟 ", bg=self.bg_panel, fg=self.fg_white, font=("Arial", 10, "bold"), bd=1)
        self.dnd_frame.pack(fill="x", padx=10, pady=5)
        
        self.dnd_label = tk.Label(self.dnd_frame, text="ここに .json ファイルをドラッグ＆ドロップしても読み込めます", bg=self.bg_panel, fg="#aaa", height=2)
        self.dnd_label.pack(fill="both", expand=True)
        
        self.dnd_label.drop_target_register(DND_FILES)
        self.dnd_label.dnd_bind('<<Drop>>', self.drop_json)

        # 2. 📅 日付指定エリア
        frame_date = tk.LabelFrame(self.root, text=" 📅 日記の記録日付を指定 📅 ", font=("Arial", 10, "bold"), fg="#ffb74d", bg=self.bg_panel, bd=1)
        frame_date.pack(fill="x", padx=10, pady=5)
        
        now = datetime.now()
        years_list = [str(y) for y in range(now.year - 10, now.year + 2)]
        
        tk.Label(frame_date, text="年:", fg=self.fg_light, bg=self.bg_panel).pack(side="left", padx=(15, 2), pady=8)
        self.combo_year = ttk.Combobox(frame_date, values=years_list, width=6, state="readonly")
        self.combo_year.set(str(now.year))
        self.combo_year.pack(side="left", padx=5)
        
        tk.Label(frame_date, text="月:", fg=self.fg_light, bg=self.bg_panel).pack(side="left", padx=(10, 2))
        self.combo_month = ttk.Combobox(frame_date, values=[f"{m:02d}" for m in range(1, 13)], width=4, state="readonly")
        self.combo_month.set(f"{now.month:02d}")
        self.combo_month.pack(side="left", padx=5)
        
        tk.Label(frame_date, text="日:", fg=self.fg_light, bg=self.bg_panel).pack(side="left", padx=(10, 2))
        self.combo_day = ttk.Combobox(frame_date, values=[f"{d:02d}" for d in range(1, 32)], width=4, state="readonly")
        self.combo_day.set(f"{now.day:02d}")
        self.combo_day.pack(side="left", padx=5)
        
        tk.Label(frame_date, text="※過去10年間まで設定可能", fg="#aaa", font=("Arial", 9), bg=self.bg_panel).pack(side="left", padx=15)

        # 3. 保存ボタン
        btn_save = tk.Button(self.root, text="💾 指定した日付で日記を保存 (前回値を更新)", bg="#1976d2", fg="white", font=("Arial", 12, "bold"), relief="flat", activebackground="#2196f3", activeforeground="white")
        btn_save.config(command=self.save_to_db)
        btn_save.pack(fill="x", padx=10, pady=10)

    def copy_prompt(self):
        prompt_text = """添付した『黒い砂漠』の画像からステータス（戦闘レベル・経験値、および各生活等級・レベル・経験値）を読み取り、以下のJSONフォーマット通りのデータだけを出力してください。余計な解説の文章は一切不要です。

{
  "battle_lv": "61",
  "battle_exp": "29.504",
  "skills": {
    "gathering": {"g": "専門", "lv": "10", "exp": "73.35"},
    "processing": {"g": "職人", "lv": "1", "exp": "20.36"},
    "fishing": {"g": "道人", "lv": "24", "exp": "55.97"},
    "hunting": {"g": "初級", "lv": "9", "exp": "92.79"},
    "cooking": {"g": "職人", "lv": "10", "exp": "0.07"},
    "alchemy": {"g": "熟練", "lv": "10", "exp": "76.21"},
    "training": {"g": "名匠", "lv": "10", "exp": "13.10"},
    "trade": {"g": "名匠", "lv": "8", "exp": "98.84"},
    "farming": {"g": "専門", "lv": "6", "exp": "86.03"},
    "sailing": {"g": "初級", "lv": "5", "exp": "54.06"},
    "barter": {"g": "初級", "lv": "1", "exp": "0.00"}
  }
}"""
        pyperclip.copy(prompt_text)
        messagebox.showinfo("コピー完了", "Geminiへの指示文をクリップボードにコピーしました！")

    def load_previous_data(self):
        row = self.db.get_latest_record()
        if row:
            self.ent_b_lv.insert(0, row["battle_lv"])
            self.ent_b_exp.insert(0, row["battle_exp"])
            for key, inputs in self.life_inputs.items():
                inputs["g"].set(row[f"{key}_g"] or "初級")
                inputs["lv"].insert(0, row[f"{key}_lv"] or "1")
                inputs["exp"].insert(0, row[f"{key}_exp"] or "0.00")
            for key, entry in self.equip_inputs.items():
                entry.insert(0, row[f"eq_{key}"] or "")
        else:
            self.ent_b_lv.insert(0, "1")
            self.ent_b_exp.insert(0, "0.00")
            for key, inputs in self.life_inputs.items():
                inputs["g"].set("初級")
                inputs["lv"].insert(0, "1")
                inputs["exp"].insert(0, "0.00")

    def update_form_fields(self, data):
        self.ent_b_lv.delete(0, tk.END)
        self.ent_b_lv.insert(0, data.get("battle_lv", "1"))
        self.ent_b_exp.delete(0, tk.END)
        self.ent_b_exp.insert(0, data.get("battle_exp", "0.00"))
        
        skills_data = data.get("skills", {})
        for key, inputs in self.life_inputs.items():
            s_data = skills_data.get(key, {})
            inputs["g"].set(s_data.get("g", "初級"))
            inputs["lv"].delete(0, tk.END)
            inputs["lv"].insert(0, s_data.get("lv", "1"))
            inputs["exp"].delete(0, tk.END)
            inputs["exp"].insert(0, s_data.get("exp", "0.00"))

    def apply_pasted_text(self):
        raw_text = self.txt_paste.get("1.0", tk.END).strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json")[1]
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]
        raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)
            self.update_form_fields(data)
            messagebox.showinfo("成功", "テキストからステータスを自動入力しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"JSONの解析に失敗しました。\n{e}")

    def drop_json(self, event):
        file_path = event.data.strip('{}')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.update_form_fields(data)
            self.dnd_label.config(text=f"読み込み成功！: {os.path.basename(file_path)}", fg="#81c995")
            messagebox.showinfo("成功", "JSONファイルから自動入力しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました。\n{e}")

    def save_to_db(self):
        year = self.combo_year.get()
        month = self.combo_month.get()
        day = self.combo_day.get()
        
        try:
            input_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("日付エラー", f"選択された日付【{year}年{month}月{day}日】はカレンダー上に存在しません。")
            return

        if input_date > datetime.now():
            messagebox.showerror("日付エラー", "未来の日付で日記を記録することはできません。")
            return

        selected_date = f"{year}-{month}-{day} 12:00:00"
        
        current_data = {
            "date": selected_date,
            "battle_lv": self.ent_b_lv.get(),
            "battle_exp": self.ent_b_exp.get()
        }
        for key, inputs in self.life_inputs.items():
            current_data[f"{key}_g"] = inputs["g"].get()
            current_data[f"{key}_lv"] = inputs["lv"].get()
            current_data[f"{key}_exp"] = inputs["exp"].get()
        for key, entry in self.equip_inputs.items():
            current_data[f"eq_{key}"] = entry.get()

        try:
            self.db.save_record(current_data)
            messagebox.showinfo("保存成功", f"【{year}-{month}-{day}】の日記としてデータベースに記録しました！")
        except Exception as e:
            messagebox.showerror("エラー", f"データベースへの保存に失敗しました。\n{e}")

    def open_dashboard(self):
        rows = self.db.get_all_records()
        if not rows:
            messagebox.showinfo("情報", "データがまだありません。日記を1件以上保存してください。")
            return

        data_list = []
        for r in rows:
            d = dict(r)
            data_list.append(d)
        json_data = json.dumps(data_list, ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>黒い砂漠 成長ダッシュボード</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Meiryo, sans-serif; background: #1e1e24; color: #e0e0e0; margin: 20px; }}
        h1, h2 {{ color: #ffffff; border-bottom: 2px solid #3f51b5; padding-bottom: 8px; margin-top: 30px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .controls {{ background: #2a2a35; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 15px; align-items: center; }}
        select, button {{ background: #3f51b5; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; }}
        select {{ background: #4e4e61; }}
        button:hover {{ background: #5c6bc0; }}
        .chart-container {{ background: #2a2a35; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
        
        .milestone-container {{ background: #2a2a35; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #ff9800; }}
        .milestone-table {{ width: 100%; border-collapse: collapse; }}
        .milestone-table th {{ background: #ff9800; color: #1e1e24; font-weight: bold; }}
        .milestone-table td, .milestone-table th {{ padding: 8px; text-align: center; border-bottom: 1px solid #444; }}

        .equip-history-container {{ background: #2a2a35; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #9c27b0; }}
        .equip-card {{ background: #343444; padding: 12px; margin-bottom: 10px; border-radius: 6px; }}
        .equip-date {{ font-size: 13px; color: #b388ff; font-weight: bold; margin-bottom: 5px; }}
        .equip-diff {{ display: flex; flex-wrap: wrap; gap: 10px; font-size: 14px; }}
        .equip-badge {{ background: #4a148c; color: #ea80fc; padding: 3px 8px; border-radius: 4px; font-weight: bold; }}

        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: #2a2a35; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #444; }}
        th {{ background: #3f51b5; color: white; }}
        tr:hover {{ background: #343444; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚔️ 黒い砂漠 成長ダッシュボード</h1>
        
        <h2>⏱️ レベルアップの軌跡（かかった日数）</h2>
        <div class="milestone-container">
            <table class="milestone-table" id="milestoneTable">
                <thead>
                    <tr>
                        <th>到達レベル</th>
                        <th>達成日</th>
                        <th>前レベルからの所要日数</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <h2>🛡️ 装備の更新履歴</h2>
        <div class="equip-history-container" id="equipHistory"></div>
        
        <h2>📈 成長グラフ</h2>
        <div class="controls">
            <label>表示対象: </label>
            <select id="targetSelect" onchange="updateChart()">
                <option value="battle">戦闘レベル・経験値</option>
                <option value="gathering">採集</option>
                <option value="processing">加工</option>
                <option value="fishing">釣り</option>
                <option value="hunting">狩猟</option>
                <option value="cooking">料理</option>
                <option value="alchemy">錬金</option>
                <option value="training">調教</option>
                <option value="trade">貿易</option>
                <option value="farming">栽培</option>
                <option value="sailing">航海</option>
                <option value="barter">交易</option>
            </select>
            
            <label>期間: </label>
            <select id="periodSelect" onchange="updateChart()">
                <option value="all">全期間</option>
                <option value="30">直近30日</option>
                <option value="7">直近7日</option>
            </select>
        </div>

        <div class="chart-container">
            <canvas id="growthChart" height="100"></canvas>
        </div>
    </div>

    <script>
        const rawData = {json_data};
        let chart = null;

        // 等級の基準インデックス
        const gradeMap = {{ "初級":0, "見習い":1, "熟練":2, "専門":3, "職人":4, "名匠":5, "道人":6 }};
        
        // 🎨 等級ごとのカラーマップ（ゲーム内イメージに準拠）
        const colorMap = {{
            "初級": "#aaaaaa",   // 灰
            "見習い": "#5c6bc0", // 青
            "熟練": "#26a69a",   // 青緑
            "専門": "#66bb6a",   // 緑
            "職人": "#ffb74d",   // 薄オレンジ
            "名匠": "#ab47bc",   // 紫
            "道人": "#ff9800"    // オレンジ（ゴールド）
        }};

        const equipSlots = {{
            "eq_helm": "頭防具", "eq_armor": "体防具/服", "eq_glove": "手防具", "eq_shoes": "足防具",
            "eq_main_wp": "メイン武器", "eq_sub_wp": "補助武器", "eq_awk_wp": "覚醒武器",
            "eq_necklace": "首飾り", "eq_belt": "ベルト",
            "eq_ring1": "リング1", "eq_ring2": "リング2",
            "eq_ear1": "耳飾り1", "eq_ear2": "耳飾り2",
            "eq_stone": "錬金石", "eq_tool": "生活ツール"
        }};

        function init() {{
            calculateMilestones();
            calculateEquipHistory();
            updateChart();
            buildTable();
        }}

        function calculateMilestones() {{
            const tbody = document.querySelector('#milestoneTable tbody');
            tbody.innerHTML = "";
            let lastLv = null;
            let lastDate = null;

            rawData.forEach((d, index) => {{
                const currentLv = parseInt(d.battle_lv);
                if (!currentLv) return;

                if (lastLv === null) {{
                    lastLv = currentLv;
                    lastDate = new Date(d.date.replace(/-/g, '/'));
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td>Lv ${{currentLv}}</td><td>${{d.date.split(' ')[0]}}</td><td>（計測開始点）</td>`;
                    tbody.appendChild(tr);
                    return;
                }}

                if (currentLv > lastLv) {{
                    const currentDate = new Date(d.date.replace(/-/g, '/'));
                    const diffTime = Math.abs(currentDate - lastDate);
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td style="font-weight:bold; color:#ff9800;">Lv ${{lastLv}} ➔ Lv ${{currentLv}}</td>
                        <td>${{d.date.split(' ')[0]}}</td>
                        <td style="font-weight:bold;">${{diffDays}} 日</td>
                    `;
                    tbody.appendChild(tr);

                    lastLv = currentLv;
                    lastDate = currentDate;
                }}
            }});

            if (tbody.innerHTML === "") {{
                tbody.innerHTML = `<tr><td colspan="3">レベルアップのデータがまだ記録されていません。</td></tr>`;
            }}
        }}

        function calculateEquipHistory() {{
            const container = document.getElementById('equipHistory');
            container.innerHTML = "";
            let prevEquip = null;
            let changeLogs = [];

            rawData.forEach((d) => {{
                if (prevEquip === null) {{
                    prevEquip = d;
                    return;
                }}

                let changes = [];
                for (let key in equipSlots) {{
                    const oldVal = prevEquip[key] || "";
                    const newVal = d[key] || "";
                    if (oldVal !== newVal) {{
                        changes.push(`<span class="equip-badge">${{equipSlots[key]}}</span> ${{oldVal || '未装着'}} ➔ <b>${{newVal || '未装着'}}</b>`);
                    }}
                }}

                if (changes.length > 0) {{
                    changeLogs.push({{ date: d.date.split(' ')[0], changes: changes }});
                }}
                prevEquip = d;
            }});

            if (changeLogs.length === 0) {{
                container.innerHTML = `<div style="color: #aaa; text-align: center; padding: 10px;">装備の変更履歴はまだありません。（データが2件以上必要です）</div>`;
            }} else {{
                changeLogs.reverse().forEach(log => {{
                    const card = document.createElement('div');
                    card.className = 'equip-card';
                    card.innerHTML = `
                        <div class="equip-date">📅 ${{log.date}} の変更点</div>
                        <div class="equip-diff">${{log.changes.join(' | ')}}</div>
                    `;
                    container.appendChild(card);
                }});
            }}
        }}

        // 🚀 【等倍計算に変更】1レベル上昇 ＝ グラフの1メモリ上昇に統一
        function getScaledScore(grade, lv, exp) {{
            const gIdx = gradeMap[grade] || 0;
            // 1等級ごとに一律「30マス分」の高さを持たせる（初級Lv.1=1, 見習いLv.1=31 ...）
            return (gIdx * 30) + lv + (exp / 100);
        }}

        function updateChart() {{
            const target = document.getElementById('targetSelect').value;
            const period = document.getElementById('periodSelect').value;
            
            let filteredData = [...rawData];
            if (period !== 'all') {{
                const cutoff = new Date();
                cutoff.setDate(cutoff.getDate() - parseInt(period));
                filteredData = rawData.filter(d => new Date(d.date) >= cutoff);
            }}

            const labels = filteredData.map(d => d.date.split(' ')[0]); 
            let dataPoints = [];
            let displayLabels = []; 
            let pointColors = []; // 点ごとに色を変える
            let pointRadius = []; // 点ごとに大きさを変える
            let highestGrade = "初級"; 
            
            let labelText = document.getElementById('targetSelect').selectedOptions[0].text;

            if (target === 'battle') {{
                dataPoints = filteredData.map(d => {{
                    const lv = parseFloat(d.battle_lv) || 0;
                    const exp = parseFloat(d.battle_exp) || 0;
                    displayLabels.push(`Lv.${{lv}} (${{exp.toFixed(3)}}%)`);
                    pointColors.push("#4caf50"); // 戦闘は緑固定
                    pointRadius.push(3);
                    
                    // 🚀 戦闘も「1レベル＝1マス」の等倍で綺麗に上昇
                    return lv + (exp / 100);
                }});
            }} else {{
                labelText = document.getElementById('targetSelect').selectedOptions[0].text; 
                dataPoints = filteredData.map(d => {{
                    const g = d[target + '_g'] || "初級";
                    const lv = parseFloat(d[target + '_lv']) || 1;
                    const exp = parseFloat(d[target + '_exp']) || 0;
                    
                    displayLabels.push(`${{g}} Lv.${{lv}} (${{exp.toFixed(2)}}%)`);
                    
                    // 等級に応じたカラーと点の大きさを設定
                    const color = colorMap[g] || "#aaa";
                    pointColors.push(color);
                    
                    if (g === "道人") {{
                        pointRadius.push(5);
                    }} else if (g === "名匠") {{
                        pointRadius.push(4);
                    }} else {{
                        pointRadius.push(3);
                    }}
                    
                    if (gradeMap[g] > gradeMap[highestGrade]) {{
                        highestGrade = g;
                    }}
                    
                    // 🚀 生活も等倍スコアをプロット
                    return getScaledScore(g, lv, exp);
                }});
            }}

            if (chart) chart.destroy();

            const mainLineColor = target === 'battle' ? '#4caf50' : (colorMap[highestGrade] || '#4caf50');
            const isDojin = highestGrade === "道人" && target !== 'battle';

            const ctx = document.getElementById('growthChart').getContext('2d');
            chart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [{{
                        label: labelText,
                        data: dataPoints,
                        borderColor: mainLineColor,
                        borderWidth: isDojin ? 4 : 2, 
                        backgroundColor: 'rgba(42, 42, 53, 0.1)',
                        tension: 0.1,
                        fill: false,
                        pointBackgroundColor: pointColors, 
                        pointBorderColor: pointColors,
                        pointRadius: pointRadius, 
                        pointHoverRadius: 7
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        x: {{ grid: {{ color: '#333' }}, ticks: {{ color: '#aaa' }} }},
                        y: {{ 
                            grid: {{ color: '#333' }}, 
                            ticks: {{ 
                                color: '#aaa',
                                display: false // 内部計算用の数値軸は非表示
                            }} 
                        }}
                    }},
                    plugins: {{ 
                        legend: {{ labels: {{ color: '#fff' }} }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const index = context.dataIndex;
                                    return ` ${{labelText}}: ${{displayLabels[index]}}`;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        function buildTable() {{
        }}
        window.onload = init;
    </script>
</body>
</html>
"""
        filename = "bdo_dashboard.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        webbrowser.open("file://" + os.path.abspath(filename))


if __name__ == "__main__":
    db_manager = BdoDatabase()
    root = TkinterDnD.Tk()
    app = BdoDiaryApp(root, db_manager)
    root.mainloop()