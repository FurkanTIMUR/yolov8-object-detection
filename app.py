import cv2
import numpy as np
import datetime
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import threading
from PIL import Image, ImageTk
import tkinter.ttk as ttk
from ttkthemes import ThemedTk
from ultralytics import YOLO

class App:
    
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        self.window.geometry("1200x700")
        self.running = False
        self.frame_width = 1200
        self.frame_height = 700

        # Arka planı kaplayacak ana video/görsel etiketi
        self.video_label = tk.Label(self.window)
        self.video_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER) # Pencerenin ortasına yerleştir
        
        # En üstte yer alacak buton barı
        self.top_bar_frame = tk.Frame(self.window, bg="#333", bd=1)
        self.top_bar_frame.pack(side=tk.TOP, fill=tk.X)

        # Butonlar
        tk.Label(self.top_bar_frame, text="Kamera Seç:", bg="#333", fg="white").pack(side=tk.LEFT, padx=5)
        self.camera_combo = ttk.Combobox(self.top_bar_frame, state="readonly")
        self.available_cameras = self.find_available_cameras()
        if self.available_cameras:
            self.camera_combo["values"] = self.available_cameras
            self.camera_combo.current(0)
            self.camera_combo.pack(side=tk.LEFT, padx=5)
        
        self.start_camera_button = tk.Button(self.top_bar_frame, text="Kamera Başlat", command=self.start_camera)
        self.start_camera_button.pack(side=tk.LEFT, padx=5)
        self.stop_camera_button = tk.Button(self.top_bar_frame, text="Kamerayı Durdur", command=self.stop_camera, state=tk.DISABLED)
        self.stop_camera_button.pack(side=tk.LEFT, padx=5)
        
        self.open_file_button = tk.Button(self.top_bar_frame, text="Görsel / Video Aç", command=self.process_file)
        self.open_file_button.pack(side=tk.LEFT, padx=5)

        self.save_button = tk.Button(self.top_bar_frame, text="Görüntüyü Kaydet", command=self.save_current_frame, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        self.record_button = tk.Button(self.top_bar_frame, text="Kaydı Başlat", command=self.toggle_recording, state=tk.DISABLED)
        self.record_button.pack(side=tk.LEFT, padx=5)
        
        self.settings_button = tk.Button(self.top_bar_frame, text="Ayarlar", command=self.open_settings_window)
        self.settings_button.pack(side=tk.LEFT, padx=5)
        
       # Sağ üstte, gizli olacak bilgi paneli
        self.info_panel = tk.Frame(self.window, bg="#333", bd=1)
        self.info_panel.place_forget() # Başlangıçta gizli
        
        self.object_label = tk.Label(self.info_panel, text="Nesne: N/A", bg="#333", fg="white")
        self.object_label.pack(padx=5, pady=2)
        
       # En altta durum çubuğu
        self.status_bar = tk.Label(self.window, text="Hazır", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.progress_bar = ttk.Progressbar(self.window, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.camera = None
        
        self.is_recording = False
        self.video_writer = None
        self.models_loaded = False 
        
        #YOLOv8 modelini yükler...
        try:
            self.yolo_model = YOLO('yolov8n.pt')
            self.models_loaded = True
            self.update_status("Yapay zeka modelleri başarıyla yüklendi.")
        except Exception as e:
            messagebox.showerror("Model Yükleme Hatası", f"Beklenmedik bir hata oluştu: {e}")
            self.update_status("Hata: Model dosyaları yüklenemedi.")

        
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.mainloop()
    
    def find_available_cameras(self):
        available_cameras = []
        for i in range(10): 
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(f"Kamera {i}")
                cap.release()
        return available_cameras

    def update_alpha(self, value):
        self.alpha = int(value) / 100.0
    
    def toggle_info_panel(self, visible):
        if visible:
            self.info_panel.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-10, y=10)
        else:
            self.info_panel.place_forget()

    def start_camera(self):
        if not self.running:
            #Kamerayı başlatmadan önce varsayılan pencere boyutlarını ayarlar
            self.window.geometry(f"{self.frame_width}x{self.frame_height}")

            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                messagebox.showerror("Hata", "Kameraya erişilemiyor. Lütfen kameranızın bağlı olduğundan emin olun.")
                return
            
            self.running = True

            # Kamera başlatıldığında buton durumlarını güncelle
            self.start_camera_button.config(state=tk.DISABLED)
            self.open_file_button.config(state=tk.DISABLED)
            self.stop_camera_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            self.record_button.config(state=tk.NORMAL)
            self.toggle_info_panel(True) # Bilgi panelini açmak için bu satır gereklidir.
            self.thread = threading.Thread(target=self.video_stream)
            self.thread.daemon = True
            self.thread.start()
            self.update_status("Kamera başlatıldı...")
         
    def update_status(self, message):
        self.status_bar.config(text=message)

    def stop_camera(self):
        # Kamerayı durdurma mantığı
        if self.running:
            self.running = False
            
            if self.camera:
                self.camera.release()
                self.camera = None
            
            # Görüntüyü temizle
            self.video_label.config(image=None)
            self.video_label.imgtk = None
            
            # Buton durumlarını eski haline getir
            self.start_camera_button.config(state=tk.NORMAL)
            self.open_file_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.DISABLED)
            self.record_button.config(state=tk.DISABLED)
            self.stop_camera_button.config(state=tk.DISABLED)
            
            self.update_status("Hazır")

            if self.progress_bar.winfo_exists():
                self.progress_bar.pack_forget()
            
    def on_closing(self):
        self.stop_camera()
        self.window.destroy()

    def update_gui_thread_safe(self, img_tk, new_width, new_height):
        # Bu metot sadece ana iş parçacığında çalışır ve GUI'ı günceller.
        if self.running:
            self.video_label.config(image=img_tk)
            self.video_label.imgtk = img_tk
            self.video_label.config(width=new_width, height=new_height)

    def update_frame(self, image):

        if not self.running:
            return
        

        # OpenCV'den gelen BGR formatını PIL'in kullanabileceği RGB'ye çevirir.
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Görselin boyutları
        original_width, original_height = pil_image.size
        
        # Ekran boyutları
        screen_width = self.window.winfo_width()
        screen_height = self.window.winfo_height()

        if screen_width ==0 or screen_height == 0:
            screen_width = self.frame_width
            screen_height = self.frame_height
        
        # Görselin en-boy oranına göre tuvalin yeni boyutlarını hesapla
        ratio = min(screen_width / original_width, screen_height / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        img_tk = ImageTk.PhotoImage(image=resized_image)
        
        # GUI güncellemesini güvenli bir şekilde ana iş parçacığına gönderir
        self.window.after(0, self.update_gui_thread_safe, img_tk, new_width, new_height)

    def run_all_models(self, frame):
        if frame is None:
            return None
        
        if not self.models_loaded:
            return frame
        
        # YOLOv8 ile algılama yapar.
        results = self.yolo_model(frame)
        
        detected_objects = []
        for r in results:
            for box in r.boxes:
                label = r.names[int(box.cls[0])]
                conf = float(box.conf[0])
                if conf > 0.5:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    detected_objects.append(label)

        self.object_label.config(text=f"Nesne: {', '.join(set(detected_objects))}" if detected_objects else "Nesne: N/A")
        

        now = datetime.datetime.now()
        datetime_text = now.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, datetime_text, (frame.shape[1] - 300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)
        return frame
      
    def run_all_models_on_image(self, frame):
        if frame is None:
            print("Görsel Yüklenemedi")
            return
        
        img = self.run_all_models(frame)
        self.update_frame(img)
    
    def run_all_models_on_video(self, file_path):
        self.camera = cv2.VideoCapture(file_path)
        if not self.camera.isOpened():
            messagebox.showerror("Hata", "Video dosyası açılamadı.")
            self.stop_camera()
            return

        self.running = True
        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                break
            
            processed_frame = self.run_all_models(frame)
            self.update_frame(processed_frame)
            
        self.camera.release()
        self.stop_camera()       
       
    def process_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.stop_camera()
            # Butonları geçici olarak devre dışı bırak
            self.start_camera_button.config(state=tk.DISABLED)
            self.open_file_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.NORMAL)
            self.stop_camera_button.config(state=tk.NORMAL)
            self.running = True

            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                self.update_status("Görsel işleniyor...")
                frame = cv2.imread(file_path)
                if frame is not None:
                   #Görselin orjinal boyutlarını alıp pencereyi ona göre boyutlandrırır..
                   original_height, original_width, _ = frame.shape
                   self.frame_width =original_width
                   self.frame_height =original_height
                   self.window.geometry(f"{self.frame_width}x{self.frame_height}")
                   
                   self.run_all_models_on_image(frame) 
                    
                else:
                    messagebox.showerror("Hata", "Dosya okunamadı veya geçerli bir görsel değil.")
                    self.update_status("Hata: Dosya okunamadı.")
            
            elif file_path.lower().endswith(('.mp4', '.avi', '.mov')):
                self.update_status("Video işleniyor...")
                # Video dosyasını ayrı bir iş parçacığında çalıştır
                self.thread = threading.Thread(target=self.process_video_file, args=(file_path,))
                self.thread.daemon = True
                self.thread.start()
            
            else:
                messagebox.showwarning("Uyarı", "Desteklenmeyen dosya formatı.")
                self.update_status("Hata: Desteklenmeyen dosya formatı.")
    
    def process_video_file(self, file_path):
        cap = cv2.VideoCapture(file_path) # Önce cap nesnesini oluştur
        if not cap.isOpened():
            messagebox.showerror("Hata", "Video dosyası açılamadı.")
            self.stop_camera()
            return

        # Video dosyasının boyutlarını al
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_width = original_width
        self.frame_height = original_height
        self.window.geometry(f"{self.frame_width}x{self.frame_height}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.progress_bar.pack(pady=10)
        self.progress_bar["maximum"] = total_frames

        self._process_stream(cap)
        
        cap.release()
        self.progress_bar.pack_forget()

    def _process_stream(self, cap):
        # Ortak video işleme döngüsü
        while cap.isOpened() and self.running:
            ret, frame = cap.read()
            if not ret:
                break
            
            processed_frame = self.run_all_models(frame)

            if self.is_recording and self.video_writer:
                self.video_writer.write(processed_frame)
            self.update_frame(processed_frame)
            
    def video_stream(self):

        self.running = True
        self._process_stream(self.camera)
        self.camera.release()
            
    def save_current_frame(self):
        if self.video_label.imgtk:
            # Tkinter PhotoImage'dan PIL Image'a dönüştür
            pil_image = ImageTk.getimage(self.video_label.imgtk)

            # Kullanıcıdan dosya adı ve konumu al
            file_path = filedialog.asksaveasfilename(defaultextension=".png", 
                                                    filetypes=[("PNG files", "*.png"), 
                                                                ("JPEG files", "*.jpg"),
                                                                ("All files", "*.*")])
            if file_path:
                try:
                    # PIL Image'dan OpenCV formatına dönüştür
                    opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                    
                    # Görüntüyü kaydet
                    cv2.imwrite(file_path, opencv_image)
                    self.update_status(f"Görüntü kaydedildi: {file_path}")
                except Exception as e:
                    self.update_status(f"Hata: Görüntü kaydedilirken bir sorun oluştu. {e}")
        else:
            self.update_status("Hata: Kaydedilecek bir görüntü yok.")

    def open_settings_window(self):
        settings_window = tk.Toplevel(self.window)
        settings_window.title("Ayarlar")
        
        # Genişlik ayarı için giriş alanı
        tk.Label(settings_window, text="Pencere Genişliği:").pack(padx=10, pady=5)
        width_entry = tk.Entry(settings_window)
        width_entry.insert(0, str(self.frame_width)) # Mevcut değeri gösterir
        width_entry.pack(padx=10, pady=5)
        
        # Yükseklik ayarı için giriş alanı
        tk.Label(settings_window, text="Pencere Yüksekliği:").pack(padx=10, pady=5)
        height_entry = tk.Entry(settings_window)
        height_entry.insert(0, str(self.frame_height)) # Mevcut değeri gösterir
        height_entry.pack(padx=10, pady=5)
        
        # Ayarları Uygula butonu
        apply_button = tk.Button(settings_window, text="Uygula", command=lambda: self.apply_settings(settings_window, width_entry, height_entry))
        apply_button.pack(pady=10)

    def apply_settings(self, window, width_entry, height_entry):
        try:
            new_width = int(width_entry.get())
            new_height = int(height_entry.get())
            
            # Değerlerin geçerli olup olmadığını kontrol eder
            if new_width > 0 and new_height > 0:
                self.frame_width = new_width
                self.frame_height = new_height
                self.window.geometry(f"{self.frame_width}x{self.frame_height}")
                self.window.title(f"{self.window.title().split(' - ')[0]} - {self.frame_width}x{self.frame_height}")
                self.update_status(f"Pencere boyutu {new_width}x{new_height} olarak güncellendi.")
                window.destroy() # Ayarlar penceresini kapatır
            else:
                self.update_status("Hata: Genişlik ve yükseklik pozitif tam sayı olmalıdır.")
        except ValueError:
            self.update_status("Hata: Lütfen geçerli tam sayılar girin.")

    def toggle_recording(self):
        if not self.is_recording:
            # Kaydı başlat
            file_path = filedialog.asksaveasfilename(defaultextension=".mp4", 
                                                    filetypes=[("MP4 files", "*.mp4")])
            if file_path:
                self.is_recording = True
                self.record_button.config(text="Kaydı Durdur", fg="red")
                self.update_status("Video kaydı başlatıldı...")
                
                # Video writer nesnesini oluştur
                codec = cv2.VideoWriter_fourcc(*'mp4v') # Codec tanımlaması
                fps = 20.0 # Frame hızı
                out_size = (self.frame_width, self.frame_height) # Çıkış boyutu
                
                self.video_writer = cv2.VideoWriter(file_path, codec, fps, out_size)
            else:
                self.update_status("Kayıt işlemi iptal edildi.")
        else:
            # Kaydı durdur
            self.is_recording = False
            self.record_button.config(text="Kaydı Başlat", fg="black")
            
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
                self.update_status("Video kaydı durduruldu.")

if __name__ == "__main__":
    #app = App(tk.Tk(), "Yapay Zeka Destekli Görüntü Analizi")

    window = ThemedTk(theme="arc") # "plastik", "equilux" veya "arc" gibi temaları deneyebilirsiniz
    app = App(window, "Yapay Zeka Destekli Görüntü Analizi")