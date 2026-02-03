import geopandas as gpd
from shapely.geometry import Polygon
from shapely.ops import unary_union
import os
import argparse
import xml.etree.ElementTree as ET
import re


def read_metadata_info(osgb_folder):
    """
    读取metadata.xml文件中的坐标系统和原点信息
    """
    metadata_path = os.path.join(osgb_folder, 'metadata.xml')
    if not os.path.exists(metadata_path):
        # 查找子目录中的metadata.xml
        for root, dirs, files in os.walk(osgb_folder):
            if 'metadata.xml' in files:
                metadata_path = os.path.join(root, 'metadata.xml')
                break
    
    if not os.path.exists(metadata_path):
        return None, None
    
    try:
        tree = ET.parse(metadata_path)
        root = tree.getroot()
        
        # 读取坐标系统
        epsg_code = None
        for elem in root.iter():
            if any(key in elem.tag.lower() for key in ['epsg', 'crs', 'srs']):
                text = elem.text
                if text:
                    match = re.search(r'epsg:?(\d+)', text.lower())
                    if match:
                        epsg_code = int(match.group(1))
                        break
        
        # 如果没有找到特定标签，检查所有元素的文本内容
        if not epsg_code:
            for elem in root.iter():
                text = elem.text
                if text:
                    match = re.search(r'epsg:?(\d+)', text.lower())
                    if match:
                        epsg_code = int(match.group(1))
                        break
        
        # 读取原点信息
        srs_origin = None
        for elem in root.iter():
            if 'origin' in elem.tag.lower():
                text = elem.text
                if text:
                    # 解析原点坐标
                    coords = text.split(',')
                    if len(coords) >= 2:
                        try:
                            x = float(coords[0].strip())
                            y = float(coords[1].strip())
                            srs_origin = (x, y)
                        except ValueError:
                            pass
        
        return epsg_code, srs_origin
    except Exception:
        return None, None






