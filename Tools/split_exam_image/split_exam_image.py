import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import shutil  # 新增导入

def split_image_to_a4(input_image_path, output_dir):
    # 读取图片，支持非 ASCII 路径
    with open(input_image_path, "rb") as f:
        file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"无法读取图片：{input_image_path}")

    # 获取图片尺寸
    height, width, _ = image.shape

    # 判断图片是竖向还是横向
    if height >= width:
        # 竖向图片，按高度中间分割
        mid_point = height // 2
        top_half = image[:mid_point, :]
        bottom_half = image[mid_point:, :]
    else:
        # 横向图片，按宽度中间分割
        mid_point = width // 2
        top_half = image[:, :mid_point]
        bottom_half = image[:, mid_point:]

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 获取输入文件名（不含扩展名）
    base_name = os.path.splitext(os.path.basename(input_image_path))[0]

    # 保存分割后的图片到临时路径
    temp_top_image_path = os.path.join(output_dir, "temp_top_half.jpg")
    temp_bottom_image_path = os.path.join(output_dir, "temp_bottom_half.jpg")
    cv2.imwrite(temp_top_image_path, top_half)
    cv2.imwrite(temp_bottom_image_path, bottom_half)

    # 重命名为目标路径，支持中文文件名
    top_image_path = os.path.join(output_dir, f"{base_name}_top_half.jpg")
    bottom_image_path = os.path.join(output_dir, f"{base_name}_bottom_half.jpg")
    shutil.move(temp_top_image_path, top_image_path)
    shutil.move(temp_bottom_image_path, bottom_image_path)

    print(f"图片已保存：\n{top_image_path}\n{bottom_image_path}")

def split_images_to_a4(input_image_paths, output_dir):
    for input_image_path in input_image_paths:
        try:
            split_image_to_a4(input_image_path, output_dir)
        except Exception as e:
            print(f"处理图片 {input_image_path} 时出错：{e}")

def select_images():
    # 打开文件选择对话框，支持多选
    file_paths = filedialog.askopenfilenames(
        title="选择试卷图片",
        filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp")]
    )
    if not file_paths:
        return

    # 设置输出目录
    output_dir = os.path.join(os.path.dirname(file_paths[0]), "output_images")

    try:
        split_images_to_a4(file_paths, output_dir)
        messagebox.showinfo("成功", f"图片已分割并保存到：\n{output_dir}")
    except Exception as e:
        messagebox.showerror("错误", f"处理图片时出错：\n{e}")

def create_gui():
    # 创建主窗口，使用 TkinterDnD.Tk() 替代 tk.Tk()
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()  # 使用 TkinterDnD 的 Tk 实例
    except ImportError:
        root = tk.Tk()  # 如果未安装 tkinterdnd2，则回退到普通 Tk 实例
        print("未安装 tkinterdnd2，拖拽功能不可用。")

    root.title("试卷图片分割工具")

    # 设置窗口大小
    root.geometry("400x200")
    root.resizable(False, False)

    # 添加提示标签
    label = tk.Label(root, text="拖拽图片到此窗口或点击按钮选择图片", font=("Arial", 12))
    label.pack(pady=20)

    # 添加选择图片按钮
    select_button = tk.Button(root, text="选择图片", command=select_images, font=("Arial", 12))
    select_button.pack(pady=10)

    # 支持拖拽功能
    def on_drop(event):
        # 修复拖拽路径解析问题，支持多个文件
        file_paths = event.data.strip("{").strip("}").split()
        valid_files = [file_path for file_path in file_paths if os.path.isfile(file_path)]
        if valid_files:
            output_dir = os.path.join(os.path.dirname(valid_files[0]), "output_images")
            try:
                split_images_to_a4(valid_files, output_dir)
                messagebox.showinfo("成功", f"图片已分割并保存到：\n{output_dir}")
            except Exception as e:
                messagebox.showerror("错误", f"处理图片时出错：\n{e}")
        else:
            messagebox.showerror("错误", "拖拽的文件无效，请拖拽图片文件。")

    # 如果 TkinterDnD 可用，绑定拖拽事件
    try:
        root.drop_target_register("*")
        root.dnd_bind("<<Drop>>", on_drop)
    except Exception as e:
        print(f"拖拽功能绑定失败：{e}")

    # 运行主循环
    root.mainloop()

if __name__ == "__main__":
    create_gui()
