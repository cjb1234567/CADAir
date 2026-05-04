"""运行所有示例"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import subprocess


def run_example(name):
    print(f"\n{'='*50}")
    print(f"  运行: {name}")
    print(f"{'='*50}")
    subprocess.run([sys.executable, f"examples/{name}.py"])


def main():
    print("╔═════════════════════════════════════════╗")
    print("║       DWG 翻译器 - 运行所有示例         ║")
    print("╚═════════════════════════════════════════╝")
    
    examples = [
        "list_engines",
        "quick_start",
        "mock_translate",
        "extract_only",
        "custom_translator",
        "performance_compare"
    ]
    
    for name in examples:
        run_example(name)
    
    print("\n" + "="*50)
    print("  其他示例:")
    print("    - python examples/baidu_translate.py (需要API密钥)")
    print("    - python examples/writeback_only.py (先运行extract_only)")
    print("="*50)


if __name__ == "__main__":
    main()
