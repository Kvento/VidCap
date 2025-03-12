import sys
import os
import json

# Указываем путь к папке libs
current_dir = os.path.dirname(os.path.abspath(__file__))
libs_path = os.path.join(current_dir, 'libs')
sys.path.append(libs_path)

import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
from tkinterdnd2 import *

class VideoPlayer:
    def __init__(self, video_path, canvas, root):
        self.video_path = video_path
        self.canvas = canvas
        self.root = root
        self.cap = cv2.VideoCapture(video_path)
        self.playing = False
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.delay = int(1000 / self.fps) if self.fps > 0 else 30
        self.original_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.original_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))  # Длина видео в кадрах

    def play(self):
        if not self.playing:
            self.playing = True
            self._play_video()

    def stop(self):
        self.playing = False
        self.release()

    def release(self):
        if self.cap.isOpened():
            self.cap.release()

    def _resize_frame(self, frame, width, height):
        """Масштабирование кадра с сохранением пропорций"""
        aspect_ratio = self.original_width / self.original_height
        target_ratio = width / height
        if aspect_ratio > target_ratio:
            new_width = width
            new_height = int(width / aspect_ratio)
        else:
            new_height = height
            new_width = int(height * aspect_ratio)
        return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    def _play_video(self):
        if not self.playing:
            return
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            frame = self.cap.read()[1]
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Получаем текущий размер канваса
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Масштабируем кадр
        frame = self._resize_frame(frame, canvas_width, canvas_height)
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image)
        
        # Центрируем изображение
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
        self.canvas.photo = photo
        self.root.after(self.delay, self._play_video)

