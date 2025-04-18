# UE生成模型插件

# 项目描述

- 在UE中实现图片生成模型,支持导入素材库
- 在UE中实现文字生成模型,支持导入素材库

### 插件

**TAPython**

- 官网: [https://www.tacolor.xyz/zh-cn/pages/TAPython.html](https://www.tacolor.xyz/zh-cn/pages/TAPython.html)
- 描述: 基于UE原生Slate的界面,在UE界面中为Python工具创建界面

### AI模型

**腾讯混元-3D**

- 官网: [https://3d.hunyuan.tencent.com/](https://3d.hunyuan.tencent.com/)
- 描述: 首个同时支持文生和图生的3D开源模型

# 使用方法

从Releases中下载文件，解压到你的项目的Plugins文件夹内（没有的话先创建一个）

![image](https://github.com/user-attachments/assets/7c8c7b59-c9ca-4a62-ba67-23f97ca6e5b7)

打开你的项目，点击编辑-项目设置-插件-Python，添加一个额外路径：`你的项目/TA/TAPython/Python`

![image 1](https://github.com/user-attachments/assets/d12cefc2-d2e4-4bb7-a6da-571c60d10dac)

重启引擎即可使用

# 大模型本地部署

<aside>
📌

**使用模型**

腾讯混元-3D：https://github.com/Tencent/Hunyuan3D-1

**测试环境**

显卡型号：NVIDIA GeForce RTX 3090 (24GB)

系统版本：Ubuntu 22.04

Conda：Miniconda3

python：3.10

cuda：12.1

</aside>

## 环境搭建

```bash
'''复制模型仓库'''
git clone https://github.com/tencent/Hunyuan3D-1
cd Hunyuan3D-1
'''环境配置'''
# 创建虚拟环境
conda create -n hunyuan3d-1 python=3.10    #3.9 or 3.11 or 3.12
conda activate hunyuan3d-1
# 配置cuda版本12.1的pytorch和torchvision
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# 运行环境安装脚本   ★请多运行几次，可能会因为网络问题部分库安装失败
bash env_install.sh
# 由于CC BY-NC-SA 4.0许可的原因，如果需要使用纹理烘焙，需要下载dust3r
cd third_party
git clone --recursive https://github.com/naver/dust3r.git
mkdir weights && cd ../third_party/weights
wget https://download.europe.naverlabs.com/ComputerVision/DUSt3R/DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth
# (可选)安装 xformers进行加速
pip install xformers --index-url https://download.pytorch.org/whl/cu121
# 安装onnxruntime库
pip install onnxruntime
'''模型下载'''
# 使用国内镜像站（不然后面需要翻墙进行）
export HF_ENDPOINT=https://hf-mirror.com
# 登陆huggingface(需要输入token,前往huggingface官网注册获取）
huggingface-cli login
# 下载模型
mkdir weights
huggingface-cli download tencent/Hunyuan3D-1 --local-dir ./weights
mkdir weights/hunyuanDiT
huggingface-cli download Tencent-Hunyuan/HunyuanDiT-v1.1-Diffusers-Distilled --local-dir ./weights/hunyuanDiT
```

## 显存需求

Inference Std-pipeline需要30GB VRAM （使用--save_memory参数，需要24GB VRAM）

Inference Lite-pipeline需要22GB VRAM  (使用--save_memory参数，需要18GB VRAM）

*▲ 注：使用--save_memory参数将增加推理时间。*

## 参数

**基础参数**

- `--text_prompt` - 文本提示词
- `--image_prompt` - 图片输入路径

*注：以上两个参数只能二选一*

**模型和设备参数**

- `--use_lite` - 是否使用轻量化模型（默认：False）
- `--device` - 运行设备（默认：cuda:0）
- `--save_memory` - 是否使用节省内存模式（默认：False）

**路径参数**

- `--save_folder` - 输出存储路径（默认：*./outputs/test/*）
- `--text2image_path` - 文生图模型路径（默认：*weights/hunyuanDiT*）
- `--mv23d_ckt_path` - 3D模型权重文件路径（默认：*weights/svrm/svrm.safetensors*）
- `--mv23d_cfg_path` - 3D模型配置文件路径（默认：*./svrm/configs/svrm.yaml*）

**生成相关参数**

- `--t2i_seed` - 文生图随机种子（默认：0）
- `--t2i_steps` - 文生图推理步数（默认：25）
- `--gen_seed` - 3D生成随机种子（默认：0）
- `--gen_steps` - 3D生成推理步数（默认：50）
- `--max_faces_num` - 最大面数（默认：120000，*使用纹理/烘焙颜色时建议10000*）

**后处理参数**

- `--do_texture_mapping` - 是否进行纹理映射（默认：False）
- `--do_render` - 是否渲染GIF（默认：False）
- `--do_bake` - 是否进行纹理烘焙（默认：False）
- `--bake_align_times` - 视图与网格之间的对齐次数（默认：3，*建议1~6*）

<aside>
✅

3090 24GB 下推荐参数：

`CUDA_VISIBLE_DEVICES=2 python3 main.py --text_prompt "睡觉的卡比兽" --save_folder ./outputs/test/ --max_faces_num 120000  --save_memory --do_texture_mapping --do_render`

</aside>

## 可能遇到的问题

### 1、运行设备问题

**问题描述：**

使用`--device`参数只能将部分计算切换过去，导致产生如下错误

`RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:2 and cuda:0!`

**解决方式：**

不使用这个参数切换设备，使用`CUDA_VISIBLE_DEVICES=2`

例如：

```bash
CUDA_VISIBLE_DEVICES=2 python3 main.py --text_prompt "躺在路边睡觉的卡比兽" --save_memory --use_lite --save_folder ./outputs/test/ --max_faces_num 100000 --do_bake
```

### 2、烘焙问题

**问题描述：**

① 如果需要使用`--do_bake`参数，要先下载dust3r(见环境搭建)，并应遵守许可，无法商用；

② 下载的`../third_party/weights/DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth`与模型中的语句不匹配，需要修改。

**解决方式：**

▲ 修改1：`../third_party/check.py`中的line 6。

原句：`is_ok = os.path.exists("./third_party/weights/DUSt3R_ViTLarge_BaseDecoder_512_dpt/model.safetensors")`

修改为：`is_ok = os.path.exists("./third_party/weights/DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth")`

▲ 修改2：`../third_party/mesh_baker.py`中的line 25。

原句：`*align_model* = "third_party/weights/DUSt3R_ViTLarge_BaseDecoder_512_dpt",`

修改为：`*align_model* = "third_party/weights/DUSt3R_ViTLarge_BaseDecoder_512_dpt.pth",`

### 3、渲染GIF问题

**问题描述：**

使用`--do_render`参数时，会出现一个错误：`NameError: name 'glob' is not defined`

**解决方式：**

在`../Hunyuan3D-1/main.py`中添加头文件：`from glob import glob`

### 4、参数选择问题

`--do_render`和`--do_bake`的使用前提是加上`--do_texture_mapping`，无法单独使用。
