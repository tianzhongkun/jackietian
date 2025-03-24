import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from datetime import datetime

clipboard = {"action": None, "path": None}  # 用于存储剪切或复制的文件路径
current_editing_file = None  # 当前正在编辑的文件路径

def format_size(size):
    """动态格式化文件大小为 KB、MB 或 GB"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"

def populate_tree(tree, parent, path):
    """递归填充目录树，并以缩进模式显示"""
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            size = format_size(os.path.getsize(item_path)) if not is_dir else ""
            mtime = datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M:%S")
            node = tree.insert(parent, "end", text=item, values=[item_path, size, mtime], open=False)
            if is_dir:
                tree.insert(node, "end")  # 添加一个占位符
    except PermissionError:
        pass  # 忽略无权限访问的目录

def on_tree_expand(event):
    """展开目录时动态加载子目录"""
    tree = event.widget
    node = tree.focus()
    path = tree.item(node, "values")[0]
    children = tree.get_children(node)
    if len(children) == 1 and not tree.item(children[0], "values"):  # 检查是否是占位符
        tree.delete(children[0])
        populate_tree(tree, node, path)

def on_tree_select(event, preview_text, preview_image_label, save_button, discard_button):
    """选中树节点时显示预览"""
    global current_editing_file
    tree = event.widget
    selected_item = tree.focus()
    if not selected_item:
        return
    path = tree.item(selected_item, "values")[0]
    current_editing_file = None  # 重置当前编辑文件
    save_button.config(state="disabled")
    discard_button.config(state="disabled")
    if os.path.isfile(path):
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
            # 显示图片
            try:
                img = Image.open(path)
                img.thumbnail((300, 300))
                img_tk = ImageTk.PhotoImage(img)
                preview_image_label.config(image=img_tk)
                preview_image_label.image = img_tk
                preview_text.delete("1.0", tk.END)
            except Exception as e:
                preview_text.delete("1.0", tk.END)
                preview_text.insert(tk.END, f"无法加载图片：{e}")
        elif path.lower().endswith((".txt", ".log", ".py", ".md")):
            # 显示文本内容并启用编辑功能
            try:
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                preview_text.delete("1.0", tk.END)
                preview_text.insert(tk.END, content)
                preview_image_label.config(image="")
                preview_image_label.image = None
                current_editing_file = path
                save_button.config(state="normal")
                discard_button.config(state="normal")
            except Exception as e:
                preview_text.delete("1.0", tk.END)
                preview_text.insert(tk.END, f"无法加载文本：{e}")
        else:
            preview_text.delete("1.0", tk.END)
            preview_text.insert(tk.END, "不支持的文件类型")
            preview_image_label.config(image="")
            preview_image_label.image = None
    else:
        preview_text.delete("1.0", tk.END)
        preview_text.insert(tk.END, "请选择文件以预览")
        preview_image_label.config(image="")
        preview_image_label.image = None

def save_changes(preview_text):
    """保存编辑的文本内容到文件"""
    global current_editing_file
    if current_editing_file:
        try:
            with open(current_editing_file, "w", encoding="utf-8") as file:
                file.write(preview_text.get("1.0", tk.END).strip())
            messagebox.showinfo("成功", f"已保存修改到文件：{current_editing_file}")
        except Exception as e:
            messagebox.showerror("错误", f"无法保存文件：{e}")

def discard_changes(preview_text):
    """放弃修改并重新加载文件内容"""
    global current_editing_file
    if current_editing_file:
        try:
            with open(current_editing_file, "r", encoding="utf-8") as file:
                content = file.read()
            preview_text.delete("1.0", tk.END)
            preview_text.insert(tk.END, content)
            messagebox.showinfo("提示", "已放弃修改，恢复原始内容")
        except Exception as e:
            messagebox.showerror("错误", f"无法加载文件：{e}")

def delete_selected(tree):
    """删除选中的文件或目录"""
    selected_item = tree.focus()
    if not selected_item:
        messagebox.showwarning("警告", "请先选择一个文件或目录！")
        return
    path = tree.item(selected_item, "values")[0]
    try:
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)
        tree.delete(selected_item)
        messagebox.showinfo("成功", f"已删除：{path}")
    except Exception as e:
        messagebox.showerror("错误", f"无法删除：{e}")

def copy_selected(tree):
    """复制选中的文件或目录"""
    global clipboard
    selected_item = tree.focus()
    if not selected_item:
        messagebox.showwarning("警告", "请先选择一个文件或目录！")
        return
    path = tree.item(selected_item, "values")[0]
    clipboard = {"action": "copy", "path": path}
    messagebox.showinfo("成功", f"已复制：{path}")

def cut_selected(tree):
    """剪切选中的文件或目录"""
    global clipboard
    selected_item = tree.focus()
    if not selected_item:
        messagebox.showwarning("警告", "请先选择一个文件或目录！")
        return
    path = tree.item(selected_item, "values")[0]
    clipboard = {"action": "cut", "path": path}
    messagebox.showinfo("成功", f"已剪切：{path}")

def paste_selected(tree):
    """粘贴文件或目录"""
    global clipboard
    selected_item = tree.focus()
    if not selected_item:
        messagebox.showwarning("警告", "请先选择一个目标目录！")
        return
    dest_path = tree.item(selected_item, "values")[0]
    if not os.path.isdir(dest_path):
        messagebox.showwarning("警告", "目标必须是一个目录！")
        return
    if clipboard["action"] and clipboard["path"]:
        src_path = clipboard["path"]
        try:
            if clipboard["action"] == "copy":
                if os.path.isfile(src_path):
                    shutil.copy2(src_path, dest_path)
                else:
                    shutil.copytree(src_path, os.path.join(dest_path, os.path.basename(src_path)))
            elif clipboard["action"] == "cut":
                shutil.move(src_path, dest_path)
            messagebox.showinfo("成功", f"已粘贴到：{dest_path}")
            clipboard = {"action": None, "path": None}
        except Exception as e:
            messagebox.showerror("错误", f"无法粘贴：{e}")

def show_context_menu(event, tree):
    """显示右键菜单"""
    menu = tk.Menu(tree, tearoff=0)
    menu.add_command(label="删除", command=lambda: delete_selected(tree))
    menu.add_command(label="复制", command=lambda: copy_selected(tree))
    menu.add_command(label="剪切", command=lambda: cut_selected(tree))
    menu.add_command(label="粘贴", command=lambda: paste_selected(tree))
    menu.post(event.x_root, event.y_root)

def main():
    root = tk.Tk()
    root.title("文件管理工具")
    root.geometry("1200x700")

    # 左侧 Treeview 组件
    tree_frame = tk.Frame(root)
    tree_frame.pack(fill="y", side="left", padx=5, pady=5)

    tree = ttk.Treeview(tree_frame, columns=("fullpath", "size", "mtime"), show="tree")
    tree.heading("#0", text="名称", anchor="w")
    tree.heading("fullpath", text="路径", anchor="w")
    tree.heading("size", text="大小", anchor="w")
    tree.heading("mtime", text="修改时间", anchor="w")
    tree.column("#0", stretch=True)
    tree.column("fullpath", width=300, anchor="w")
    tree.column("size", width=100, anchor="center")
    tree.column("mtime", width=150, anchor="center")
    tree.pack(fill="y", expand=True, side="left")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(fill="y", side="right")

    # 右侧预览区域
    preview_frame = tk.Frame(root, bg="white", relief="sunken", borderwidth=2)
    preview_frame.pack(fill="both", expand=True, side="right", padx=5, pady=5)

    preview_image_label = tk.Label(preview_frame, bg="white")
    preview_image_label.pack(fill="x", padx=10, pady=10)

    preview_text = tk.Text(preview_frame, wrap="word", bg="white")
    preview_text.pack(fill="both", expand=True, padx=10, pady=10)

    # 保存和放弃按钮
    button_frame = tk.Frame(preview_frame, bg="white")
    button_frame.pack(fill="x", padx=10, pady=5)
    save_button = tk.Button(button_frame, text="保存", state="disabled", command=lambda: save_changes(preview_text))
    save_button.pack(side="left", padx=5)
    discard_button = tk.Button(button_frame, text="放弃", state="disabled", command=lambda: discard_changes(preview_text))
    discard_button.pack(side="left", padx=5)

    # 填充根目录（所有硬盘）
    for drive in [f"{chr(d)}:\\" for d in range(65, 91) if os.path.exists(f"{chr(d)}:\\")]:
        node = tree.insert("", "end", text=drive, values=[drive, "", ""], open=False)
        populate_tree(tree, node, drive)

    # 绑定事件
    tree.bind("<<TreeviewOpen>>", on_tree_expand)
    tree.bind("<<TreeviewSelect>>", lambda e: on_tree_select(e, preview_text, preview_image_label, save_button, discard_button))
    tree.bind("<Button-3>", lambda e: show_context_menu(e, tree))

    root.mainloop()

if __name__ == "__main__":
    main()
