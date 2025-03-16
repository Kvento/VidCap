import sys
import os
import json
import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from PIL import Image, ImageTk
from tkinterdnd2 import *

class VideoPlayer:
    def __init__(self, file_path, canvas, root):
        self.file_path = os.path.normpath(file_path)  # Нормализуем путь
        self.canvas = canvas
        self.root = root
        self.is_image = self.is_image_file(self.file_path)
        if self.is_image:
            try:
                # Читаем изображение в байты и декодируем через OpenCV
                with open(self.file_path, 'rb') as f:
                    img_data = np.frombuffer(f.read(), np.uint8)
                self.image = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                if self.image is None:
                    raise ValueError("Не удалось декодировать изображение")
                self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                self.original_width, self.original_height = self.image.shape[1], self.image.shape[0]
                self.total_frames = 1
                self.fps = 0
            except Exception as e:
                raise ValueError(f"Ошибка загрузки изображения {self.file_path}: {e}")
        else:
            # Для видео используем VideoCapture с диагностикой
            self.cap = cv2.VideoCapture(self.file_path)
            if not self.cap.isOpened():
                raise ValueError(f"Не удалось открыть видео {self.file_path}")
            self.playing = False
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.delay = int(1000 / self.fps) if self.fps > 0 else 30
            self.original_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.original_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def is_image_file(self, file_path):
        image_extensions = ('.jpg', '.png')
        return file_path.lower().endswith(image_extensions)

    def play(self):
        if self.is_image:
            self._display_image()
        else:
            if not self.playing:
                self.playing = True
                self._play_video()

    def stop(self):
        if not self.is_image:
            self.playing = False
            self.release()

    def release(self):
        if not self.is_image and self.cap.isOpened():
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
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        frame = self._resize_frame(frame, canvas_width, canvas_height)
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
        self.canvas.photo = photo
        self.root.after(self.delay, self._play_video)

    def _display_image(self):
        if self.canvas.winfo_width() <= 1 or self.canvas.winfo_height() <= 1:
            self.root.after(100, self._display_image)
            return
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        frame = self._resize_frame(self.image, canvas_width, canvas_height)
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
        self.canvas.photo = photo

