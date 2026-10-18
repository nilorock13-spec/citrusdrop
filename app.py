import os, subprocess, shutil, tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk, ImageOps
from pypdf import PdfReader, PdfWriter
from tkinterdnd2 import TkinterDnD, DND_FILES

IMAGE_EXT={'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff'}
VIDEO_EXT={'.mp4','.mov','.mkv','.avi','.webm'}
BG='#10151e'; PANEL='#1d2633'; FG='#f3f6fa'; MUTED='#a8b6c7'; ACCENT='#ffad53'

class App:
    def __init__(self):
        self.root=TkinterDnD.Tk(); self.root.title('CitrusDrop — Drop. Edit. Done.'); self.root.geometry('1040x750'); self.root.minsize(740,560); self.root.configure(bg=BG)
        self.path=None; self.image=None; self.preview=None; self.scale=1; self.offset=(0,0); self.start=None; self.selection=None; self.rect=None
        tk.Label(self.root,text='●  CitrusDrop',bg=BG,fg=ACCENT,font=('Segoe UI',24,'bold')).pack(anchor='w',padx=30,pady=(22,0))
        tk.Label(self.root,text='Drop a photo, PDF or video. Pick a tool. Save.',bg=BG,fg=MUTED,font=('Segoe UI',11)).pack(anchor='w',padx=32,pady=(0,15))
        top=tk.Frame(self.root,bg=PANEL,highlightbackground='#3c4b5e',highlightthickness=1); top.pack(fill='x',padx=30,pady=6)
        self.drop=tk.Label(top,text='↓   Drag files here   •   or click to browse',bg=PANEL,fg=FG,font=('Segoe UI',14),height=3,cursor='hand2'); self.drop.pack(fill='x'); self.drop.bind('<Button-1>',lambda e:self.browse())
        for w in (self.root,top,self.drop): w.drop_target_register(DND_FILES); w.dnd_bind('<<Drop>>',self.dropped)
        self.file_label=tk.Label(self.root,text='No file selected',bg=BG,fg=MUTED,font=('Segoe UI',10)); self.file_label.pack(anchor='w',padx=32,pady=(12,6))
        self.toolbar=tk.Frame(self.root,bg=BG); self.toolbar.pack(fill='x',padx=28,pady=(0,9))
        self.buttons=[]
        for title,fn in [('Crop photo',self.crop_mode),('Resize',self.resize),('Convert',self.convert),('Compress',self.compress),('Rotate ↻',self.rotate),('PDF tools',self.pdf_tools),('Trim video',self.trim_video)]:
            b=tk.Button(self.toolbar,text=title,command=fn,bg=PANEL,fg=FG,activebackground='#35445a',activeforeground=FG,relief='flat',font=('Segoe UI',10),padx=11,pady=9,cursor='hand2'); b.pack(side='left',padx=3); self.buttons.append(b)
        self.canvas=tk.Canvas(self.root,bg='#161e29',highlightthickness=0,cursor='crosshair'); self.canvas.pack(fill='both',expand=True,padx=30,pady=(0,8)); self.canvas.bind('<Configure>',lambda e:self.render()); self.canvas.bind('<ButtonPress-1>',self.mouse_down); self.canvas.bind('<B1-Motion>',self.mouse_drag); self.canvas.bind('<ButtonRelease-1>',self.mouse_up)
        bottom=tk.Frame(self.root,bg=BG); bottom.pack(fill='x',padx=30,pady=(0,20))
        self.hint=tk.Label(bottom,text='Drop an image to preview it here.',bg=BG,fg=MUTED,font=('Segoe UI',10)); self.hint.pack(side='left')
        tk.Button(bottom,text='Crop & Save',command=self.save_crop,bg=ACCENT,fg='#111111',relief='flat',font=('Segoe UI',11,'bold'),padx=18,pady=10).pack(side='right')
        self.crop_active=True; self.render()
    def dropped(self,event):
        paths=self.root.tk.splitlist(event.data)
        if paths:self.open_file(paths[0])
    def browse(self):
        p=filedialog.askopenfilename(filetypes=[('Supported files','*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.pdf *.mp4 *.mov *.mkv *.avi *.webm'),('All files','*.*')]);
        if p:self.open_file(p)
    def open_file(self,p):
        self.path=Path(p); self.file_label.config(text=self.path.name); self.selection=None
        try:
            self.image=ImageOps.exif_transpose(Image.open(p)).copy() if self.path.suffix.lower() in IMAGE_EXT else None
        except Exception as e:self.image=None;messagebox.showerror('Cannot open image',str(e))
        self.hint.config(text='Drag a rectangle over the photo, then click Crop & Save.' if self.image else 'Choose a PDF or video tool above.'); self.render()
    def render(self):
        if not hasattr(self,'canvas'):return
        c=self.canvas;c.delete('all'); w=max(100,c.winfo_width());h=max(100,c.winfo_height())
        if self.image:
            iw,ih=self.image.size; self.scale=min((w-30)/iw,(h-30)/ih,1); pw=max(1,int(iw*self.scale));ph=max(1,int(ih*self.scale));self.offset=((w-pw)//2,(h-ph)//2)
            display=self.image.convert('RGB').resize((pw,ph),Image.Resampling.LANCZOS);self.preview=ImageTk.PhotoImage(display);c.create_image(*self.offset,image=self.preview,anchor='nw')
            if self.selection:self.draw_selection()
        else:
            c.create_text(w/2,h/2,text='Your preview appears here\n\nDrag a photo into the window to begin',fill=MUTED,font=('Segoe UI',17),justify='center')
    def coords(self,x,y):
        if not self.image:return (0,0)
        ox,oy=self.offset; iw,ih=self.image.size
        return (max(0,min(iw,round((x-ox)/self.scale))),max(0,min(ih,round((y-oy)/self.scale))))
    def mouse_down(self,e):
        if self.image and self.crop_active:self.start=self.coords(e.x,e.y);self.selection=None
    def mouse_drag(self,e):
        if self.start:self.selection=(*self.start,*self.coords(e.x,e.y));self.draw_selection()
    def mouse_up(self,e):
        if self.start:self.selection=(*self.start,*self.coords(e.x,e.y));self.start=None;self.draw_selection()
    def draw_selection(self):
        c=self.canvas;c.delete('cropbox')
        if not self.selection:return
        x1,y1,x2,y2=self.selection;ox,oy=self.offset
        c.create_rectangle(ox+x1*self.scale,oy+y1*self.scale,ox+x2*self.scale,oy+y2*self.scale,outline=ACCENT,width=3,dash=(7,3),tags='cropbox')
    def image_required(self):
        if not self.image:messagebox.showinfo('Choose a photo','Drop or open a photo first.');return False
        return True
    def crop_mode(self):
        if self.image_required():self.crop_active=True;self.hint.config(text='Drag across the photo to select the area to keep.')
    def save_image(self,img,suffix='_edited',fmt=None,quality=90):
        if not self.path:return
        ext=('.'+fmt.lower().replace('jpeg','jpg')) if fmt else self.path.suffix.lower()
        if ext not in IMAGE_EXT:ext='.png'
        p=filedialog.asksaveasfilename(defaultextension=ext,initialfile=self.path.stem+suffix+ext,filetypes=[('Image',f'*{ext}'),('All files','*.*')]);
        if not p:return
        try:
            output=img.convert('RGB') if Path(p).suffix.lower() in ('.jpg','.jpeg') else img
            output.save(p,quality=quality,optimize=True);self.hint.config(text='Saved: '+p);messagebox.showinfo('Saved','Saved successfully!')
        except Exception as e:messagebox.showerror('Save failed',str(e))
    def save_crop(self):
        if not self.image_required():return
        if not self.selection:messagebox.showinfo('Select an area','Click and drag over the photo to select what you want to keep.');return
        x1,y1,x2,y2=self.selection;box=(min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2))
        if box[2]-box[0]<2 or box[3]-box[1]<2:messagebox.showwarning('Selection too small','Please select a larger area.');return
        self.save_image(self.image.crop(box),'_cropped')
    def ask_values(self,title,fields,defaults):
        dlg=tk.Toplevel(self.root);dlg.title(title);dlg.configure(bg=BG);dlg.resizable(False,False);dlg.transient(self.root);dlg.grab_set();values=[];entries=[]
        for i,(label,default) in enumerate(zip(fields,defaults)):
            tk.Label(dlg,text=label,bg=BG,fg=FG).grid(row=i,column=0,padx=16,pady=9,sticky='w');e=tk.Entry(dlg,width=25);e.insert(0,str(default));e.grid(row=i,column=1,padx=16,pady=9);entries.append(e)
        def done():values.extend(e.get() for e in entries);dlg.destroy()
        tk.Button(dlg,text='Continue',command=done,bg=ACCENT,fg='black').grid(row=len(fields),columnspan=2,pady=14);self.root.wait_window(dlg);return values or None
    def resize(self):
        if not self.image_required():return
        vals=self.ask_values('Resize photo',['Width (pixels)','Height (pixels)'],self.image.size)
        if vals:
            try:
                w,h=map(int,vals);assert 0<w<=20000 and 0<h<=20000;self.save_image(self.image.resize((w,h),Image.Resampling.LANCZOS),'_resized')
            except (ValueError,AssertionError):messagebox.showerror('Invalid dimensions','Enter positive dimensions up to 20,000 pixels.')
    def convert(self):
        if not self.image_required():return
        vals=self.ask_values('Convert photo',['Format: JPG, PNG or WEBP'],['PNG'])
        if vals:
            fmt=vals[0].strip().upper().replace('JPG','JPEG')
            if fmt not in ('JPEG','PNG','WEBP'):messagebox.showerror('Format','Choose JPG, PNG or WEBP.');return
            self.save_image(self.image,'_converted',fmt)
    def compress(self):
        if not self.image_required():return
        vals=self.ask_values('Compress photo',['Quality (1–95, lower = smaller)'],[65])
        if vals:
            try:
                q=int(vals[0]);assert 1<=q<=95;self.save_image(self.image.convert('RGB'),'_compressed','JPEG',q)
            except (ValueError,AssertionError):messagebox.showerror('Quality','Enter a number between 1 and 95.')
    def rotate(self):
        if self.image_required():self.image=self.image.rotate(-90,expand=True);self.selection=None;self.render();self.hint.config(text='Rotated preview. Use Convert to save it.')
    def pdf_tools(self):
        vals=self.ask_values('PDF tools',['Action: merge, split, rotate'],['merge'])
        if not vals:return
        action=vals[0].strip().lower()
        try:
            if action=='merge':
                paths=filedialog.askopenfilenames(filetypes=[('PDF','*.pdf')]);
                if len(paths)<2:return
                writer=PdfWriter()
                for p in paths:writer.append(p)
            else:
                p=str(self.path) if self.path and self.path.suffix.lower()=='.pdf' else filedialog.askopenfilename(filetypes=[('PDF','*.pdf')]);
                if not p:return
                reader=PdfReader(p);writer=PdfWriter()
                if action=='split':
                    n=self.ask_values('Extract pages',['Page range, e.g. 1-3'],['1-1']);
                    if not n:return
                    a,b=map(int,n[0].split('-'))
                    if a<1 or b>len(reader.pages) or a>b:raise ValueError('Invalid page range')
                    for i in range(a-1,b):writer.add_page(reader.pages[i])
                elif action=='rotate':
                    for page in reader.pages:writer.add_page(page.rotate(90))
                else:messagebox.showinfo('PDF tools','Choose merge, split or rotate.');return
            out=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')],initialfile='CitrusDrop_output.pdf')
            if out:
                with open(out,'wb') as f:writer.write(f)
                messagebox.showinfo('Saved','PDF saved successfully.')
        except Exception as e:messagebox.showerror('PDF error',str(e))
    def trim_video(self):
        if not self.path or self.path.suffix.lower() not in VIDEO_EXT:messagebox.showinfo('Choose video','Drop a video file first.');return
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg:messagebox.showinfo('FFmpeg required','Install FFmpeg and add it to PATH to enable video trimming.');return
        vals=self.ask_values('Trim video',['Start time (seconds)','Duration (seconds)'],[0,10]);
        if not vals:return
        try:
            start=float(vals[0]);duration=float(vals[1]);assert start>=0 and duration>0
            out=filedialog.asksaveasfilename(defaultextension='.mp4',initialfile=self.path.stem+'_trimmed.mp4',filetypes=[('MP4','*.mp4')]);
            if out:
                subprocess.run([ffmpeg,'-y','-ss',str(start),'-i',str(self.path),'-t',str(duration),'-c:v','libx264','-crf','23','-c:a','aac',out],check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));messagebox.showinfo('Saved','Video saved successfully.')
        except (ValueError,AssertionError):messagebox.showerror('Invalid time','Enter a valid start time and duration.')
        except subprocess.CalledProcessError:messagebox.showerror('FFmpeg error','Could not process video. Check that the file is supported.')

if __name__=='__main__':
    App().root.mainloop()
