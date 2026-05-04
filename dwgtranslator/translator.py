from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class TranslationEngine(ABC):
    """翻译引擎基类 - 所有翻译实现必须继承此类"""
    
    name: str = "base"
    
    def __init__(self, **kwargs):
        self.config = kwargs
    
    @abstractmethod
    def translate(self, text: str, from_lang: str = 'auto', to_lang: str = 'zh') -> str:
        """翻译单条文本"""
        pass
    
    def batch_translate(self, texts: List[str], from_lang: str = 'auto', 
                       to_lang: str = 'zh') -> List[str]:
        """批量翻译 - 默认逐条调用"""
        return [self.translate(t, from_lang, to_lang) for t in texts]
    
    def supports_batch(self) -> bool:
        """是否支持批量翻译"""
        return False
    
    @classmethod
    def get_engine_name(cls) -> str:
        return cls.name


class MockTranslator(TranslationEngine):
    """模拟翻译引擎 - 用于测试"""
    
    name: str = "mock"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.translations = kwargs.get('translations', {
            "前视图": "Front View",
            "后视图": "Back View",
            "左视图": "Left View",
            "右视图": "Right View",
            "俯视图": "Top View",
            "仰视图": "Bottom View",
            "剖视图": "Section View",
            "技术要求": "Technical Requirements",
            "材料": "Material",
            "尺寸": "Dimension",
            "比例": "Scale",
            "重量": "Weight",
            "数量": "Quantity",
            "备注": "Remarks",
            "图纸": "Drawing",
            "Front View": "前视图",
            "Back View": "后视图",
            "Left View": "左视图",
            "Right View": "右视图",
            "Top View": "俯视图",
            "Bottom View": "仰视图",
            "Section View": "剖视图",
            "Technical Requirements": "技术要求",
            "Material": "材料",
            "Dimension": "尺寸",
            "Scale": "比例",
            "Weight": "重量",
            "Quantity": "数量",
            "Remarks": "备注",
            "Drawing": "图纸",
        })
        self.prefix = kwargs.get('prefix', '')
    
    def translate(self, text: str, from_lang: str = 'auto', to_lang: str = 'zh') -> str:
        if text in self.translations:
            result = self.translations[text]
            return result if result else f"{self.prefix}{text}"
        return f"{self.prefix}{text}"


class TranslationEngineFactory:
    """翻译引擎工厂 - 管理注册的翻译实现"""
    
    _engines: Dict[str, type] = {}
    
    @classmethod
    def register(cls, engine_class: type):
        """注册翻译引擎"""
        if issubclass(engine_class, TranslationEngine):
            cls._engines[engine_class.get_engine_name()] = engine_class
    
    @classmethod
    def create(cls, engine_name: str, **kwargs) -> TranslationEngine:
        """创建翻译引擎实例"""
        engine_class = cls._engines.get(engine_name)
        if not engine_class:
            raise ValueError(f"未知的翻译引擎: {engine_name}, 可用: {list(cls._engines.keys())}")
        return engine_class(**kwargs)
    
    @classmethod
    def list_engines(cls) -> List[str]:
        """列出所有可用的翻译引擎"""
        return list(cls._engines.keys())


TranslationEngineFactory.register(MockTranslator)
