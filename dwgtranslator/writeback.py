import json
import os
import re
from ezdxf.document import Drawing
from typing import Dict, Any, Optional


DXF_CODEPAGE_ENCODINGS = {
    'ANSI_874': 'cp874',
    'ANSI_932': 'cp932',
    'ANSI_936': 'gbk',
    'ANSI_949': 'cp949',
    'ANSI_950': 'cp950',
    'ANSI_1250': 'cp1250',
    'ANSI_1251': 'cp1251',
    'ANSI_1252': 'cp1252',
    'ANSI_1253': 'cp1253',
    'ANSI_1254': 'cp1254',
    'ANSI_1255': 'cp1255',
    'ANSI_1256': 'cp1256',
    'ANSI_1257': 'cp1257',
    'ANSI_1258': 'cp1258',
}

UTF8_DXF_VERSIONS = {
    'AC1021',  # R2007
    'AC1024',  # R2010
    'AC1027',  # R2013
    'AC1032',  # R2018
}


def detect_dxf_encoding(source_path: str) -> str:
    """Detect DXF text encoding from ACADVER/DWGCODEPAGE without parsing the full file."""
    acadver = None
    codepage = None

    with open(source_path, 'r', encoding='ascii', errors='ignore', newline='') as f:
        lines = []
        for _ in range(1200):
            line = f.readline()
            if not line:
                break
            lines.append(line.strip())

    for i, value in enumerate(lines[:-2]):
        if value == '$ACADVER':
            acadver = lines[i + 2].upper()
        elif value == '$DWGCODEPAGE':
            codepage = lines[i + 2].upper()

        if acadver and codepage:
            break

    if acadver in UTF8_DXF_VERSIONS:
        return 'utf-8'
    return DXF_CODEPAGE_ENCODINGS.get(codepage or '', 'cp1252')


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
            
            elif dxftype == 'MULTILEADER':
                try:
                    if entity.has_mtext:
                        entity.mtext.text = translated_text
                except Exception:
                    pass
            
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

    def _detect_dxf_encoding(self, source_path: str) -> str:
        return detect_dxf_encoding(source_path)

    def patch_dxf_file(self, source_path: str, output_path: str) -> int:
        """直接修改DXF文本，不通过ezdxf重新保存整个文件。"""
        if not self.translated_bundles:
            print("没有翻译数据可写回")
            return 0

        encoding = self._detect_dxf_encoding(source_path)
        with open(source_path, 'r', encoding=encoding, errors='surrogateescape', newline='') as f:
            lines = f.readlines()

        entity_ranges = self._index_entity_ranges(lines)
        success = 0

        for handle, data in self.translated_bundles.items():
            entity_range = entity_ranges.get(str(handle).upper())
            if not entity_range:
                continue

            if self._patch_entity_lines(lines, entity_range, data):
                success += 1

        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding=encoding, errors='surrogateescape', newline='') as f:
            f.writelines(lines)

        print(f"成功直接补丁写回 {success}/{len(self.translated_bundles)} 条文本")
        return success

    def _index_entity_ranges(self, lines):
        ranges = {}
        current_start = None
        current_handle = None
        line_count = len(lines)

        for i in range(0, line_count - 1, 2):
            code = lines[i].strip()
            value = lines[i + 1].strip()

            if code == '0':
                if current_start is not None and current_handle:
                    ranges[current_handle] = (current_start, i)
                current_start = i
                current_handle = None
            elif current_start is not None and code == '5' and current_handle is None:
                current_handle = value.upper()

        if current_start is not None and current_handle:
            ranges[current_handle] = (current_start, line_count)

        return ranges

    def _patch_entity_lines(self, lines, entity_range, data: Dict[str, Any]) -> bool:
        translated_text = data.get('translated') or data.get('content')
        if not translated_text:
            return False

        start, end = entity_range
        entity_type = data.get('type')

        if entity_type in {'TEXT', 'ATTRIB'}:
            encoded = self._single_line_text(translated_text)
            return self._replace_first_group_value(lines, start, end, {'1'}, encoded)
        if entity_type == 'MTEXT':
            encoded = self._mtext_value(translated_text)
            return self._replace_first_group_value(lines, start, end, {'1'}, encoded)
        if entity_type == 'MULTILEADER':
            encoded = self._mtext_value(translated_text)
            return self._replace_first_group_value(lines, start, end, {'304'}, encoded)

        return False

    def _replace_first_group_value(self, lines, start: int, end: int, codes, value: str) -> bool:
        newline = '\r\n' if lines[start].endswith('\r\n') else '\n'
        for i in range(start, end - 1, 2):
            if lines[i].strip() in codes:
                lines[i + 1] = str(value) + newline
                return True
        return False

    def _single_line_text(self, value: str) -> str:
        return re.sub(r'[\r\n]+', ' ', str(value)).strip()

    def _mtext_value(self, value: str) -> str:
        return str(value).replace('\r\n', '\\P').replace('\r', '\\P').replace('\n', '\\P')
