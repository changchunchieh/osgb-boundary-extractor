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


def extract_osgb_boundary_original_coords(osgb_folder, output_path, epsg_id, output_epsg=None):
    """
    使用原始坐标提取OSGB边界，然后基于XML原点进行移动
    适用于有规则瓦片的OSGB数据
    
    参数:
    - osgb_folder: OSGB数据文件夹路径
    - output_path: 输出Shapefile路径
    - epsg_id: 输入坐标系统EPSG代码
    - output_epsg: 输出坐标系统EPSG代码（可选）
    """
    boundary_polygons = []
    processed_tiles = 0
    
    print('正在初始化处理...')
    
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
    
    # 5. 处理瓦片 - 使用原始坐标，不计算行列号
    # 从瓦片文件夹名称中提取坐标信息
    print('从瓦片文件夹名称提取原始坐标...')
    

    
    for i, tile_folder in enumerate(tile_folders):
        tile_path = os.path.join(tile_data_folder, tile_folder)
        if os.path.isdir(tile_path):
            try:
                # 直接从瓦片文件夹名称提取原始坐标信息
                # 解析瓦片文件夹名称，格式可能为 Tile_+xxx_+yyy
                tile_info = tile_folder.split('_')[1:]
                if len(tile_info) >= 2:
                    # 提取原始坐标值
                    x_str = tile_info[0].replace('+', '')
                    y_str = tile_info[1].replace('+', '')
                    
                    # 转换为整数作为原始坐标
                    original_x = int(x_str)
                    original_y = int(y_str)
                    
                    # 创建基于原始坐标的瓦片多边形
                    # 这里不使用单位距离，而是直接使用原始坐标作为偏移量
                    # 假设瓦片大小为固定值（根据实际数据调整）
                    tile_size = 1000.0  # 调整为更大的瓦片大小
                    
                    min_x = original_x
                    min_y = original_y
                    max_x = original_x + 1
                    max_y = original_y + 1
                    
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
            except ValueError as e:
                print(f'处理瓦片文件夹 {tile_folder} 时出错: {e}')
                pass
    
    # 6. 使用所有多边形
    if boundary_polygons:
        print(f'瓦片处理完成，共处理 {processed_tiles} 个瓦片')
        
        # 7. 基于XML原点进行坐标移动
        if srs_origin:
            print(f'从metadata.xml读取到原点坐标: {srs_origin}')
            print('基于原点坐标进行瓦片移动...')
            
            # 移动所有多边形到原点位置
            moved_polygons = []
            for polygon in boundary_polygons:
                # 计算多边形的边界框
                min_x, min_y, max_x, max_y = polygon.bounds
                
                # 计算移动偏移量
                # 将瓦片移动到原点位置，使用原始坐标作为偏移量
                # 这里假设原始坐标是从0开始的索引，需要乘以一个缩放因子
                scale_factor = 100.0  # 缩放因子，根据实际数据调整
                
                offset_x = srs_origin[0] + (min_x * scale_factor)
                offset_y = srs_origin[1] + (min_y * scale_factor)
                tile_width = (max_x - min_x) * scale_factor
                tile_height = (max_y - min_y) * scale_factor
                
                # 创建移动后的多边形
                moved_polygon = Polygon([
                    (offset_x, offset_y),
                    (offset_x + tile_width, offset_y),
                    (offset_x + tile_width, offset_y + tile_height),
                    (offset_x, offset_y + tile_height)
                ])
                moved_polygons.append(moved_polygon)
            
            boundary_polygons = moved_polygons
            print('瓦片移动完成!')
        else:
            print('未找到metadata.xml中的原点坐标，使用原始坐标...')
        
        # 8. 合并所有多边形为一个
        print('正在合并所有多边形为一个...')
        merged_polygon = unary_union(boundary_polygons)
        print('多边形合并完成!')
        
        # 9. 创建输出文件夹
        print('正在创建输出文件夹...')
        output_folder = os.path.splitext(output_path)[0]
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f'创建输出文件夹: {output_folder}')
        
        # 10. 创建并保存
        print('正在创建并保存GeoDataFrame...')
        output_file = os.path.join(output_folder, os.path.basename(output_path))
        
        # 确保坐标系统设置正确
        crs_input = f'EPSG:{input_crs}'
        print(f'设置输入坐标系统: {crs_input}')
        
        # 创建包含合并多边形的GeoDataFrame
        gdf = gpd.GeoDataFrame(
            {'id': [1], 'name': ['merged_boundary']},
            geometry=[merged_polygon],
            crs=crs_input
        )
        
        # 10. 如果输出坐标系统不同，进行坐标转换
        if output_crs != input_crs:
            crs_output = f'EPSG:{output_crs}'
            print(f'正在进行坐标转换，从EPSG:{input_crs}到EPSG:{output_crs}...')
            print(f'转换前坐标范围: {gdf.total_bounds}')
            gdf = gdf.to_crs(crs_output)
            print(f'转换后坐标范围: {gdf.total_bounds}')
        
        print(f'正在保存Shapefile: {output_file}')
        gdf.to_file(output_file)
        
        # 11. 生成报告
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
            f.write(f'合并前多边形数: {len(boundary_polygons)}\n')
            f.write(f'合并后多边形数: 1\n')
            if srs_origin:
                f.write(f'使用的原点坐标: {srs_origin}\n')
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
    parser = argparse.ArgumentParser(description='OSGB边界提取工具（使用原始坐标）')
    parser.add_argument('--input', '-i', default='Data', help='OSGB数据输入路径')
    parser.add_argument('--output', '-o', default='osgb_boundary_original.shp', help='输出shapefile路径和名称')
    parser.add_argument('--epsg', '-e', type=int, default=4326, help='输入坐标系统EPSG ID')
    parser.add_argument('--output-epsg', '-oe', type=int, help='输出坐标系统EPSG ID，默认使用输入坐标系统')
    args = parser.parse_args()
    
    print(f'开始提取OSGB边界...')
    print(f'输入路径: {args.input}')
    print(f'输出路径: {args.output}')
    print(f'输入坐标系统: EPSG:{args.epsg}')
    if args.output_epsg:
        print(f'输出坐标系统: EPSG:{args.output_epsg}')
    else:
        print(f'输出坐标系统: 与输入相同')
    
    gdf, report = extract_osgb_boundary_original_coords(args.input, args.output, args.epsg, args.output_epsg)
    
    print('\n提取完成!')
    print(f'生成文件: {os.path.splitext(args.output)[0]} 文件夹')
    print(f'生成报告: {report}')