class VideoCaptionEditor:
    def __init__(self, root):
        self.root = root
        self.player = None
        with open('translations.json', 'r', encoding='utf-8') as f:
            self.translations = json.load(f)
        self.settings_file = 'settings.json'
        self.load_settings()
        self.video_folder = None
        self.create_gui()
        self.themes = {
            'light': {
                'background': 'white',
                'text': 'black',
                'button_bg': '#f0f0f0',
                'button_fg': 'black',
                'border': 'white',
                'preview_bg': '#f0f0f0',
                'text_bg': '#f0f0f0',
                'select_bg': '#c0c0c0',  # Цвет фона выделения для светлой темы
                'select_fg': 'black'     # Цвет текста выделения для светлой темы
            },
            'dark': {
                'background': '#2c3e50',
                'text': 'white',
                'button_bg': '#34495e',
                'button_fg': 'white',
                'border': '#2c3e50',
                'preview_bg': '#1f2b38',
                'text_bg': '#1f2b38',
                'select_bg': '#4a708b',  # Цвет фона выделения для тёмной темы
                'select_fg': 'white'     # Цвет текста выделения для тёмной темы
            }
        }
        self.apply_theme()
        self.update_localization()
        initial_width = 1280
        initial_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - initial_width) // 2
        y = (screen_height - initial_height) // 14
        self.root.geometry(f"{initial_width}x{initial_height}+{x}+{y}")
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

    def load_settings(self):
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.current_language = settings.get('language', 'ru')
                self.current_theme = settings.get('theme', 'light')
                self.text_size = settings.get('text_size', 12)
                self.info_size = settings.get('info_size', 9)
        except (FileNotFoundError, json.JSONDecodeError):
            self.current_language = 'ru'
            self.current_theme = 'light'
            self.text_size = 12
            self.info_size = 9

    def save_settings(self):
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
        self.video_listbox = tk.Listbox(self.sidebar, width=40, height=20, yscrollcommand=self.scrollbar.set, exportselection=0)
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
        self.text_area = tk.Text(self.main_frame, height=0, wrap=tk.WORD, font=("Arial", self.text_size), undo=True)
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=5)
        self.text_area.bind('<KeyRelease>', self.save_text)
        self.settings_button = tk.Button(self.root, text="⚙", command=self.show_settings_menu)
        self.settings_button.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)
        self.increase_size_button = tk.Button(self.root, text="➕", command=self.increase_text_size)
        self.increase_size_button.place(relx=0.99, rely=0.0, anchor="ne", x=-35, y=5)
        self.decrease_size_button = tk.Button(self.root, text="➖", command=self.decrease_text_size)
        self.decrease_size_button.place(relx=0.99, rely=0.0, anchor="ne", x=-65, y=5)
        self.show_hint()
        self.create_context_menu()
        # Привязка горячих клавиш для Undo и Redo
        self.text_area.bind('<Control-z>', self.undo_text)
        self.text_area.bind('<Control-Shift-Z>', self.redo_text)

    def undo_text(self, event=None):
        try:
            self.text_area.edit_undo()
        except tk.TclError:
            pass  # Игнорируем ошибку, если Undo недоступно

    def redo_text(self, event=None):
        try:
            self.text_area.edit_redo()
        except tk.TclError:
            pass  # Игнорируем ошибку, если Redo недоступно

    def create_context_menu(self):
        lang = self.translations[self.current_language]
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label=lang["undo"], command=self.undo_text)
        self.context_menu.add_command(label=lang["redo"], command=self.redo_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=lang["copy"], command=self.copy_text)
        self.context_menu.add_command(label=lang["paste"], command=self.paste_text)
        self.context_menu.add_command(label=lang["cut"], command=self.cut_text)
        self.text_area.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_text(self):
        self.text_area.event_generate("<<Copy>>")

    def paste_text(self):
        self.text_area.event_generate("<<Paste>>")

    def cut_text(self):
        self.text_area.event_generate("<<Cut>>")

    def increase_text_size(self):
        self.text_size += 1
        self.info_size += 1
        self.update_text_sizes()
        self.save_settings()

    def decrease_text_size(self):
        if self.text_size > 10 and self.info_size > 1:
            self.text_size -= 1
            self.info_size -= 1
            self.update_text_sizes()
            self.save_settings()

    def update_text_sizes(self):
        self.text_area.config(font=("Arial", self.text_size))
        self.video_info_label.config(font=("Arial", self.info_size))

    def apply_theme(self):
        theme = self.themes[self.current_theme]
        self.root.config(bg=theme['background'])
        self.sidebar.config(bg=theme['background'], highlightbackground=theme['border'], highlightthickness=1)
        self.video_listbox.config(
            bg=theme['background'],
            fg=theme['text'],
            selectbackground=theme['select_bg'],
            selectforeground=theme['select_fg'],
            activestyle='none'  # Убираем пунктирную рамку при фокусе
        )
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
        self.create_context_menu()

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
            if self.player.is_image:
                info_text = lang["image_info"].format(
                    width=self.player.original_width,
                    height=self.player.original_height
                )
            else:
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
        menu = tk.Menu(self.root, tearoff=0)
        lang_menu = tk.Menu(menu, tearoff=0)
        for lang_code in self.translations.keys():
            lang_name = self.translations[lang_code].get('language_name', lang_code)
            lang_menu.add_command(label=lang_name, command=lambda lc=lang_code: self.set_language(lc))
        menu.add_cascade(label=self.translations[self.current_language]['language'], menu=lang_menu)
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
        self.current_language = lang_code
        self.update_localization()
        self.save_settings()

    def set_theme(self, theme):
        self.current_theme = theme
        self.apply_theme()
        self.save_settings()

    def on_drop(self, event):
        path = event.data
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]  # Убираем фигурные скобки, если они есть
        path = path.strip()  # Убираем ведущие и конечные пробелы
        if os.path.isdir(path):
            self.video_folder = os.path.normpath(path)  # Нормализуем путь к папке
            self.load_videos()
            if self.video_files:
                first_file = os.path.join(self.video_folder, self.video_files[0])
                try:
                    if VideoPlayer(first_file, self.video_canvas, self.root).is_image:
                        with open(first_file, 'rb') as f:
                            img_data = np.frombuffer(f.read(), np.uint8)
                        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                        width, height = img.shape[1], img.shape[0]
                    else:
                        cap = cv2.VideoCapture(first_file)
                        if not cap.isOpened():
                            raise ValueError(f"Не удалось открыть видео {first_file}")
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        cap.release()
                    window_width = width + 800 + 20
                    window_height = height + 400
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    max_width = int(screen_width * 0.90)
                    max_height = int(screen_height * 0.90)
                    window_width = min(window_width, max_width)
                    window_height = min(window_height, max_height)
                    current_y = self.root.winfo_y()
                    current_height = self.root.winfo_height()
                    current_bottom_margin = screen_height - (current_y + current_height)
                    if (current_bottom_margin / screen_height) < 0.25:
                        new_y = (screen_height - window_height) // 10
                    else:
                        new_y = current_y
                    current_x = self.root.winfo_x()
                    self.root.geometry(f"{window_width}x{window_height}+{current_x}+{new_y}")
                    self.root.update_idletasks()
                    self.root.after(100, self.select_first_file)
                except Exception as e:
                    print(f"Ошибка при обработке файла {first_file}: {e}")
            self.show_hint()
        else:
            print(self.translations[self.current_language]['drop_folder_message'])

    def select_first_file(self):
        self.video_listbox.selection_clear(0, tk.END)
        self.video_listbox.selection_set(0)
        self.video_listbox.activate(0)
        self.on_video_select(None)

    def load_videos(self):
        if self.video_folder:
            supported_formats = ('.mp4', '.mov', '.avi', '.jpg', '.png')
            self.video_files = [f for f in os.listdir(self.video_folder) if f.lower().endswith(supported_formats)]
            self.video_listbox.delete(0, tk.END)
            for video in self.video_files:
                self.video_listbox.insert(tk.END, video)

    def on_video_select(self, event):
        selection = self.video_listbox.curselection()
        if not selection:
            return
        file_name = self.video_listbox.get(selection[0])
        file_path = os.path.join(self.video_folder, file_name)
        file_path = os.path.normpath(file_path)  # Нормализуем путь к файлу
        if self.player:
            self.player.stop()
        try:
            self.player = VideoPlayer(file_path, self.video_canvas, self.root)
            self.player.play()
            self.update_video_info()
            self.show_hint()
            txt_path = os.path.join(self.video_folder, os.path.splitext(file_name)[0] + '.txt')
            txt_path = os.path.normpath(txt_path)  # Нормализуем путь к текстовому файлу
            self.load_text(txt_path)
        except Exception as e:
            print(f"Ошибка при загрузке файла {file_path}: {e}")

    def load_text(self, txt_path):
        self.current_txt_path = txt_path
        self.text_area.delete(1.0, tk.END)
        if os.path.exists(txt_path):
            try:
                with open(txt_path, 'r', encoding='utf-8') as f:
                    self.text_area.insert(tk.END, f.read())
            except Exception as e:
                print(f"Ошибка при загрузке текста {txt_path}: {e}")

    def save_text(self, event):
        if hasattr(self, 'current_txt_path'):
            text_content = self.text_area.get(1.0, tk.END).strip()
            try:
                with open(self.current_txt_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)
            except Exception as e:
                print(f"Ошибка при сохранении текста {self.current_txt_path}: {e}")

    def on_closing(self):
        if self.player:
            self.player.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VideoCaptionEditor(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    sys.exit(0)