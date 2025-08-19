import wget
import os

models_folder = "models"

# Dosya yolları
yolov4_cfg_url = "https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4.cfg"
yolov4_weights_url = "https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4.weights"
coco_names_url = "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"

# Klasör yoksa oluştur
if not os.path.exists(models_folder):
    os.makedirs(models_folder)
    print(f"'{models_folder}' klasörü oluşturuldu.")

# Dosyaları indirme
print("YOLOv4.cfg dosyası indiriliyor...")
wget.download(yolov4_cfg_url, out=os.path.join(models_folder, "yolov4.cfg"))
print("\nYOLOv4.weights dosyası indiriliyor (bu biraz zaman alabilir)...")
wget.download(yolov4_weights_url, out=os.path.join(models_folder, "yolov4.weights"))
print("\nCoco.names dosyası indiriliyor...")
wget.download(coco_names_url, out=os.path.join(models_folder, "coco.names"))

print("\nTüm dosyalar başarıyla indirildi!")