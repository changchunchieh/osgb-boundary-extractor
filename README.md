# OSGB瓦片范围提取工具

## 项目简介

OSGB瓦片范围提取工具是一个专门用于从OSGB格式的三维模型数据中提取边界并生成Shapefile的Python工具集。该工具支持两种提取模式：标准版（基于行列号计算）和原始坐标版（基于文件夹名称提取坐标）。

## 功能特点

### 核心功能

| 功能 | 说明 |
|------|------|
| **OSGB瓦片范围提取** | 从OSGB瓦片数据中提取瓦片范围信息 |
| **多种提取模式** | 支持标准版（行列号计算）和原始坐标版（文件夹名称提取） |
| **坐标系统处理** | 自动从metadata.xml读取坐标系统或手动指定 |
| **坐标转换** | 支持输入输出坐标系统分离，可进行坐标转换 |
| **多边形操作** | 支持保留原始瓦片多边形或合并为单一多边形 |
| **原点模式** | 支持原点作为最小坐标或最大坐标的计算模式 |
| **自动路径检测** | 自动检测Data子文件夹，简化路径输入 |
| **详细报告** | 生成包含处理信息和边界范围的详细报告 |

### 工具对比

| 工具 | 特点 | 适用场景 |
|------|------|----------|
| `osgb2shp.py` | 基于行列号计算，支持多种原点模式 | 规则瓦片布局，需要精确坐标计算 |
| `osgb2shp_original_coords.py` | 基于文件夹名称提取坐标，自动合并多边形 | 任意瓦片布局，需要快速提取整体边界 |

### 依赖包

该工具依赖以下Python包：

- `geopandas` - 用于地理数据处理和Shapefile保存
- `shapely` - 用于多边形几何操作
- `lxml` - 用于XML文件解析
- `fiona` - 用于Shapefile读写（geopandas的依赖）
- `pyproj` - 用于坐标系统转换（geopandas的依赖）

### 安装方法

#### 在线安装

```bash
pip install  -r requirements.txt
```


## 使用方法

### 标准版工具 (`osgb2shp.py`)

```bash
# 基本用法
python osgb2shp.py --input /path/to/osgb --output output.shp

# 指定坐标系统
python osgb2shp.py --input /path/to/osgb --output output.shp --epsg 4326

# 使用原点作为最大坐标
python osgb2shp.py --input /path/to/osgb --output output.shp --origin-is-max
```

### 原始坐标版工具 (`osgb2shp_original_coords.py`)

```bash
# 基本用法
python osgb2shp_original_coords.py --input /path/to/osgb --output output.shp

# 指定输出坐标系统
python osgb2shp_original_coords.py --input /path/to/osgb --output output.shp --output-epsg 3857
```

## 参数说明

### 通用参数

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | `-i` | `Data` | OSGB数据输入路径 |
| `--output` | `-o` | 自动生成 | 输出Shapefile路径和名称 |
| `--epsg` | `-e` | `4326` | 输入坐标系统EPSG代码 |
| `--output-epsg` | `-oe` | 与输入相同 | 输出坐标系统EPSG代码 |

### 标准版特有参数

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--origin-is-max` | `-om` | `False` | 将原点视为最大坐标（默认原点为最小坐标） |

## 输入数据格式

### OSGB数据结构

工具支持以下OSGB数据结构：

```
OSGB_project/
├── metadata.xml          # 包含坐标系统和原点信息
└── Data/                 # 瓦片数据文件夹
    ├── Tile_+001_+001/   # 瓦片文件夹（列1，行1）
    │   ├── *.osgb        # OSGB瓦片文件
    │   └── ...
    ├── Tile_+001_+002/   # 瓦片文件夹（列1，行2）
    │   ├── *.osgb
    │   └── ...
    └── ...
```

### metadata.xml格式

metadata.xml文件应包含坐标系统和原点信息：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<OSGBMetadata>
    <SRS>EPSG:4544</SRS>
    <Origin>380812.0, 4040114.0, 1820.000000</Origin>
    <!-- 其他元数据 -->
</OSGBMetadata>
```

