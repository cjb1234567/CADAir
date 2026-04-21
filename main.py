import json
import ezdxf
import os
from ezdxf.addons import odafc
# 确保你系统路径里有 OdaFileConverter，或者手动指定路径：
oda_path = r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe"
# odafc.unix_exec_path = "/usr/bin/ODAFileConverter"
if not os.path.exists(oda_path):
    print(f"错误：在指定路径找不到文件！请检查版本号是否正确：\n{oda_path}")
else:
    # 注入路径到 ezdxf.options（新版 ezdxf 从这里读取）
    ezdxf.options.set("odafc-addon", "win_exec_path", oda_path)
    print("ODA 路径设置成功。")

def dwg_to_json(dwg_path, json_path):
    # 1. 使用 odafc 将 DWG 读入为 ezdxf 的 Document 对象
    # 注意：odafc.readfile 会在后台调用 ODA File Converter 产生临时 DXF 并读取
    try:
        print(f"正在转换并读取 DWG: {dwg_path}")
        doc = odafc.readfile(dwg_path)
    except Exception as e:
        print(f"转换失败: {e}")
        return

    # 2. 准备数据容器
    cad_data = {
        "header": {
            "version": doc.dxfversion,
            "units": doc.header.get('$INSUNITS', 0) # 0 为无单位
        },
        "entities": []
    }

    # 3. 遍历模型空间中的实体
    msp = doc.modelspace()
    for entity in msp:
        # 提取基础通用属性
        base_info = {
            "type": entity.dxftype(),
            "layer": entity.dxf.layer,
            "color": entity.dxf.color,
            "handle": entity.dxf.handle
        }

        # 根据不同实体类型提取特定几何数据
        if entity.dxftype() == 'LINE':
            base_info.update({
                "start": entity.dxf.start, # 返回 Vector(x, y, z)
                "end": entity.dxf.end
            })
        
        elif entity.dxftype() == 'CIRCLE':
            base_info.update({
                "center": entity.dxf.center,
                "radius": entity.dxf.radius
            })

        elif entity.dxftype() == 'TEXT':
            base_info.update({
                "content": entity.dxf.text,
                "insert": entity.dxf.insert,
                "height": entity.dxf.height
            })

        elif entity.dxftype() == 'LWPOLYLINE':
            # 多段线包含多个顶点
            base_info.update({
                "vertices": [v for v in entity.get_points()] # (x, y, start_width, end_width, bulge)
            })

        cad_data["entities"].append(base_info)

    # 4. 写入 JSON 文件
    # 使用 default=str 是因为 ezdxf 的 Vector 对象需要转换为字符串或列表
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(cad_data, f, indent=4, default=lambda x: list(x) if hasattr(x, '__iter__') else str(x))

    print(f"成功导出 JSON 至: {json_path}")






if __name__ == "__main__":
    
    dwg_to_json("your_design.dwg", "output.json")
