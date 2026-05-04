import json
from ezdxf.document import Drawing
from ezdxf.tools.text import plain_mtext
from typing import Dict, Any, Optional


class TextExtractor:
    """文本提取模块 - 从DWG中提取所有可翻译文本"""
    
    def __init__(self, doc: Optional[Drawing] = None):
        self.doc = doc
        self.bundles: Dict[str, Dict[str, Any]] = {}
    
    def set_document(self, doc: Drawing):
        self.doc = doc
        self.bundles.clear()
    
    def _add_entity(self, entity, container: str):
        """提取单个实体的文本"""
        dxftype = entity.dxftype()
        
        if dxftype == 'TEXT':
            content = entity.dxf.text
            if content and content.strip():
                self.bundles[entity.dxf.handle] = {
                    'handle': entity.dxf.handle,
                    'content': content,
                    'type': 'TEXT',
                    'container': container,
                    'entity': entity
                }
        
        elif dxftype == 'MTEXT':
            content = entity.text
            if content and content.strip():
                self.bundles[entity.dxf.handle] = {
                    'handle': entity.dxf.handle,
                    'content': content,
                    'plain_content': plain_mtext(content),
                    'type': 'MTEXT',
                    'container': container,
                    'entity': entity
                }
        
        elif dxftype == 'INSERT':
            for attr in entity.attribs:
                content = attr.dxf.text
                if content and content.strip():
                    self.bundles[attr.dxf.handle] = {
                        'handle': attr.dxf.handle,
                        'content': content,
                        'type': 'ATTRIB',
                        'container': f"{container} -> INSERT({entity.dxf.name})",
                        'entity': attr,
                        'block_name': entity.dxf.name
                    }
    
    def extract(self) -> Dict[str, Dict[str, Any]]:
        """执行完整文本提取"""
        if not self.doc:
            raise ValueError("未设置Document对象")
        
        print("开始提取文本...")
        
        for layout in self.doc.layouts:
            container_name = layout.name if layout.name.lower() != 'model' else 'ModelSpace'
            for entity in layout:
                self._add_entity(entity, container_name)
        
        for block in self.doc.blocks:
            # 不跳过匿名块(*U开头)，因为它们可能包含标题栏、版权信息等需要翻译的文本
            # 只跳过系统定义的块
            if not block.name.startswith('*MODEL') and not block.name.startswith('*PAPER'):
                for entity in block:
                    self._add_entity(entity, f"Block({block.name})")
        
        print(f"共提取 {len(self.bundles)} 条文本")
        return self.bundles
    
    def get_bundles(self) -> Dict[str, Dict[str, Any]]:
        return self.bundles
    
    def export_json(self, json_path: str, include_entity: bool = False):
        """导出提取的文本到JSON"""
        export_data = {}
        for handle, data in self.bundles.items():
            export_data[handle] = {k: v for k, v in data.items() 
                                  if include_entity or k != 'entity'}
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"已导出到: {json_path}")
