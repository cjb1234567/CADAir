import os
import sys
import subprocess
import ezdxf
from ezdxf.addons import odafc
from ezdxf.document import Drawing
from typing import Optional


class DWGCore:
    """DWG/DXF 核心读写模块"""
    
    def __init__(self, oda_path: str):
        if not oda_path:
            raise ValueError("必须指定ODA File Converter路径")
        
        self.oda_path = oda_path
        self._use_xvfb = False
        self._setup_oda()
    
    def _setup_oda(self):
        """配置ODA File Converter路径"""
        if os.path.exists(self.oda_path):
            if os.name == 'nt':
                ezdxf.options.set("odafc-addon", "win_exec_path", self.oda_path)
            else:
                ezdxf.options.set("odafc-addon", "lin_exec_path", self.oda_path)
                self._use_xvfb = self._check_needs_xvfb()
                os.environ['XDG_RUNTIME_DIR'] = '/tmp/runtime-chongjibo'
                os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
                os.makedirs('/tmp/runtime-chongjibo', exist_ok=True)
            print(f"ODA已配置: {self.oda_path}")
        else:
            print(f"警告: ODA路径不存在: {self.oda_path}")
    
    def _check_needs_xvfb(self) -> bool:
        """检查Linux环境是否需要xvfb"""
        return os.name != 'nt' and not os.environ.get('DISPLAY')
    
    def read(self, file_path: str) -> Optional[Drawing]:
        """读取DWG/DXF文件"""
        try:
            if file_path.lower().endswith('.dwg'):
                print(f"正在转换并读取 DWG: {file_path}")
                try:
                    return odafc.readfile(file_path)
                except odafc.UnknownODAFCError:
                    # ODAFC在Linux下可能因为MESA警告而误判失败
                    # 尝试直接手动转换
                    return self._manual_dwg_to_dxf(file_path)
            else:
                print(f"正在读取 DXF: {file_path}")
                return ezdxf.readfile(file_path)
        except Exception as e:
            print(f"读取文件失败: {e}")
            return None
    
    def _manual_dwg_to_dxf(self, dwg_path: str) -> Optional[Drawing]:
        """手动调用ODA转换DWG到DXF"""
        import tempfile
        import subprocess
        from pathlib import Path
        
        infile = Path(dwg_path).absolute()
        with tempfile.TemporaryDirectory(prefix="odafc_") as tmp_dir:
            # 构建ODA参数
            args = [
                self.oda_path,
                str(infile.parent),
                tmp_dir,
                "ACAD2007",
                "DXF",
                "0",
                "1",
                infile.name
            ]
            
            env = os.environ.copy()
            env['XDG_RUNTIME_DIR'] = '/tmp/runtime-chongjibo'
            env['LIBGL_ALWAYS_SOFTWARE'] = '1'
            os.makedirs('/tmp/runtime-chongjibo', exist_ok=True)
            
            # 根据环境自动决定是否使用xvfb
            if self._use_xvfb:
                cmd = ['xvfb-run', '-a'] + args
            else:
                cmd = args
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=60
                )
                
                # 检查输出文件
                out_file = Path(tmp_dir) / infile.with_suffix('.dxf').name
                if out_file.exists():
                    return ezdxf.readfile(str(out_file))
                else:
                    print(f"转换后的文件未找到，stderr: {result.stderr[:200]}")
                    return None
            except Exception as e:
                print(f"手动转换失败: {e}")
                return None
    
    def save(self, doc: Drawing, output_path: str, version: str = "R2007"):
        """保存为DXF文件"""
        try:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            dxf_path = output_path.replace('.dwg', '.dxf')
            doc.dxfversion = ezdxf.const.DXF2007
            doc.saveas(dxf_path)
            print(f"文件已保存: {dxf_path}")
            return dxf_path
        except Exception as e:
            print(f"保存文件失败: {e}")
            return None
    
    def ensure_encoding(self, doc: Drawing) -> str:
        """确保文件编码支持UTF-8"""
        version = doc.dxfversion
        if version < ezdxf.const.DXF2007:
            print(f"DXF版本: {version}, 自动升级到 R2007 以支持 UTF-8")
            doc.dxfversion = ezdxf.const.DXF2007
        return "R2007"
    
    def set_chinese_fonts(self, doc: Drawing, font: str = "txt.shx", 
                         bigfont: str = "gbcbig.shx"):
        """设置中文字体支持"""
        try:
            for style in doc.styles:
                style.dxf.font = font
                style.dxf.bigfont = bigfont
            print(f"已设置中文字体: {font} + {bigfont}")
        except Exception as e:
            print(f"设置字体失败: {e}")
