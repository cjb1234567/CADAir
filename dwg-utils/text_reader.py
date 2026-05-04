import ezdxf
import os
from ezdxf.addons import odafc
from ezdxf.document import Drawing
from collections import Counter

class DWGReader:
    def __init__(self, oda_path=None):
        if not oda_path:
            # odafc.unix_exec_path = "/usr/bin/ODAFileConverter"
            oda_path = r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
        elif not os.path.exists(oda_path):
            raise FileNotFoundError(f"在指定路径找不到文件！请检查版本号是否正确：\n{oda_path}")
        # 注入路径到 ezdxf.options（新版 ezdxf 从这里读取）
        ezdxf.options.set("odafc-addon", "win_exec_path", oda_path)
        print("ODA 路径设置成功。")

    def read_dwg(self, dwg_path):
        # 注意：odafc.readfile 会在后台调用 ODA File Converter 产生临时 DXF 并读取
        try:
            print(f"正在转换并读取 DWG: {dwg_path}")
            doc = odafc.readfile(dwg_path)
            return doc
        except IOError:
            print(f"无法打开文件: {dwg_path}")
        except ezdxf.DXFStructureError:
            print(f"无效的 DXF 文件结构")
        except Exception as e:
            print(f"转换失败: {e}")
            return None


def list_all_entity_types(doc: Drawing):
    try:
        # 定义一个计数器
        entity_counts = Counter()

        # 1. 统计模型空间 (Modelspace)
        msp = doc.modelspace()
        for entity in msp:
            entity_counts[entity.dxftype()] += 1

        # 2. 统计所有布局空间 (Paperspace / Layouts)
        for layout in doc.layouts:
            # 排除已经统计过的模型空间
            if layout.name.lower() != 'model':
                for entity in layout:
                    entity_counts[entity.dxftype()] += 1

        # 打印结果
        print(f"文件中各实体类型及其数量:")
        print("-" * 30)
        for e_type, count in entity_counts.most_common():
            print(f"{e_type:<15} : {count} 个")

        return entity_counts

    except Exception as e:
        print(f"处理文件时出错: {e}")

def get_all_text_nodes(doc: Drawing):
    try:
        # 加载 DXF 文件
        msp = doc.modelspace()

        text_data = []

        # 遍历模型空间中的所有实体
        for entity in msp:
            # 检查是否为 TEXT (单行文字)
            if entity.dxftype() == 'TEXT':
                text_data.append({
                    'type': 'TEXT',
                    'content': entity.dxf.text,
                    'insert': entity.dxf.insert, # 插入点坐标
                })

            # 检查是否为 MTEXT (多行文字)
            elif entity.dxftype() == 'MTEXT':
                # MTEXT 的内容通过 .text 属性获取，ezdxf 会处理分段内容
                text_data.append({
                    'type': 'MTEXT',
                    'content': entity.text,
                    'insert': entity.dxf.insert,
                })

        return text_data

    except Exception as e:
        print(f"读取失败: {e}")
        return None


def get_text_nodes_by_container(doc: Drawing):
    try:
        results = []
        # 1. 定义一个提取函数
        def extract_from_layout(layout, container_name):
            for entity in layout:
                # 处理基础文字
                if entity.dxftype() in ('TEXT', 'MTEXT'):
                    content = entity.dxf.text if entity.dxftype() == 'TEXT' else entity.text
                    results.append({
                        'content': content,
                        'container': container_name, # 记录它所在的容器
                        'type': entity.dxftype(),
                        'handle': entity.dxf.handle # 唯一身份证号
                    })

                # 处理块引用 (INSERT) 携带的属性
                elif entity.dxftype() == 'INSERT':
                    for attr in entity.attribs:
                        results.append({
                            'content': attr.dxf.text,
                            'container': f"INSERT_ATTRIB (Block: {entity.dxf.name})",
                            'type': 'ATTRIB',
                            'handle': attr.dxf.handle
                        })

        # 2. 扫描模型空间 (直属节点)
        extract_from_layout(doc.modelspace(), "ModelSpace")

        # 3. 扫描所有块定义 (内部节点)
        # 这一步会列出所有在块编辑器里定义的文字
        for block in doc.blocks:
            # 过滤掉系统自动生成的匿名块（如 *Model_Space）以防重复
            if not block.name.startswith('*'):
                extract_from_layout(block, f"Block Definition: {block.name}")

        return results

    except Exception as e:
        print(f"发生错误: {e}")
        return []

def extract_translation_bundles(doc: Drawing):
    # 存储结构: { handle: "original_text" }
    translation_map = {}

    def add_to_map(entity):
        if entity.dxftype() in ('TEXT', 'MTEXT'):
            # MTEXT 需要注意其包含格式代码，text 属性会自动处理
            content = entity.dxf.text if entity.dxftype() == 'TEXT' else entity.text
            if content.strip():
                translation_map[entity.dxf.handle] = content

        # 处理 INSERT 的属性 (ATTRIB)
        if entity.dxftype() == 'INSERT':
            for attr in entity.attribs:
                if attr.dxf.text.strip():
                    translation_map[attr.dxf.handle] = attr.dxf.text

    # 1. 遍历所有空间 (Model & Layouts)
    for layout in doc.layouts:
        for entity in layout:
            add_to_map(entity)

    # 2. 遍历所有块定义 (内部静态文字)
    for block in doc.blocks:
        if not block.name.startswith('*'): # 排除系统匿名块
            for entity in block:
                if entity.dxftype() in ('TEXT', 'MTEXT'):
                    content = entity.dxf.text if entity.dxftype() == 'TEXT' else entity.text
                    if content.strip():
                        translation_map[entity.dxf.handle] = content

    return doc, translation_map


# 使用示例
reader = DWGReader()
doc = reader.read_dwg("20260123.dwg")
cnt = list_all_entity_types(doc)


results = get_text_nodes_by_container(doc)
# 打印前10条结果查看
print(f"共找到 {len(results)} 条文字信息：")
for item in results:
    print(f"内容: {item['content']} | 位置: {item['container']} | 类型: {item['type']}")
