from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("ROBOFLOW_API_KEY")

from google.colab import drive
drive.mount('/content/drive')

!pip install -q roboflow ultralytics

import os, random, shutil, glob
from pathlib import Path
from roboflow import Roboflow
from ultralytics import YOLO

rf = Roboflow(api_key=API_KEY)

datasets = {
    "fire":   rf.workspace("guided-new").project("fire-fkf66-ppdkq").version(1).download("yolov8"),
    "cables": rf.workspace("guided-new").project("cables-l0moa-ozjm9").version(1).download("yolov8"),
    "knife":  rf.workspace("guided-new").project("knife-04h7h-iy6db").version(1).download("yolov8"),
    "tool":   rf.workspace("guided-new").project("hammer-screwdriver-detection-pgatx").version(1).download("yolov8")
}

mapping = {
    "cables--1": 0,                  
    "fire-1": 1,                     
    "knife-1": 2,                    
    "hammer-screwdriver-detection-1": 3
}

def relabel_dataset(folder, new_id):
    label_files = glob.glob(f"/content/{folder}/**/labels/*.txt", recursive=True)
    count = 0
    for file in label_files:
        lines = open(file).read().strip().splitlines()
        if not lines:
            continue
        with open(file, "w") as f:
            for line in lines:
                parts = line.split()
                parts[0] = str(new_id)
                f.write(" ".join(parts) + "\n")
                count += 1
    print(f"Relabeled {count} boxes in {folder} → class {new_id}")

for folder, cid in mapping.items():
    if os.path.exists(f"/content/{folder}"):
        relabel_dataset(folder, cid)

ROOT = "/content/drive/MyDrive/guidedvision_finalANJADPLEASE"
dataset_dir = f"{ROOT}/dataset"
for s in ["train","valid","test"]:
    os.makedirs(f"{dataset_dir}/{s}/images", exist_ok=True)
    os.makedirs(f"{dataset_dir}/{s}/labels", exist_ok=True)

def merge_split(src_root, split, dst_root, max_images=None):
    img_src = Path(src_root)/split/"images"
    lbl_src = Path(src_root)/split/"labels"
    if not img_src.exists():
        return
    imgs = list(img_src.glob("*"))
    if max_images:
        imgs = random.sample(imgs, min(max_images, len(imgs)))
    for img in imgs:
        lbl = lbl_src / (img.stem + ".txt")
        new_name = f"{Path(src_root).stem}_{img.name}"
        shutil.copy2(img, f"{dst_root}/{split}/images/{new_name}")
        if lbl.exists():
            shutil.copy2(lbl, f"{dst_root}/{split}/labels/{Path(src_root).stem}_{lbl.name}")

for name, ds in datasets.items():
    path = ds.location
    merge_split(path, "train", dataset_dir, max_images=1000)
    merge_split(path, "valid", dataset_dir, max_images=200)
    merge_split(path, "test", dataset_dir)

yaml_path = f"{dataset_dir}/data.yaml"
with open(yaml_path, "w") as f:
    f.write(f"""
train: {dataset_dir}/train/images
val: {dataset_dir}/valid/images
test: {dataset_dir}/test/images

nc: 4
names: ['cable', 'fire', 'knife', 'tool']
""")

model = YOLO('yolov8s.pt')
model.train(
    data=yaml_path,
    epochs=60,
    imgsz=640,
    batch=16,
    project=f"{ROOT}/runs/train",
    name="guidedvision_multiclass_fixed"
)

results = model.val(data=yaml_path, split='test')
print(results)
