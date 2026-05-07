import os
import sys
import subprocess
import shutil
import tempfile
import ezdxf
from ezdxf.addons import odafc
from ezdxf.document import Drawing
from pathlib import Path
from typing import Optional


class DWGCore:
    """DWG/DXF 核心读写模块"""
    
    def __init__(self, oda_path: str, oda_timeout: Optional[int] = None):
        if not oda_path:
            raise ValueError("必须指定ODA File Converter路径")
        
        self.oda_path = oda_path
        self.oda_timeout = oda_timeout or int(os.getenv('CADAIR_ODA_TIMEOUT_SECONDS', '120'))
        self.runtime_dir = os.getenv('XDG_RUNTIME_DIR') or os.getenv('CADAIR_ODA_RUNTIME_DIR', '/tmp/runtime-cadair')
        self._use_xvfb = False
        self.last_converted_dxf: Optional[str] = None
        self._setup_oda()
    
    def _setup_oda(self):
        """配置ODA File Converter路径"""
        if os.path.exists(self.oda_path):
            if os.name == 'nt':
                ezdxf.options.set("odafc-addon", "win_exec_path", self.oda_path)
            else:
                ezdxf.options.set("odafc-addon", "lin_exec_path", self.oda_path)
                self._use_xvfb = self._check_needs_xvfb()
                os.environ['XDG_RUNTIME_DIR'] = self.runtime_dir
                os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
                os.makedirs(self.runtime_dir, exist_ok=True)
            print(f"ODA已配置: {self.oda_path}")
        else:
            print(f"警告: ODA路径不存在: {self.oda_path}")
    
    def _check_needs_xvfb(self) -> bool:
        """检查Linux环境是否需要xvfb"""
        return os.name != 'nt' and not os.environ.get('DISPLAY')
    
    def read(self, file_path: str) -> Optional[Drawing]:
        """读取DWG/DXF文件"""
        self.last_converted_dxf = None
        try:
            if file_path.lower().endswith('.dwg'):
                print(f"正在转换并读取 DWG: {file_path}")
                return self._manual_dwg_to_dxf(file_path)
            else:
                print(f"正在读取 DXF: {file_path}")
                return ezdxf.readfile(file_path)
        except Exception as e:
            print(f"读取文件失败: {e}")
            return None
    
    def _manual_dwg_to_dxf(self, dwg_path: str) -> Optional[Drawing]:
        """手动调用ODA转换DWG到DXF"""
        dxf_path = self.convert_dwg_to_dxf(dwg_path)
        if not dxf_path:
            return None

        self.last_converted_dxf = dxf_path
        return ezdxf.readfile(dxf_path)

    def convert_dwg_to_dxf(self, dwg_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """使用ODA直接转换DWG到DXF，返回转换后的DXF路径。"""
        infile = Path(dwg_path).expanduser().resolve()
        if not infile.exists():
            print(f"DWG文件不存在: {dwg_path}")
            return None

        if output_path:
            final_path = Path(output_path).expanduser().resolve()
            final_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            fd, temp_name = tempfile.mkstemp(prefix=f"{infile.stem}_", suffix=".dxf")
            os.close(fd)
            final_path = Path(temp_name)

        with tempfile.TemporaryDirectory(prefix="odafc_") as tmp_dir:
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
            env['XDG_RUNTIME_DIR'] = self.runtime_dir
            env['LIBGL_ALWAYS_SOFTWARE'] = '1'
            os.makedirs(self.runtime_dir, exist_ok=True)
            
            # 根据环境自动决定是否使用xvfb
            if self._use_xvfb and shutil.which('xvfb-run'):
                cmd = ['xvfb-run', '-a'] + args
            else:
                cmd = args
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=self.oda_timeout
                )
                
                out_file = Path(tmp_dir) / infile.with_suffix('.dxf').name
                if out_file.exists():
                    shutil.copy2(out_file, final_path)
                    return str(final_path)
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