class VideoCaptionEditor:
    def __init__(self, root):
        self.root = root
        self.player = None
        
        # Загрузка переводов из файла
        with open('translations.json', 'r', encoding='utf-8') as f:
            self.translations = json.load(f)
        
        # Определение пути к файлу настроек
        self.settings_file = 'settings.json'
        
        # Загрузка настроек
        self.load_settings()
        
        self.video_folder = None
        self.create_gui()  # Сначала создаём интерфейс
        
        # Определение тем
        self.themes = {
            'light': {
                'background': 'white',
                'text': 'black',
                'button_bg': '#f0f0f0',
                'button_fg': 'black',
                'border': 'white',
                'preview_bg': '#f0f0f0',
                'text_bg': '#f0f0f0'
            },
            'dark': {
                'background': '#2c3e50',
                'text': 'white',
                'button_bg': '#34495e',
                'button_fg': 'white',
                'border': '#2c3e50',
                'preview_bg': '#1f2b38',
                'text_bg': '#1f2b38'
            }
        }
        
        self.apply_theme()         # Применяем тему
        self.update_localization()   # Обновляем локализацию
        
        # Устанавливаем начальный размер окна и центруем его с уменьшенным верхним отступом
        initial_width = 1280
        initial_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - initial_width) // 2
        y = (screen_height - initial_height) // 4  # Верхний отступ уменьшен (25% от оставшегося пространства)
        self.root.geometry(f"{initial_width}x{initial_height}+{x}+{y}")
        
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

    def load_settings(self):
        """Загрузка настроек из файла"""
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.current_language = settings.get('language', 'ru')
                self.current_theme = settings.get('theme', 'light')
                self.text_size = settings.get('text_size', 12)  # Размер шрифта для text_area
                self.info_size = settings.get('info_size', 9)  # Размер шрифта для video_info_label
        except (FileNotFoundError, json.JSONDecodeError):
            # Если файл не найден или повреждён, используем значения по умолчанию
            self.current_language = 'ru'
            self.current_theme = 'light'
            self.text_size = 12
            self.info_size = 9

    def save_settings(self):
        """Сохранение настроек в файл"""
        settings = {
            'language': self.current_language,
            'theme': self.current_theme,
            'text_size': self.text_size,
            'info_size': self.info_size
        }
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    def create_gui(self):
        self.sidebar = tk.Frame(self.root, width=200, relief=tk.SUNKEN, borderwidth=1)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.scrollbar = tk.Scrollbar(self.sidebar, orient=tk.VERTICAL)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.video_listbox = tk.Listbox(self.sidebar, width=40, height=20, yscrollcommand=self.scrollbar.set)
        self.video_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.video_listbox.bind('<<ListboxSelect>>', self.on_video_select)

        self.scrollbar.config(command=self.video_listbox.yview)

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=34)

        self.video_canvas = tk.Canvas(self.main_frame, bg="black")
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        self.hint_label = tk.Label(self.video_canvas, text="", font=("Arial", 16), fg="white", bg="black")

        self.info_frame = tk.Frame(self.main_frame)
        self.info_frame.pack(pady=(5, 0))

        self.video_info_label = tk.Label(self.info_frame, text="", font=("Arial", self.info_size), anchor=tk.W, justify=tk.LEFT)
        self.video_info_label.pack(side=tk.LEFT)

        self.text_area = tk.Text(self.main_frame, height=0, wrap=tk.WORD, font=("Arial", self.text_size))
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=5)
        self.text_area.bind('<KeyRelease>', self.save_text)

        # Кнопка настроек
        self.settings_button = tk.Button(self.root, text="⚙", command=self.show_settings_menu)
        self.settings_button.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)
        
        # Кнопка "+"
        self.increase_size_button = tk.Button(self.root, text="➕", command=self.increase_text_size)
        self.increase_size_button.place(relx=0.99, rely=0.0, anchor="ne", x=-35, y=5)

        # Кнопка "−"
        self.decrease_size_button = tk.Button(self.root, text="➖", command=self.decrease_text_size)
        self.decrease_size_button.place(relx=0.99, rely=0.0, anchor="ne", x=-65, y=5)

        self.show_hint()

    def increase_text_size(self):
        """Увеличение размера шрифта"""
        self.text_size += 1
        self.info_size += 1
        self.update_text_sizes()
        self.save_settings()

    def decrease_text_size(self):
        """Уменьшение размера шрифта"""
        if self.text_size > 10 and self.info_size > 1:  # Ограничиваем минимальный размер
            self.text_size -= 1
            self.info_size -= 1
            self.update_text_sizes()
            self.save_settings()

    def update_text_sizes(self):
        """Обновление размеров шрифта в интерфейсе"""
        self.text_area.config(font=("Arial", self.text_size))
        self.video_info_label.config(font=("Arial", self.info_size))

    def apply_theme(self):
        """Применение выбранной темы ко всем элементам интерфейса"""
        theme = self.themes[self.current_theme]
        self.root.config(bg=theme['background'])
        self.sidebar.config(bg=theme['background'], highlightbackground=theme['border'], highlightthickness=1)
        self.video_listbox.config(bg=theme['background'], fg=theme['text'])
        self.main_frame.config(bg=theme['background'], highlightbackground=theme['border'], highlightthickness=1)
        self.video_canvas.config(bg=theme['preview_bg'])
        self.hint_label.config(bg=theme['preview_bg'], fg=theme['text'])
        self.info_frame.config(bg=theme['background'], highlightbackground=theme['border'], highlightthickness=1)
        self.video_info_label.config(bg=theme['background'], fg=theme['text'])
        self.text_area.config(bg=theme['text_bg'], fg=theme['text'], insertbackground=theme['text'])
        self.settings_button.config(bg=theme['button_bg'], fg=theme['button_fg'])
        self.increase_size_button.config(bg=theme['button_bg'], fg=theme['button_fg'])
        self.decrease_size_button.config(bg=theme['button_bg'], fg=theme['button_fg'])
        self.scrollbar.config(background=theme['button_bg'], troughcolor=theme['background'], activebackground=theme['button_fg'])

    def update_localization(self):
        lang = self.translations[self.current_language]
        self.root.title(lang['title'])
        self.update_video_info()
        self.show_hint()

    def show_hint(self):
        if self.video_folder is None:
            hint_text = self.translations[self.current_language]['drag_folder_hint']
            self.hint_label.config(text=hint_text)
            self.hint_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            self.hint_label.place_forget()

    def update_video_info(self):
        if self.player:
            lang = self.translations[self.current_language]
            info_text = lang["video_info"].format(
                width=self.player.original_width,
                height=self.player.original_height,
                total_frames=self.player.total_frames,
                fps=self.player.fps
            )
            self.video_info_label.config(text=info_text)
        else:
            self.video_info_label.config(text="")

    def show_settings_menu(self):
        """Динамическое создание меню настроек на основе translations.json"""
        menu = tk.Menu(self.root, tearoff=0)
        
        # Подменю "Язык"
        lang_menu = tk.Menu(menu, tearoff=0)
        for lang_code in self.translations.keys():
            lang_name = self.translations[lang_code].get('language_name', lang_code)
            lang_menu.add_command(label=lang_name, command=lambda lc=lang_code: self.set_language(lc))
        menu.add_cascade(label=self.translations[self.current_language]['language'], menu=lang_menu)
        
        # Подменю "Тема"
        theme_menu = tk.Menu(menu, tearoff=0)
        theme_menu.add_command(label=self.translations[self.current_language]['light_theme'], 
                               command=lambda: self.set_theme('light'))
        theme_menu.add_command(label=self.translations[self.current_language]['dark_theme'], 
                               command=lambda: self.set_theme('dark'))
        menu.add_cascade(label=self.translations[self.current_language]['theme'], menu=theme_menu)
        
        try:
            menu.tk_popup(self.settings_button.winfo_rootx(),
                          self.settings_button.winfo_rooty() + self.settings_button.winfo_height())
        finally:
            menu.grab_release()

    def set_language(self, lang_code):
        """Установка языка и сохранение настроек"""
        self.current_language = lang_code
        self.update_localization()
        self.save_settings()  # Сохраняем настройки после изменения языка

    def set_theme(self, theme):
        """Установка темы и сохранение настроек"""
        self.current_theme = theme
        self.apply_theme()
        self.save_settings()  # Сохраняем настройки после изменения темы

    def on_drop(self, event):
        path = event.data
        if os.path.isdir(path):
            self.video_folder = path
            self.load_videos()
            if self.video_files:
                first_video = os.path.join(self.video_folder, self.video_files[0])
                cap = cv2.VideoCapture(first_video)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                # Расчёт размеров окна на основе видео и дополнительных отступов
                window_width = width + 800 + 20
                window_height = height + 400
                # Ограничение максимального размера окна 95% от разрешения экрана
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                max_width = int(screen_width * 0.95)
                max_height = int(screen_height * 0.95)
                window_width = min(window_width, max_width)
                window_height = min(window_height, max_height)
                # Проверяем текущий отступ от нижней границы окна до нижней границы экрана
                current_y = self.root.winfo_y()
                current_height = self.root.winfo_height()
                current_bottom_margin = screen_height - (current_y + current_height)
                # Если текущий нижний отступ меньше 5% от высоты экрана, выполняем авто-выравнивание
                if (current_bottom_margin / screen_height) < 0.05:
                    new_y = (screen_height - window_height) // 4
                else:
                    new_y = current_y
                # Горизонтальное положение сохраняется
                current_x = self.root.winfo_x()
                self.root.geometry(f"{window_width}x{window_height}+{current_x}+{new_y}")
                # Выделяем первое видео в списке и загружаем его автоматически
                self.video_listbox.selection_clear(0, tk.END)
                self.video_listbox.selection_set(0)
                self.video_listbox.activate(0)
                self.on_video_select(None)
            self.show_hint()
        else:
            print(self.translations[self.current_language]['drop_folder_message'])

    def load_videos(self):
        if self.video_folder:
            self.video_files = [f for f in os.listdir(self.video_folder) if f.endswith('.mp4')]
            self.video_listbox.delete(0, tk.END)
            for video in self.video_files:
                self.video_listbox.insert(tk.END, video)

    def on_video_select(self, event):
        selection = self.video_listbox.curselection()
        if not selection:
            return

        video_name = self.video_listbox.get(selection[0])
        video_path = os.path.join(self.video_folder, video_name)

        if self.player:
            self.player.stop()

        self.player = VideoPlayer(video_path, self.video_canvas, self.root)
        self.player.play()

        self.update_video_info()
        self.show_hint()

        txt_path = os.path.join(self.video_folder, video_name.replace('.mp4', '.txt'))
        self.load_text(txt_path)

    def load_text(self, txt_path):
        self.current_txt_path = txt_path
        self.text_area.delete(1.0, tk.END)
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                self.text_area.insert(tk.END, f.read())

    def save_text(self, event):
        if hasattr(self, 'current_txt_path'):
            text_content = self.text_area.get(1.0, tk.END).strip()
            with open(self.current_txt_path, 'w', encoding='utf-8') as f:
                f.write(text_content)

    def on_closing(self):
        if self.player:
            self.player.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VideoCaptionEditor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    sys.exit(0)  # Завершаем процесс Python после закрытия окна
