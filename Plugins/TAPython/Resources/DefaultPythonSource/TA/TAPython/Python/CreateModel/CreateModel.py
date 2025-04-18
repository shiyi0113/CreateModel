# -*- coding: utf-8 -*-
import unreal
import os
import socket
import struct
from pathlib import Path
from tkinter import filedialog, Tk
import zipfile
import shutil
import time
import errno

class CreateModel:
    current_image_path = None
    model_path = None
    gif_path = None
    original_image_path = None
    perspective_image_path = None
    # 在类的开头添加单例支持
    _instance = None  # 类变量用于存储实例    

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __init__(self, json_path: str):
        self.data = unreal.PythonBPLib.get_chameleon_data(json_path)
        if not self.data:
            raise RuntimeError(f"Failed to load UI configuration from {json_path}")
        # 获取界面组件
        self.ui_main_content="main_overlay"             # 主界面
        self.ui_result_overlay="result_overlay"         # 结果展示界面
        self.ui_processing="processing_overlay"         # 处理中界面
        self.ui_failure_overlay="failure_overlay"       # 连接失败界面
        # 获取组件
        self.ui_text_to_model="text_to_model"            # 文生模型
        self.ui_image_to_model="image_to_model"          # 图生模型
        self.ui_preview_image="preview_image"            # 图生模型的图片预览
        self.ui_text_to_model_textbox="textbox"          # 文生模型的输入框
        self.ui_combobox="CombBox"                       # 生成模式选择框
        self.ui_original_image="original_image"          # 结果界面-原图
        self.ui_perspective_image="perspective_image"    # 结果界面-视角图   
        # 保存实例引用
        CreateModel._instance = self
    
    # 返回首页按钮
    def back_to_homepage(self):
        self.data.set_visibility(self.ui_main_content, "Visible")
        self.data.set_visibility(self.ui_result_overlay, "Collapsed")
        self.data.set_visibility(self.ui_processing, "Collapsed")
        self.data.set_visibility(self.ui_failure_overlay, "Collapsed")
        self.select_generate_mode(self.data.get_combo_box_selected_item(self.ui_combobox))
        self.current_image_path = None 
        self.model_path = None

    # 选择生成模式
    def select_generate_mode(self, model_type):
        if model_type == "文生模型":  
            self.data.set_visibility(self.ui_text_to_model, "Visible")
            self.data.set_visibility(self.ui_image_to_model, "Collapsed")
            self.data.set_visibility(self.ui_preview_image, "Collapsed")
            self.data.set_text(self.ui_text_to_model_textbox, "")
            self.current_image_path = None 
        elif model_type == "图生模型":
            self.data.set_visibility(self.ui_text_to_model, "Collapsed")
            self.data.set_visibility(self.ui_image_to_model, "Visible")
            self.data.set_visibility(self.ui_preview_image, "Collapsed")
            self.data.set_text(self.ui_text_to_model_textbox, "")
            self.current_image_path = None
        else:
            self.data.set_visibility(self.ui_text_to_model, "Collapsed")
            self.data.set_visibility(self.ui_image_to_model, "Collapsed")
            self.data.set_visibility(self.ui_preview_image, "Collapsed")
            self.data.set_text(self.ui_text_to_model_textbox, "")
            self.current_image_path = None
    
    # 添加图片按钮
    def add_picture(self):
        try:
            root = Tk()
            root.withdraw()
            
            file_path = filedialog.askopenfilename(
                title="选择图片",
                filetypes=[
                    ("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                    ("All Files", "*.*")
                ]
            )
            
            self.current_image_path = file_path
            self.data.set_image_from_path(self.ui_preview_image, self.current_image_path)
            self.data.set_visibility(self.ui_preview_image, "Visible")            
        finally:
            if 'root' in locals():
                root.destroy()
    
    # 创建模型按钮  
    def create_model(self):
        temp_file = None  # 初始化临时文件变量
        if not self.current_image_path and not self.data.get_text(self.ui_text_to_model_textbox):
            self.data.modal_window("CreateModel/failure.json")
            return False
        try:
            # 检查是否已有监听线程在运行,如果有则不允许创建新的模型
            if hasattr(self, 'listen_thread') and self.listen_thread.is_alive():
                self.data.set_text(self.ui_failure_text,"本机已有请求正在生成...")
                self.data.modal_window("CreateModel/linkfail.json")
                self.back_to_homepage()             
                return False
            # 更新UI显示
            self.data.set_visibility(self.ui_main_content, "Collapsed")
            self.data.set_visibility(self.ui_processing, "Visible")

            # 根据输入类型发送不同的数据
            if self.current_image_path:
                # 发送图片文件
                file_path = self.current_image_path
            else:
                # 如果是文本输入，创建临时文本文件，使用输入的文本内容作为文件名
                text_content = self.data.get_text(self.ui_text_to_model_textbox)
                # 将文本内容作为文件名（去除特殊字符，限制长度）
                safe_filename = "".join(x for x in text_content if x.isalnum() or x in (' ', '_'))[:50]
                safe_filename = safe_filename.strip().replace(' ', '_')
                if not safe_filename:  # 如果文件名为空（比如只包含特殊字符），使用默认名称
                    safe_filename = "text_prompt"
                
                temp_file = Path(f"{safe_filename}.txt")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(text_content)
                file_path = str(temp_file)

            # 发送文件到服务器
            if not self.send_file(file_path, '192.168.110.133', 8088):
                self.data.modal_window("CreateModel/linkfail.json")
                self.back_to_homepage()
                return False
            
            # 启动后台监听线程，接收处理后的图片、视频和模型
            self.start_listening_thread() 
            return True
        
        except Exception as e:
            print(f"创建模型时出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False
        finally:
            # 如果存在临时文本文件，删除它
            if temp_file and temp_file.exists():
                temp_file.unlink()
    
    # 导入模型按钮
    def import_model(self):
        """导入模型到UE编辑器"""
        try:
            if not self.model_path or not os.path.exists(self.model_path):
                print(f"模型文件不存在: {self.model_path}")
                return False
            
            model_dir = os.path.dirname(self.model_path)
            model_name = os.path.splitext(os.path.basename(self.model_path))[0]
            
            # 查找可用的序号
            index = 1
            while True:
                destination_path = f'/Game/Models/input{index}'
                if not unreal.EditorAssetLibrary.does_asset_exist(f"{destination_path}/mesh"):
                    break
                index += 1
            
            print(f"模型目录: {model_dir}")
            print(f"模型文件: {self.model_path}")
            print(f"导入路径: {destination_path}")
            
            # 创建导入任务
            task = unreal.AssetImportTask()
            task.set_editor_property('filename', self.model_path)
            task.set_editor_property('destination_path', destination_path)
            task.set_editor_property('replace_existing', True)
            task.set_editor_property('automated', True)
            #task.set_editor_property('save', True)
            
            # 执行导入
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            imported_assets = asset_tools.import_asset_tasks([task])
            
            # 等待资产构建完成
            time.sleep(2)  # 等待2秒让UE完成资产构建
            
            # 检查资产是否存在
            expected_asset_path = f"{destination_path}/mesh"
            if unreal.EditorAssetLibrary.does_asset_exist(expected_asset_path):
                print("模型导入成功")
                return True
            else:
                print("模型导入失败：资产不存在")
                return False
            
        except Exception as e:
            print(f"导入模型时出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return False

    # 模型演示按钮：显示GIF图片
    def show_gif(self):
        if not os.path.exists(self.gif_path):
            print(f"GIF文件不存在: {self.gif_path}")
            return     
        # 使用系统默认程序打开GIF文件
        try:
            os.startfile(self.gif_path)  # Windows系统
        except AttributeError:
            import subprocess
            # 对于MacOS和Linux系统
            if os.name == 'posix':
                subprocess.call(('open', self.gif_path))  # MacOS
            else:
                subprocess.call(('xdg-open', self.gif_path))  # Linux
    # 发送文件
    def send_file(self, file_path, host:str='127.0.0.1', port:int=5000)->bool:
        """
        发送文件到服务器
        发送格式：文件大小(8字节) + 文件名长度(2字节) + 文件名(utf-8编码) + 文件内容
        Args:
            file_path: 要发送的文件路径
            host: 服务器IP地址
            port: 服务器端口号
        Returns:
            bool: 发送是否成功
        """
        try:
            # 创建socket连接
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect_ex((host, port))  
            # 获取文件大小
            filesize = os.path.getsize(file_path)
            # 获取文件名
            filename = os.path.basename(file_path)
            # 将文件名编码为utf-8
            filename_bytes = filename.encode('utf-8')
            # 获取文件名长度
            name_length = len(filename_bytes)
                
            print(f"准备发送文件: {filename}, 大小: {filesize} bytes")
                
            # 发送文件大(8字节)
            client_socket.send(struct.pack('!Q', filesize))    
            # 发送文件名长度(2字节)
            client_socket.send(struct.pack('!H', name_length))   
            # 发送文件名
            client_socket.send(filename_bytes)    
            # 发送文件内容
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(1024000)
                    if not data:
                        break
                    client_socket.send(data)
                        
            print(f"文件 {filename} 发送完成")
            return True
        
        except Exception as e:
            print(f"发送文件时出错: {str(e)}")
            return False
        finally:
            if 'client_socket' in locals():
                client_socket.close()
                print("已关闭发送文件的连接")
    
    # 接收文件
    def receive_file(self, client_socket, save_dir, buffer):
        """
        接收文件并返回保存路径
        接收文件格式：文件大小(8字节) + 文件名长度(2字节) + 文件名(utf-8编码) + 文件内容
        Args:
            client_socket: socket连接对象
            save_dir: 保存路径
            buffer: 缓冲区
        Returns:
            Path: 保存路径
        """
        save_path = None
        try:
            # 读取文件大小
            while len(buffer) < 8:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        raise Exception("连接已关闭")
                    buffer += data
                except socket.error as e:
                    if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                        time.sleep(0.1)
                        continue
                    raise
            
            file_size = struct.unpack('!Q', buffer[:8])[0]
            buffer = buffer[8:]
            
            # 读取文件名长度
            while len(buffer) < 2:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        raise Exception("连接已关闭")
                    buffer += data
                except socket.error as e:
                    if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                        time.sleep(0.1)
                        continue
                    raise
            
            name_length = struct.unpack('!H', buffer[:2])[0]
            buffer = buffer[2:]
            
            # 读取文件名
            while len(buffer) < name_length:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        raise Exception("连接已关闭")
                    buffer += data
                except socket.error as e:
                    if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                        time.sleep(0.1)
                        continue
                    raise
            
            filename = buffer[:name_length].decode()
            buffer = buffer[name_length:]
            
            print(f"开始接收文件: {filename}, 大小: {file_size} bytes")
            
            # 保存文件
            save_path = save_dir / filename
            received = 0
            
            with open(save_path, 'wb') as f:
                # 先写入buffer中的数据
                to_write = min(len(buffer), file_size)
                if to_write > 0:
                    f.write(buffer[:to_write])
                    buffer = buffer[to_write:]
                    received += to_write
                
                # 继续接收剩余数据
                last_progress = 0  # 记录上次打印的进度
                while received < file_size:
                    try:
                        chunk = client_socket.recv(min(8192, file_size - received))
                        if not chunk:
                            raise Exception(f"连接断开，已接收: {received}/{file_size} bytes")
                        f.write(chunk)
                        received += len(chunk)
                        
                        # 每10%打印一次进度
                        progress = (received / file_size) * 100
                        if progress - last_progress >= 10:
                            print(f"\r接收进度: {progress:.1f}%", end='')
                            last_progress = progress
                            
                    except socket.error as e:
                        if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                            time.sleep(0.1)
                            continue
                        raise
                
                # 确保打印100%进度
                if last_progress < 100:
                    print(f"\r接收进度: 100.0%")
            
            print(f"\n文件接收完成: {save_path}")
            return save_path
            
        except Exception as e:
            print(f"接收文件时出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            if save_path and save_path.exists():
                save_path.unlink()  # 删除不完整的文件
            raise
    
    # 启动后台监听线程
    def start_listening_thread(self):
        """启动后台监听线程"""
        def listen_for_results():
            server_socket = None
            try:
                print("开始监听处理结果...")
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.bind(('0.0.0.0', 5001))
                server_socket.listen(1)  # 只需要接收一个连接
                
                # 设置保存目录
                current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
                save_dir = current_dir / "received"
                save_dir.mkdir(parents=True, exist_ok=True)
                
                print("等待接收处理结果...")
                client_socket = None
                try:
                    client_socket, addr = server_socket.accept()
                    buffer = b''
                    saved_path = self.receive_file(client_socket, save_dir, buffer)
                    print(f"成功接收处理结果: {saved_path}")
                    
                    # 处理接收到的文件
                    self.process_received_file(saved_path)
                    
                except Exception as e:
                    print(f"接收文件时出错: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    self.data.modal_window("CreateModel/linkfail.json")
                    self.back_to_homepage()
                finally:
                    if client_socket:
                        client_socket.close()
                
            except socket.timeout:
                print("监听超时：等待时间超过30分钟")
                self.data.modal_window("CreateModel/linkfail.json")
                self.back_to_homepage()
            except Exception as e:
                print(f"监听结果时出错: {str(e)}")
                import traceback
                print(traceback.format_exc())
                self.data.modal_window("CreateModel/linkfail.json")
                self.back_to_homepage()
            finally:
                if server_socket:
                    server_socket.close()
    
        # 启动监听线程
        import threading
        self.listen_thread = threading.Thread(target=listen_for_results)
        self.listen_thread.daemon = True
        self.listen_thread.start()
    # 处理接收到的文件
    def process_received_file(self, file_path):
        """
        处理接收到的文件
        Args:
            file_path: 接收到的文件路径
        """
        try:
            # 如果接收到的是zip文件,进行解压
            if file_path.suffix.lower() == '.zip':
                # 获取压缩文件的名称（不含扩展名）作为解压目录名
                zip_name = file_path.stem
                
                # 解压目录为 received/压缩文件名/
                extract_dir = file_path.parent / zip_name
                extract_dir.mkdir(parents=True, exist_ok=True)
                
                # 解压文件
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                print(f"成功解压文件到: {extract_dir}")
                
                # 删除zip文件
                file_path.unlink()
                
                # 保存路径供UI更新使用
                self.model_path = str(extract_dir / "output" / "mesh.glb")
                self.gif_path = str(extract_dir / "output" / "output.gif")
                self.perspective_image_path = str(extract_dir / "output" / "views.jpg")
                # 如果是文生模型,设置原始图片为文本框内容
                if self.data.get_combo_box_selected_item(self.ui_combobox) == "文生模型":
                    self.original_image_path = str(extract_dir / "output" / "img.jpg")
                else:
                    self.original_image_path = self.current_image_path
                # 在主线程中更新UI
                cmd = "from CreateModel.CreateModel import CreateModel\n" \
                      f"instance = CreateModel.get_instance()\n" \
                      "if instance:\n" \
                      "    instance._update_ui_after_process()\n" \
                      "else:\n" \
                      "    print(\"错误：无法获取CreateModel实例\")"
                unreal.PythonBPLib.exec_python_command(cmd, True)
                
        except Exception as e:
            print(f"处理接收文件时出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            # 在主线程中处理错误
            cmd = "from CreateModel.CreateModel import CreateModel\n" \
                  f"instance = CreateModel.get_instance()\n" \
                  "if instance:\n" \
                  "    instance._handle_process_error()\n" \
                  "else:\n" \
                  "    print(\"错误：无法获取CreateModel实例\")"
            unreal.PythonBPLib.exec_python_command(cmd, True)

    def _update_ui_after_process(self):
        """在游戏线程中更新UI"""
        self.data.set_image_from_path(self.ui_original_image, self.original_image_path)
        self.data.set_image_from_path(self.ui_perspective_image, self.perspective_image_path)
        self.data.set_visibility(self.ui_processing, "Collapsed")
        self.data.set_visibility(self.ui_result_overlay, "Visible")

    def _handle_process_error(self):
        """在游戏线程中处理错误"""
        self.data.modal_window("CreateModel/linkfail.json")
        self.back_to_homepage()
        