## 输出结果

### 输出文件结构

执行命令后，会在当前目录创建一个与输出文件名同名的文件夹：

```
output_name/
├── output_name.shp       # Shapefile主文件
├── output_name.shx       # 空间索引文件
├── output_name.dbf       # 属性数据表
├── output_name.prj       # 坐标系统文件
└── output_name_report.txt # 处理报告文件
```

### 报告文件内容

报告文件包含以下信息：

- 输入输出路径
- 坐标系统信息
- 处理瓦片数量
- 多边形数量
- 瓦片分割级别（标准版）
- 边界范围（最小/最大X/Y坐标、宽度、高度）

## 常见问题及解决方案

### 1. 找不到metadata.xml文件

**问题**：工具无法找到metadata.xml文件，无法读取坐标系统和原点信息。

**解决方案**：
- 确保OSGB数据文件夹中包含metadata.xml文件
- 检查文件路径是否正确，工具会自动搜索子文件夹中的metadata.xml
- 如果确实没有metadata.xml文件，使用`--epsg`参数手动指定坐标系统

### 2. 瓦片文件夹名称格式不正确

**问题**：瓦片文件夹名称格式不符合预期，无法提取坐标信息。

**解决方案**：
- 确保瓦片文件夹名称格式为`Tile_+xxx_+yyy`格式
- 检查文件夹名称中的数字部分是否为纯数字

### 3. 坐标系统转换失败

**问题**：指定的EPSG代码无效或不支持坐标转换。

**解决方案**：
- 确保使用有效的EPSG代码
- 检查输入输出坐标系统是否都支持转换
- 如果不确定EPSG代码，不使用`--output-epsg`参数，保持与输入相同的坐标系统

### 4. 输出Shapefile无法在GIS软件中打开

**问题**：生成的Shapefile无法在ArcGIS、QGIS等软件中打开。

**解决方案**：
- 检查坐标系统设置是否正确
- 确保输出文件夹具有写入权限
- 尝试使用不同的输出文件名

## 性能优化

### 处理大型数据集

对于包含大量瓦片的大型OSGB数据集：
- 工具会自动批量处理瓦片，每处理10个瓦片显示一次进度
- 多边形合并操作可能会占用较多内存，建议在具有足够内存的系统上运行
- 对于特别大的数据集，可以考虑分批处理

### 提高处理速度

- 确保输入路径直接指向包含瓦片文件夹的目录，减少搜索时间
- 使用SSD存储可以显著提高文件读写速度
- 关闭不必要的后台程序，释放系统资源

## 使用示例

### 示例1：提取标准OSGB边界

```bash
# 从标准OSGB数据中提取边界，使用默认参数
python osgb2shp.py --input /data/city_model --output city_boundary.shp
```

### 示例2：提取并转换坐标系统

```bash
# 提取边界并转换到Web墨卡托投影
python osgb2shp.py --input /data/city_model --output city_boundary_webmerc.shp --epsg 4326 --output-epsg 3857
```

### 示例3：使用原始坐标提取并合并多边形

```bash
# 使用原始坐标提取并自动合并多边形
python osgb2shp_original_coords.py --input /data/city_model --output city_boundary_merged.shp
```

## 项目结构

```
OSGB_boundary_extractor/
├── osgb2shp.py                  # 标准版OSGB边界提取工具
├── osgb2shp_original_coords.py  # 原始坐标版OSGB边界提取工具
├── README.md                    # 项目说明文档
├── LICENSE                      # MIT许可证文件
└── .gitignore                   # Git忽略文件
```

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 联系方式

如有问题或建议，请通过以下方式联系：

- GitHub Issues: https://github.com/changchunchieh/osgb-boundary-extractor/issues
- Email: changchunchieh@163.com

---
**© changchunchieh 2026-02-03**
**最后更新时间：2026-02-03**
