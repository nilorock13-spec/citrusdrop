"""CitrusDrop: offline Windows file utility. Python 3.11+ / Tkinter."""
from __future__ import annotations
import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.webm', '.avi'}

def unique_path(folder: Path, stem: str, ext: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / (stem + ext)
    index = 2
    while dest.exists():
        dest = folder / f'{stem}_{index}{ext}'
        index += 1
    return dest

def ffmpeg_path() -> str:
    executable = shutil.which('ffmpeg')
    if not executable:
        raise RuntimeError('FFmpeg is missing. Install it and add ffmpeg to PATH, then restart the app.')
    return executable

def image_process(path: Path, output: Path, action: str, fmt: str, width: int, height: int, quality: int):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        if action == 'Resize':
            if width < 1 or height < 1:
                raise ValueError('Width and height must be positive.')
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
        elif action == 'Center crop':
            if width < 1 or height < 1 or width > image.width or height > image.height:
                raise ValueError(f'Crop size must be within {image.width} × {image.height} pixels.')
            left = (image.width - width) // 2
            top = (image.height - height) // 2
            image = image.crop((left, top, left + width, top + height))
        elif action == 'Rotate 90°':
            image = image.rotate(-90, expand=True)
        elif action not in ('Convert', 'Compress'):
            raise ValueError('Unsupported image operation.')
        if fmt == 'JPEG':
            if image.mode not in ('RGB', 'L'):
                background = Image.new('RGB', image.size, 'white')
                if 'A' in image.getbands():
                    background.paste(image, mask=image.getchannel('A'))
                else:
                    background.paste(image.convert('RGB'))
                image = background
            image.save(output, format='JPEG', quality=quality, optimize=True)
        elif fmt == 'PNG':
            image.save(output, format='PNG', optimize=True)
        elif fmt == 'WEBP':
            image.save(output, format='WEBP', quality=quality, method=5)
        else:
            raise ValueError('Unsupported image format.')

def pdf_process(paths: list[Path], folder: Path, action: str, degrees: int):
    outputs = []
    if action == 'Merge':
        writer = PdfWriter()
        for path in paths:
            writer.append(str(path))
        dest = unique_path(folder, 'merged', '.pdf')
        with dest.open('wb') as stream:
            writer.write(stream)
        writer.close()
        return [dest]
    for path in paths:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError(f'{path.name} is encrypted. Unlock it first.')
        if action == 'Rotate':
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page.rotate(degrees))
            dest = unique_path(folder, path.stem + '_rotated', '.pdf')
            with dest.open('wb') as stream:
                writer.write(stream)
            writer.close()
            outputs.append(dest)
        elif action == 'Split pages':
            for n, page in enumerate(reader.pages, start=1):
                writer = PdfWriter()
                writer.add_page(page)
                dest = unique_path(folder, f'{path.stem}_page_{n:03d}', '.pdf')
                with dest.open('wb') as stream:
                    writer.write(stream)
                writer.close()
                outputs.append(dest)
        else:
            raise ValueError('Unsupported PDF operation.')
    return outputs

