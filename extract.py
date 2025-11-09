import zipfile
import rarfile
import io
import os
import docx  # 用于处理 .docx
import fitz  # PyMuPDF, 用于处理 .pdf


# ==============================================================================
# GradingService 类 (已更新，以支持 .docx, .pdf, .md)
# ==============================================================================

class GradingService:
    """处理所有指定的代码/文本文件信息，并合并内容。"""

    # --- 文件扩展名白名单 (已更新) ---
    ALLOWED_EXTENSIONS = {
        # Web
        ".html", ".css", ".vue",
        # Code
        ".py", ".java",
        # Document
        ".docx", ".pdf", ".md" 
    }
    # ----------------------------------------------

    def _get_content_from_file(self, filename: str, file_bytes: bytes) -> str:
        """
        根据文件类型提取文本内容。
        - .docx -> 使用 python-docx 库解析
        - .pdf -> 使用 PyMuPDF (fitz) 库解析
        - .md 和其他 -> 作为纯文本解码
        """
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return ""

        # --- .docx 文件处理逻辑 ---
        if file_ext == ".docx":
            try:
                mem_stream = io.BytesIO(file_bytes)
                document = docx.Document(mem_stream)
                full_text = [para.text for para in document.paragraphs]
                return "\n".join(full_text)
            except Exception as e:
                return f"[无法解析 .docx 文件: {filename}, 错误: {e}]"
        
        # --- 新增：.pdf 文件处理逻辑 ---
        elif file_ext == ".pdf":
            try:
                # 从内存中的字节流打开 PDF
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    full_text = [page.get_text() for page in doc]
                    return "\n".join(full_text)
            except Exception as e:
                return f"[无法解析 .pdf 文件: {filename}, 错误: {e}]"
        # ------------------------------------
        
        # --- 其他纯文本文件 (.py, .java, .md 等) 的解码逻辑 ---
        else:
            try:
                return file_bytes.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                return file_bytes.decode("latin-1", errors="ignore")

    def _process_archive_items(self, archive_ref, item_infos) -> str:
        """遍历压缩包内的文件，根据白名单筛选并提取内容。"""
        merged_contents = []
        
        for item_info in sorted(item_infos, key=lambda x: x.filename if hasattr(x, 'filename') else x.name):
            is_dir = item_info.is_dir() if hasattr(item_info, 'is_dir') else item_info.isdir()
            if is_dir:
                continue

            filename = item_info.filename if hasattr(item_info, 'filename') else item_info.name
            if filename.startswith("__MACOSX/") or os.path.basename(filename) == ".DS_Store" or filename.endswith('/'):
                continue

            if os.path.splitext(filename)[1].lower() in self.ALLOWED_EXTENSIONS:
                file_content_bytes = archive_ref.read(item_info)
                raw_answer = self._get_content_from_file(filename, file_content_bytes)
                
                if raw_answer and raw_answer.strip():
                    merged_contents.append(
                        f"--- 文件开始: {filename} ---\n\n"
                        f"{raw_answer.strip()}\n\n"
                        f"--- 文件结束: {filename} ---\n\n"
                    )
            elif filename.lower().endswith((".zip", ".rar")):
                try:
                    file_content_bytes = archive_ref.read(item_info)
                    nested_content = self.process_archive(file_content_bytes, filename)
                    if nested_content.strip():
                        raw_answer = (
                            f"--- 嵌套压缩包 '{filename}' 内容开始 ---\n\n"
                            f"{nested_content}\n"
                            f"--- 嵌套压缩包 '{filename}' 内容结束 ---\n"
                        )
                        merged_contents.append(raw_answer)
                except Exception as e:
                    merged_contents.append(f"--- 无法处理嵌套压缩文件: {filename} (错误: {e}) ---\n")
                    
        return "".join(merged_contents)

    def process_archive(self, file_bytes: bytes, original_filename: str) -> str:
        """
        处理文件的总入口。
        """
        file_ext = os.path.splitext(original_filename)[1].lower()
        
        try:
            file_stream = io.BytesIO(file_bytes)
            if file_ext == ".zip" and zipfile.is_zipfile(file_stream):
                file_stream.seek(0)
                with zipfile.ZipFile(file_stream, 'r') as zip_ref:
                    return self._process_archive_items(zip_ref, zip_ref.infolist())
            
            elif file_ext == ".rar" and rarfile.is_rarfile(file_stream):
                file_stream.seek(0)
                with rarfile.RarFile(file_stream, 'r') as rar_ref:
                    return self._process_archive_items(rar_ref, rar_ref.infolist())
            
            else:
                return self._get_content_from_file(original_filename, file_bytes)

        except Exception as e:
            return f"[处理文件 '{original_filename}' 时发生错误: {e}]"

# ==============================================================================
# 遍历指定文件夹并提取所有内容
# ==============================================================================

def extract_content_from_folder(folder_path: str, output_txt_file: str):
    """
    遍历指定文件夹中的所有文件和子文件夹，根据白名单提取文本内容并保存。
    """
    if not os.path.isdir(folder_path):
        print(f"错误: 文件夹 '{folder_path}' 不存在。")
        return

    grading_service = GradingService()
    all_extracted_content = []
    
    print(f"开始处理文件夹: {folder_path}")
    print(f"将只提取以下类型的文件: {', '.join(grading_service.ALLOWED_EXTENSIONS)}")

    for root, _, files in os.walk(folder_path):
        for filename in sorted(files):
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, folder_path)
            
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in grading_service.ALLOWED_EXTENSIONS and file_ext not in ['.zip', '.rar']:
                continue

            print(f"  -> 正在处理: {relative_path}")

            try:
                with open(full_path, "rb") as f:
                    file_bytes = f.read()
                
                content = grading_service.process_archive(file_bytes, filename)
                
                if content and content.strip():
                    separator = f"====================\n源文件: {relative_path}\n====================\n\n"
                    all_extracted_content.append(separator + content.strip() + "\n\n")

            except Exception as e:
                print(f"    [!] 处理文件 {relative_path} 时跳过，发生错误: {e}")
    
    if not all_extracted_content:
        print("\n处理完成，但未找到任何符合筛选条件的文件。")
        return

    try:
        with open(output_txt_file, "w", encoding="utf-8") as f:
            f.write("".join(all_extracted_content))
        print(f"\n处理完成！所有内容已成功汇总到: {output_txt_file}")
    except Exception as e:
        print(f"\n错误: 无法写入输出文件 {output_txt_file}。原因: {e}")

# ==============================================================================
# 主程序入口
# ==============================================================================
if __name__ == "__main__":
    # --- 请在这里配置 ---
    # 1. 设置您要扫描的文件夹路径
    SOURCE_FOLDER = r"D:\DZQ\项目\软件工程设计"
    
    # 2. 设置输出的 txt 文件名
    OUTPUT_FILE = "extracted.txt"
    # --------------------

    extract_content_from_folder(SOURCE_FOLDER, OUTPUT_FILE)

