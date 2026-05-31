import sqlite3
import urllib.request
import re
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox, ttk


class DatabaseManager:
    def __init__(self, db_name="crawler_search.db"):
        self.db_name = db_name
        self._init_database()

    def _init_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS web_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL
                )
            ''')
            conn.commit()

    def add_url(self, url: str) -> bool:
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO web_targets (url) VALUES (?)", (url,))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_all_urls(self) -> list:
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url FROM web_targets")
            return [row[0] for row in cursor.fetchall()]

    def clear_database(self):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM web_targets")
            conn.commit()


class WebScraper:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    def _get_clean_text(self, url: str) -> str:
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html_content, 'html.parser')
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                return soup.get_text().lower()
        except Exception:
            return ""

    def count_keyword_frequency(self, url: str, keyword: str) -> int:
        page_text = self._get_clean_text(url)
        if not page_text:
            return -1
        matches = re.findall(re.escape(keyword.lower()), page_text)
        return len(matches)


class SearchAppGUI:
    def __init__(self, root):
        self.db_manager = DatabaseManager()
        self.scraper = WebScraper()

        self.root = root
        self.root.title("Система ранжування веб-сторінок за релевантністю")
        self.root.geometry("650x550")
        self.root.minsize(600, 450)

        frame_url = tk.LabelFrame(root, text=" Керування базою веб-ресурсів ", padx=10, pady=10)
        frame_url.pack(fill="x", padx=15, pady=10)

        tk.Label(frame_url, text="Введіть URL:").pack(side="left", padx=5)
        self.entry_url = tk.Entry(frame_url, width=40)
        self.entry_url.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_url.insert(0, "https://")

        btn_add = tk.Button(frame_url, text="Додати сайт", command=self._action_add_url, bg="#d4edda")
        btn_add.pack(side="left", padx=5)

        frame_search = tk.LabelFrame(root, text=" Пошук контенту та Ранжування ", padx=10, pady=10)
        frame_search.pack(fill="x", padx=15, pady=5)

        tk.Label(frame_search, text="Ключове слово:").pack(side="left", padx=5)
        self.entry_keyword = tk.Entry(frame_search, width=30)
        self.entry_keyword.pack(side="left", fill="x", expand=True, padx=5)

        btn_search = tk.Button(frame_search, text="🔍 Запустити аналіз", command=self._action_search, bg="#cce5ff",
                               font=("Arial", 10, "bold"))
        btn_search.pack(side="left", padx=5)

        frame_results = tk.LabelFrame(root, text=" Результати аналізу та Рейтинг сайтів ", padx=10, pady=10)
        frame_results.pack(fill="both", expand=True, padx=15, pady=10)

        columns = ("rating", "count", "url")
        self.tree = ttk.Treeview(frame_results, columns=columns, show="headings")

        self.tree.heading("rating", text="Ранг (Місце)")
        self.tree.heading("count", text="Частота слова")
        self.tree.heading("url", text="Веб-адреса сторінки (URL)")

        self.tree.column("rating", width=90, anchor="center")
        self.tree.column("count", width=120, anchor="center")
        self.tree.column("url", width=380, anchor="w")

        self.tree.pack(fill="both", expand=True)

        frame_footer = tk.Frame(root, pady=5)
        frame_footer.pack(fill="x", padx=15)

        btn_view_all = tk.Button(frame_footer, text="Показати всі сайти в базі даних", command=self._action_view_urls)
        btn_view_all.pack(side="left", padx=5)

        btn_clear = tk.Button(frame_footer, text="🗑 Очистити базу даних", command=self._action_clear_db, bg="#f8d7da")
        btn_clear.pack(side="right", padx=5)

    def _action_add_url(self):
        url = self.entry_url.get().strip()
        if not (url.startswith("http://") or url.startswith("https://")) or len(url) < 10:
            messagebox.showerror("Помилка валідації", "URL повинен починатися з http:// або https://")
            return

        if self.db_manager.add_url(url):
            messagebox.showinfo("Успіх", f"Сайт {url} успішно збережено в базі!")
            self.entry_url.delete(0, tk.END)
            self.entry_url.insert(0, "https://")
            self._action_view_urls()
        else:
            messagebox.showwarning("Дублікат", "Це посилання вже було додано до бази даних раніше.")

    def _action_search(self):
        keyword = self.entry_keyword.get().strip()
        if not keyword:
            messagebox.showwarning("Порожній запит", "Будь ласка, введіть слово для пошуку.")
            return

        urls = self.db_manager.get_all_urls()
        if not urls:
            messagebox.showwarning("База порожня", "У базі даних немає сайтів. Спочатку додайте посилання.")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        raw_results = []
        for url in urls:
            count = self.scraper.count_keyword_frequency(url, keyword)
            if count > 0:
                raw_results.append({"url": url, "count": count})
            elif count == -1:
                raw_results.append({"url": f"❌ {url} (Недоступний/Помилка з'єднання)", "count": -1})

        sorted_results = sorted(raw_results, key=lambda item: item["count"], reverse=True)

        if not sorted_results or (len(sorted_results) == 1 and sorted_results[0]["count"] == -1):
            messagebox.showinfo("Результат пошуку", "Збігів ключового слова на доступних сайтах не знайдено.")
            return

        for index, result in enumerate(sorted_results, 1):
            if result["count"] == -1:
                self.tree.insert("", tk.END, values=("—", "Помилка з'єднання", result["url"]))
            else:
                self.tree.insert("", tk.END, values=(f"🏆 {index}", f"{result['count']} раз(и)", result["url"]))

    def _action_view_urls(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        urls = self.db_manager.get_all_urls()
        if not urls:
            self.tree.insert("", tk.END, values=("—", "Порожньо", "База даних не містить жодного посилання"))
            return

        for i, url in enumerate(urls, 1):
            self.tree.insert("", tk.END, values=(i, "В базі даних", url))

    def _action_clear_db(self):
        if messagebox.askyesno("Підтвердження видалення",
                               "Ви дійсно хочете безповоротно видалити ВСІ сайти з бази даних?"):
            self.db_manager.clear_database()
            self._action_view_urls()
            messagebox.showinfo("Видалено", "Локальна база даних успішно очищена.")


if __name__ == "__main__":
    window = tk.Tk()
    app = SearchAppGUI(window)
    window.mainloop()