def video_process(path: Path, dest: Path, action: str, start: float, duration: float, crf: int):
    cmd = [ffmpeg_path(), '-hide_banner', '-loglevel', 'error', '-nostdin', '-n']
    if action == 'Trim':
        if start < 0 or duration <= 0:
            raise ValueError('Start must be ≥ 0 and duration > 0.')
        cmd += ['-ss', str(start), '-i', str(path), '-t', str(duration)]
    else:
        cmd += ['-i', str(path)]
    cmd += ['-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf),
            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(dest)]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError(result.stderr[-1800:] or 'FFmpeg failed.')

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('CitrusDrop — Offline File Toolkit')
        self.geometry('850x680')
        self.minsize(690, 570)
        self.files: list[Path] = []
        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self.output = tk.StringVar(value=str(Path.home() / 'Documents' / 'CitrusDrop Output'))
        self.image_action = tk.StringVar(value='Convert')
        self.image_format = tk.StringVar(value='PNG')
        self.img_width = tk.StringVar(value='800')
        self.img_height = tk.StringVar(value='800')
        self.quality = tk.StringVar(value='80')
        self.pdf_action = tk.StringVar(value='Merge')
        self.degrees = tk.StringVar(value='90')
        self.video_action = tk.StringVar(value='Convert / Compress')
        self.start = tk.StringVar(value='0')
        self.duration = tk.StringVar(value='10')
        self.crf = tk.StringVar(value='25')
        self.build_ui()
        self.after(120, self.poll)

    def build_ui(self):
        ttk.Style().theme_use('clam')
        container = ttk.Frame(self, padding=16)
        container.pack(fill='both', expand=True)
        ttk.Label(container, text='🍊 CitrusDrop', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
        ttk.Label(container, text='Local-first file tools • Nothing is uploaded').pack(anchor='w', pady=(0, 12))
        buttons = ttk.Frame(container)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='Add files', command=self.add_files).pack(side='left', padx=(0, 7))
        ttk.Button(buttons, text='Remove selected', command=self.remove_selected).pack(side='left', padx=(0, 7))
        ttk.Button(buttons, text='Clear', command=self.clear_files).pack(side='left')
        self.listbox = tk.Listbox(container, height=9, selectmode='extended', font=('Segoe UI', 10))
        self.listbox.pack(fill='both', expand=True, pady=(9, 12))
        out = ttk.Frame(container)
        out.pack(fill='x', pady=(0, 12))
        ttk.Label(out, text='Output folder').pack(side='left', padx=(0, 8))
        ttk.Entry(out, textvariable=self.output).pack(side='left', fill='x', expand=True)
        ttk.Button(out, text='Browse', command=self.browse_output).pack(side='left', padx=(8, 0))
        self.tabs = ttk.Notebook(container)
        self.tabs.pack(fill='x')
        self.tab_image = ttk.Frame(self.tabs, padding=12)
        self.tab_pdf = ttk.Frame(self.tabs, padding=12)
        self.tab_video = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.tab_image, text='Images')
        self.tabs.add(self.tab_pdf, text='PDF')
        self.tabs.add(self.tab_video, text='Video')
        self.make_row(self.tab_image, 0, 'Action', self.image_action, ['Convert', 'Compress', 'Resize', 'Center crop', 'Rotate 90°'])
        self.make_row(self.tab_image, 1, 'Output format', self.image_format, ['PNG', 'JPEG', 'WEBP'])
        self.make_entry(self.tab_image, 2, 'Width (px)', self.img_width)
        self.make_entry(self.tab_image, 3, 'Height (px)', self.img_height)
        self.make_entry(self.tab_image, 4, 'Quality 1–100', self.quality)
        ttk.Label(self.tab_image, text='Resize preserves aspect ratio. Crop takes the center region.').grid(row=5, column=0, columnspan=2, sticky='w', pady=4)
        self.make_row(self.tab_pdf, 0, 'Action', self.pdf_action, ['Merge', 'Split pages', 'Rotate'])
        self.make_row(self.tab_pdf, 1, 'Rotation', self.degrees, ['90', '180', '270'])
        ttk.Label(self.tab_pdf, text='Merge uses file-list order; split exports every page separately.').grid(row=2, column=0, columnspan=2, sticky='w', pady=8)
        self.make_row(self.tab_video, 0, 'Action', self.video_action, ['Convert / Compress', 'Trim'])
        self.make_entry(self.tab_video, 1, 'Start (seconds)', self.start)
        self.make_entry(self.tab_video, 2, 'Duration (seconds)', self.duration)
        self.make_entry(self.tab_video, 3, 'CRF quality 18–35', self.crf)
        ttk.Label(self.tab_video, text='Requires FFmpeg on PATH. Outputs H.264/AAC MP4. Lower CRF = higher quality.').grid(row=4, column=0, columnspan=2, sticky='w', pady=8)
        bottom = ttk.Frame(container)
        bottom.pack(fill='x', pady=(14, 0))
        self.run_button = ttk.Button(bottom, text='Process selected tab', command=self.start_job)
        self.run_button.pack(side='left')
        self.status = ttk.Label(bottom, text='Ready')
        self.status.pack(side='left', padx=12)
        self.progress = ttk.Progressbar(container, mode='indeterminate')
        self.progress.pack(fill='x', pady=(8, 0))

    def make_row(self, parent, row, label, var, choices):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=(0, 14), pady=3)
        ttk.Combobox(parent, textvariable=var, values=choices, state='readonly', width=25).grid(row=row, column=1, sticky='w', pady=3)

    def make_entry(self, parent, row, label, var):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=(0, 14), pady=3)
        ttk.Entry(parent, textvariable=var, width=27).grid(row=row, column=1, sticky='w', pady=3)

    def add_files(self):
        for name in filedialog.askopenfilenames(title='Choose files'):
            path = Path(name)
            if path not in self.files:
                self.files.append(path)
                self.listbox.insert('end', str(path))

    def remove_selected(self):
        for index in reversed(self.listbox.curselection()):
            self.listbox.delete(index)
            del self.files[index]

    def clear_files(self):
        self.files.clear()
        self.listbox.delete(0, 'end')

    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output.set(folder)

    def start_job(self):
        if self.busy:
            return
        tab = self.tabs.index(self.tabs.select())
        selected = [self.files[i] for i in self.listbox.curselection()] or list(self.files)
        if not selected:
            messagebox.showwarning('No files', 'Add at least one file first.')
            return
        try:
            folder = Path(self.output.get()).expanduser().resolve()
            if tab == 0:
                action, fmt = self.image_action.get(), self.image_format.get()
                width, height, quality = int(self.img_width.get()), int(self.img_height.get()), int(self.quality.get())
                if not 1 <= quality <= 100:
                    raise ValueError('Quality must be 1–100.')
                args = (action, fmt, width, height, quality)
            elif tab == 1:
                args = (self.pdf_action.get(), int(self.degrees.get()))
            else:
                start, duration, crf = float(self.start.get()), float(self.duration.get()), int(self.crf.get())
                if not 18 <= crf <= 35:
                    raise ValueError('CRF must be between 18 and 35.')
                args = (self.video_action.get(), start, duration, crf)
        except ValueError as error:
            messagebox.showerror('Invalid settings', str(error))
            return
        self.busy = True
        self.run_button.configure(state='disabled')
        self.progress.start(12)
        self.status.configure(text='Processing…')
        threading.Thread(target=self.worker, args=(tab, selected, folder, args), daemon=True).start()

    def worker(self, tab, selected, folder, args):
        count = 0
        failures = []
        try:
            folder.mkdir(parents=True, exist_ok=True)
            valid_exts = [IMAGE_EXTS, {'.pdf'}, VIDEO_EXTS][tab]
            selected = [p for p in selected if p.suffix.lower() in valid_exts]
            if not selected:
                raise ValueError('No supported files for the selected tab.')
            if tab == 1 and args[0] == 'Merge':
                pdf_process(selected, folder, *args)
                count = 1
            else:
                for path in selected:
                    try:
                        if tab == 0:
                            action, fmt, width, height, quality = args
                            ext = {'PNG': '.png', 'JPEG': '.jpg', 'WEBP': '.webp'}[fmt]
                            dest = unique_path(folder, path.stem + '_' + action.lower().replace(' ', '_'), ext)
                            image_process(path, dest, *args)
                        elif tab == 1:
                            results = pdf_process([path], folder, *args)
                            count += len(results) - 1
                        else:
                            action, start, duration, crf = args
                            dest = unique_path(folder, path.stem + ('_trimmed' if action == 'Trim' else '_converted'), '.mp4')
                            video_process(path, dest, *args)
                        count += 1
                    except Exception as error:
                        failures.append(f'{path.name}: {error}')
            self.events.put(('done', count, failures, str(folder)))
        except Exception as error:
            self.events.put(('error', str(error)))

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                self.busy = False
                self.progress.stop()
                self.run_button.configure(state='normal')
                if event[0] == 'done':
                    _, count, failures, folder = event
                    self.status.configure(text=f'{count} output file(s) created')
                    details = f'Created {count} file(s) in:\n{folder}'
                    if failures:
                        details += '\n\nFailures:\n' + '\n'.join(failures[:10])
                    (messagebox.showwarning if failures else messagebox.showinfo)('Processing finished', details)
                else:
                    self.status.configure(text='Failed')
                    messagebox.showerror('Processing failed', event[1])
        except queue.Empty:
            pass
        self.after(120, self.poll)

if __name__ == '__main__':
    App().mainloop()
