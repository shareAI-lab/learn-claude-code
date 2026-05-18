import os
import shutil
import glob

# 配置要删除的文件夹名称列表
DIRS_TO_DELETE = [
    '.git',
    'node_modules',
    '__pycache__',
    '.pytest_cache',
    'venv',
    '.venv',
    'env',
    'build',
    'dist',
    '.next',
    '.idea',
    '.DS_Store'
]

# 配置要删除的文件扩展名或模式
FILES_TO_DELETE = [
    '*.log',
    '*.pyc',
    '.DS_Store',
    # LaTeX 编译产生的中间文件
    '*.aux',
    '*.out',
    '*.bbl',
    '*.blg',
    '*.synctex.gz',
    '*.fls',
    '*.fdb_latexmk',
    '*.toc'
]

def format_size(size):
    """将字节大小格式化为易读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

def clean_directory(root_dir):
    print(f"开始清理目录: {root_dir}")
    total_freed_space = 0
    deleted_dirs = 0
    deleted_files = 0

    # 1. 遍历并删除匹配的文件夹和文件
    # 使用 topdown=False 是为了在修改目录结构时不影响遍历
    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        
        # 删除文件夹
        for dirname in dirnames:
            if dirname in DIRS_TO_DELETE:
                full_path = os.path.join(dirpath, dirname)
                try:
                    # 计算文件夹大小
                    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, filenames in os.walk(full_path) for f in filenames)
                    total_freed_space += size
                    
                    shutil.rmtree(full_path)
                    print(f"[已删除目录] {full_path} (释放了 {format_size(size)})")
                    deleted_dirs += 1
                except Exception as e:
                    print(f"[错误] 无法删除目录 {full_path}: {e}")

        # 删除特定文件
        for filename in filenames:
            # 检查文件是否匹配模式
            is_match = False
            for pattern in FILES_TO_DELETE:
                if glob.fnmatch.fnmatch(filename, pattern):
                    is_match = True
                    break
            
            if is_match:
                full_path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(full_path)
                    total_freed_space += size
                    os.remove(full_path)
                    print(f"[已删除文件] {full_path} (释放了 {format_size(size)})")
                    deleted_files += 1
                except Exception as e:
                    print(f"[错误] 无法删除文件 {full_path}: {e}")

    print("-" * 40)
    print("清理完成！")
    print(f"总计删除文件夹数量: {deleted_dirs}")
    print(f"总计删除文件数量: {deleted_files}")
    print(f"总计释放空间: {format_size(total_freed_space)}")

if __name__ == "__main__":
    # 默认获取当前脚本所在的目录作为根目录
    current_directory = os.path.dirname(os.path.abspath(__file__))
    
    # 确认提示（防止误删）
    print("=========================================")
    print("即将开始清理以下无用目录和文件用于备份准备：")
    print(f"目标文件夹: {DIRS_TO_DELETE}")
    print(f"目标文件: {FILES_TO_DELETE}")
    print("=========================================")
    
    confirm = input("确定要继续吗？(输入 y 确认, 其他键取消): ")
    if confirm.lower() == 'y':
        clean_directory(current_directory)
    else:
        print("已取消清理。")
