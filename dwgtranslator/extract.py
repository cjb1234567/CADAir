import json
from ezdxf.document import Drawing
from ezdxf.tools.text import plain_mtext
from typing import Dict, Any, Optional
from .writeback import detect_dxf_encoding


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
        
        elif dxftype == 'MULTILEADER':
            try:
                if entity.has_mtext:
                    mtext = entity.mtext
                    content = mtext.text
                    if content and content.strip():
                        self.bundles[entity.dxf.handle] = {
                            'handle': entity.dxf.handle,
                            'content': content,
                            'plain_content': plain_mtext(content),
                            'type': 'MULTILEADER',
                            'container': container,
                            'entity': entity
                        }
            except Exception:
                pass
    
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

    def extract_raw_multileaders(self, dxf_path: str) -> int:
        """从原始DXF文本补充提取MULTILEADER，避免ezdxf丢失复杂实体。"""
        encoding = detect_dxf_encoding(dxf_path)
        with open(dxf_path, 'r', encoding=encoding, errors='surrogateescape', newline='') as f:
            lines = f.readlines()

        added = 0
        for start, end in self._raw_entity_ranges(lines):
            if self._line_value(lines, start) != 'MULTILEADER':
                continue

            handle = None
            content = None
            for i in range(start + 2, end - 1):
                code = lines[i].strip()
                value = lines[i + 1].rstrip('\r\n')
                if code == '5' and handle is None:
                    handle = value.strip()
                elif code == '304' and content is None and value.strip():
                    content = value

            if not handle or not content or handle in self.bundles:
                continue

            self.bundles[handle] = {
                'handle': handle,
                'content': content,
                'plain_content': plain_mtext(content),
                'type': 'MULTILEADER',
                'container': 'RawDXF',
                'raw_dxf': True
            }
            added += 1

        if added:
            print(f"从原始DXF补充提取 MULTILEADER {added} 条")
        return added

    def _raw_entity_ranges(self, lines):
        start = None
        for i in range(0, len(lines) - 1, 2):
            if lines[i].strip() == '0':
                if start is not None:
                    yield start, i
                start = i
        if start is not None:
            yield start, len(lines)

    def _line_value(self, lines, index: int) -> str:
        if index + 1 >= len(lines):
            return ''
        return lines[index + 1].strip()