def extract_osgb_boundary(osgb_folder, output_path, epsg_id, output_epsg=None, origin_is_max=False):
    """
    通过解析OSGB瓦片结构提取实际边界
    适用于有规则瓦片的OSGB数据
    
    参数:
    - osgb_folder: OSGB数据文件夹路径
    - output_path: 输出Shapefile路径
    - epsg_id: 输入坐标系统EPSG代码
    - output_epsg: 输出坐标系统EPSG代码（可选）
    - origin_is_max: 是否将原点视为最大坐标（默认False，原点为最小坐标）
    """
    boundary_polygons = []
    processed_tiles = 0
    tile_pixel_size = None
    tile_level = None
    tile_resolution = None
    
    print('正在初始化处理...')
    if origin_is_max:
        print('使用原点作为最大坐标的计算模式')
    else:
        print('使用原点作为最小坐标的计算模式')
    
    # 1. 检查是否存在Data子文件夹
    data_folder = os.path.join(osgb_folder, 'Data')
    if os.path.exists(data_folder) and os.path.isdir(data_folder):
        tile_data_folder = data_folder
        print(f'检测到Data子文件夹: {tile_data_folder}')
    else:
        tile_data_folder = osgb_folder
        print(f'使用输入目录作为瓦片数据目录: {tile_data_folder}')
    
    # 2. 尝试从metadata.xml读取坐标系统和原点信息
    print('正在读取坐标系统信息...')
    metadata_epsg, srs_origin = read_metadata_info(osgb_folder)
    if metadata_epsg:
        input_crs = metadata_epsg
        crs_source = 'metadata.xml'
        print(f'从metadata.xml读取到坐标系统: EPSG:{input_crs}')
        if srs_origin:
            print(f'从metadata.xml读取到原点坐标: {srs_origin}')
    else:
        input_crs = epsg_id
        crs_source = 'user_input'
        print(f'使用用户指定的坐标系统: EPSG:{input_crs}')
    
    # 3. 确定输出坐标系统
    if output_epsg:
        output_crs = output_epsg
        output_crs_source = 'user_input'
        print(f'使用用户指定的输出坐标系统: EPSG:{output_crs}')
    else:
        output_crs = input_crs
        output_crs_source = 'same_as_input'
        print(f'使用与输入相同的输出坐标系统: EPSG:{output_crs}')
    
    # 4. 遍历所有瓦片文件夹
    print('正在遍历和处理瓦片文件夹...')
    total_tiles = 0
    tile_folders = []
    
    for tile_folder in os.listdir(tile_data_folder):
        if tile_folder.startswith('Tile_'):
            tile_folders.append(tile_folder)
    
    total_tiles = len(tile_folders)
    print(f'发现 {total_tiles} 个瓦片文件夹')
    
    # 设置默认瓦片大小（地理单位）
    tile_geo_size = 0.0002777777777777778  # 1/3600度，约30米精度
    print(f'使用固定瓦片大小: {tile_geo_size} 度')
    
    # 6. 处理瓦片
    for i, tile_folder in enumerate(tile_folders):
        tile_path = os.path.join(tile_data_folder, tile_folder)
        if os.path.isdir(tile_path):
            # 解析行列号
            tile_info = tile_folder.split('_')[1:]
            if len(tile_info) == 2:
                try:
                    # 解析行列号，处理带+号的情况，将行列号减1使其从0开始
                    col_str = tile_info[0].replace('+', '')
                    row_str = tile_info[1].replace('+', '')
                    col = int(col_str) - 1
                    row = int(row_str) - 1
                    
                    # 计算实际地理坐标
                    if srs_origin:
                        if origin_is_max:
                            # 原点作为最大坐标
                            max_x = srs_origin[0] - col * tile_geo_size
                            min_x = srs_origin[0] - (col + 1) * tile_geo_size
                            max_y = srs_origin[1] - row * tile_geo_size
                            min_y = srs_origin[1] - (row + 1) * tile_geo_size
                        else:
                            # 原点作为最小坐标
                            min_x = srs_origin[0] + col * tile_geo_size
                            max_x = srs_origin[0] + (col + 1) * tile_geo_size
                            min_y = srs_origin[1] + row * tile_geo_size
                            max_y = srs_origin[1] + (row + 1) * tile_geo_size
                    else:
                        # 不考虑原点偏移
                        min_x = col * tile_geo_size
                        max_x = (col + 1) * tile_geo_size
                        min_y = row * tile_geo_size
                        max_y = (row + 1) * tile_geo_size
                        
                        # 创建多边形
                        polygon = Polygon([
                            (min_x, min_y),
                            (max_x, min_y),
                            (max_x, max_y),
                            (min_x, max_y)
                        ])
                        boundary_polygons.append(polygon)
                        processed_tiles += 1
                        
                        # 每处理10个瓦片显示一次进度
                        if (i + 1) % 10 == 0:
                            print(f'已处理 {i + 1}/{total_tiles} 个瓦片')
                except ValueError:
                    pass
    
    # 6. 直接使用所有多边形，不合并
    if boundary_polygons:
        print(f'瓦片处理完成，共处理 {processed_tiles} 个瓦片')
        print('保留所有原始瓦片多边形...')
        
        # 7. 创建输出文件夹
        print('正在创建输出文件夹...')
        output_folder = os.path.splitext(output_path)[0]
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f'创建输出文件夹: {output_folder}')
        
        # 8. 创建并保存
        print('正在创建并保存GeoDataFrame...')
        output_file = os.path.join(output_folder, os.path.basename(output_path))
        
        # 确保坐标系统设置正确
        crs_input = f'EPSG:{input_crs}'
        print(f'设置输入坐标系统: {crs_input}')
        
        # 创建包含所有原始瓦片多边形的GeoDataFrame
        gdf = gpd.GeoDataFrame(
            {'id': range(1, len(boundary_polygons) + 1), 'name': ['tile'] * len(boundary_polygons)},
            geometry=boundary_polygons,
            crs=crs_input
        )
        
        # 9. 如果输出坐标系统不同，进行坐标转换
        if output_crs != input_crs:
            crs_output = f'EPSG:{output_crs}'
            print(f'正在进行坐标转换，从EPSG:{input_crs}到EPSG:{output_crs}...')
            print(f'转换前坐标范围: {gdf.total_bounds}')
            gdf = gdf.to_crs(crs_output)
            print(f'转换后坐标范围: {gdf.total_bounds}')
        
        print(f'正在保存Shapefile: {output_file}')
        gdf.to_file(output_file)
        
        # 10. 生成报告
        print('正在生成报告文件...')
        report_path = os.path.join(output_folder, f'{os.path.splitext(os.path.basename(output_path))[0]}_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('OSGB边界提取报告\n')
            f.write('=' * 50 + '\n')
            f.write(f'输入路径: {osgb_folder}\n')
            f.write(f'瓦片数据路径: {tile_data_folder}\n')
            f.write(f'输出路径: {output_file}\n')
            f.write(f'输入坐标系统: EPSG:{input_crs}\n')
            f.write(f'输入坐标系统来源: {crs_source}\n')
            f.write(f'输出坐标系统: EPSG:{output_crs}\n')
            f.write(f'输出坐标系统来源: {output_crs_source}\n')
            f.write(f'处理瓦片数: {processed_tiles}\n')
            f.write(f'生成多边形数: {len(boundary_polygons)}\n')
            f.write(f'瓦片大小: {tile_geo_size} 度\n')
            f.write('\n边界范围:\n')
            bounds = gdf.total_bounds
            f.write(f'最小X: {bounds[0]:.6f}\n')
            f.write(f'最小Y: {bounds[1]:.6f}\n')
            f.write(f'最大X: {bounds[2]:.6f}\n')
            f.write(f'最大Y: {bounds[3]:.6f}\n')
            f.write(f'宽度: {bounds[2] - bounds[0]:.6f}\n')
            f.write(f'高度: {bounds[3] - bounds[1]:.6f}\n')
            f.write('\n提取完成!\n')
        
        print('报告生成完成!')
        return gdf, report_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OSGB边界提取工具')
    parser.add_argument('--input', '-i', default='Data', help='OSGB数据输入路径')
    parser.add_argument('--output', '-o', default='osgb_boundary.shp', help='输出shapefile路径和名称')
    parser.add_argument('--epsg', '-e', type=int, default=4326, help='输入坐标系统EPSG ID')
    parser.add_argument('--output-epsg', '-oe', type=int, help='输出坐标系统EPSG ID，默认使用输入坐标系统')
    parser.add_argument('--origin-is-max', '-om', action='store_true', help='将原点视为最大坐标（默认原点为最小坐标）')
    args = parser.parse_args()
    
    print(f'开始提取OSGB边界...')
    print(f'输入路径: {args.input}')
    print(f'输出路径: {args.output}')
    print(f'输入坐标系统: EPSG:{args.epsg}')
    if args.output_epsg:
        print(f'输出坐标系统: EPSG:{args.output_epsg}')
    else:
        print(f'输出坐标系统: 与输入相同')
    print(f'原点模式: {"最大坐标" if args.origin_is_max else "最小坐标"}')
    
    gdf, report = extract_osgb_boundary(args.input, args.output, args.epsg, args.output_epsg, args.origin_is_max)
    
    print('\n提取完成!')
    print(f'生成文件: {os.path.splitext(args.output)[0]} 文件夹')
    print(f'生成报告: {report}')
