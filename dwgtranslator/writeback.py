import json
from ezdxf.document import Drawing
from typing import Dict, Any, Optional


class TextWriter:
    """文本写回模块 - 将翻译后的文本写回DWG"""
    
    def __init__(self, doc: Optional[Drawing] = None):
        self.doc = doc
        self.translated_bundles: Dict[str, Dict[str, Any]] = {}
    
    def set_document(self, doc: Drawing):
        self.doc = doc
    
    def load_translated(self, bundles: Dict[str, Dict[str, Any]]):
        """加载翻译后的bundle数据"""
        self.translated_bundles = bundles
    
    def load_from_json(self, json_path: str):
        """从JSON文件加载翻译结果"""
        with open(json_path, 'r', encoding='utf-8') as f:
            self.translated_bundles = json.load(f)
    
    def _write_entity(self, handle: str, data: Dict[str, Any]) -> bool:
        """写回单个实体的翻译文本"""
        try:
            translated_text = data.get('translated') or data.get('content')
            if not translated_text:
                return False
            
            entity = data.get('entity')
            if not entity and self.doc:
                entity = self.doc.entitydb.get(handle)
            
            if not entity:
                return False
            
            dxftype = entity.dxftype()
            
            if dxftype == 'TEXT':
                entity.dxf.text = translated_text
                original_len = len(data.get('content', ''))
                if len(translated_text) > original_len and hasattr(entity.dxf, 'width'):
                    entity.dxf.width = entity.dxf.width * 0.9
            
            elif dxftype == 'MTEXT':
                entity.text = translated_text
            
            elif dxftype == 'ATTRIB':
                entity.dxf.text = translated_text
            
            return True
            
        except Exception as e:
            print(f"写回失败 [{handle}]: {e}")
            return False
    
    def write_all(self) -> int:
        """写回所有翻译文本"""
        if not self.translated_bundles:
            print("没有翻译数据可写回")
            return 0
        
        print("开始写回翻译文本...")
        success = 0
        
        for handle, data in self.translated_bundles.items():
            if self._write_entity(handle, data):
                success += 1
        
        print(f"成功写回 {success}/{len(self.translated_bundles)} 条文本")
        return success
