#!/usr/bin/env python3
"""
Sandbox Runner - 容器內的 Python 程式執行器

功能：
- 執行 Python 代碼
- 捕獲 stdout/stderr
- 捕獲 matplotlib 圖表轉為 base64
- 安全的執行環境
"""

import sys
import json
import io
import base64
import traceback
import contextlib
from typing import Dict, Any, List

# 預載入常用模組（加速執行）
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 非 GUI 後端
import matplotlib.pyplot as plt


class OutputCapture:
    """捕獲 stdout/stderr 和圖表"""
    
    def __init__(self):
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        self.figures: List[str] = []  # base64 圖表列表
        
    @contextlib.contextmanager
    def capture(self):
        """Context manager 捕獲輸出"""
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            sys.stdout = self.stdout_buffer
            sys.stderr = self.stderr_buffer
            yield self
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def capture_figures(self):
        """捕獲所有 matplotlib 圖表"""
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            self.figures.append(img_base64)
            plt.close(fig)
    
    def get_stdout(self) -> str:
        return self.stdout_buffer.getvalue()
    
    def get_stderr(self) -> str:
        return self.stderr_buffer.getvalue()


def create_safe_globals() -> Dict[str, Any]:
    """創建安全的全域命名空間"""
    safe_globals = {
        '__builtins__': {
            # 安全的內建函數
            'print': print,
            'len': len,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'sorted': sorted,
            'reversed': reversed,
            'list': list,
            'dict': dict,
            'set': set,
            'tuple': tuple,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'bytes': bytes,
            'type': type,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,
            'delattr': delattr,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'round': round,
            'pow': pow,
            'divmod': divmod,
            'all': all,
            'any': any,
            'ord': ord,
            'chr': chr,
            'hex': hex,
            'oct': oct,
            'bin': bin,
            'format': format,
            'repr': repr,
            'hash': hash,
            'id': id,
            'slice': slice,
            'iter': iter,
            'next': next,
            'callable': callable,
            'staticmethod': staticmethod,
            'classmethod': classmethod,
            'property': property,
            'super': super,
            'object': object,
            'Exception': Exception,
            'ValueError': ValueError,
            'TypeError': TypeError,
            'KeyError': KeyError,
            'IndexError': IndexError,
            'AttributeError': AttributeError,
            'RuntimeError': RuntimeError,
            'StopIteration': StopIteration,
            'True': True,
            'False': False,
            'None': None,
            # 禁止危險操作
            # 'open': None,  # 禁止文件操作
            # 'exec': None,
            # 'eval': None,
            # '__import__': None,
        },
        # 預載入的安全模組
        'np': np,
        'numpy': np,
        'pd': pd,
        'pandas': pd,
        'plt': plt,
        'matplotlib': matplotlib,
    }
    
    # 允許 import 常用模組
    import math
    import statistics
    import datetime
    import json as json_module
    import re
    import collections
    import itertools
    import functools
    import random
    
    safe_globals.update({
        'math': math,
        'statistics': statistics,
        'datetime': datetime,
        'json': json_module,
        're': re,
        'collections': collections,
        'itertools': itertools,
        'functools': functools,
        'random': random,
    })
    
    # 嘗試載入更多套件
    try:
        import seaborn as sns
        safe_globals['sns'] = sns
        safe_globals['seaborn'] = sns
    except ImportError:
        pass
    
    try:
        import scipy
        safe_globals['scipy'] = scipy
    except ImportError:
        pass
    
    try:
        import sklearn
        safe_globals['sklearn'] = sklearn
    except ImportError:
        pass
    
    try:
        import sympy
        safe_globals['sympy'] = sympy
    except ImportError:
        pass
    
    return safe_globals


def execute_code(code: str) -> Dict[str, Any]:
    """
    執行 Python 代碼
    
    Args:
        code: Python 代碼字串
        
    Returns:
        執行結果字典
    """
    capture = OutputCapture()
    result = {
        'success': False,
        'stdout': '',
        'stderr': '',
        'error': None,
        'error_type': None,
        'traceback': None,
        'figures': [],
        'return_value': None,
    }
    
    try:
        # 創建安全的執行環境
        safe_globals = create_safe_globals()
        local_vars = {}
        
        # 編譯代碼
        compiled = compile(code, '<sandbox>', 'exec')
        
        # 執行代碼並捕獲輸出
        with capture.capture():
            exec(compiled, safe_globals, local_vars)
        
        # 捕獲圖表
        capture.capture_figures()
        
        # 檢查是否有 result 變數（用於返回值）
        return_value = local_vars.get('result', local_vars.get('output', None))
        
        result['success'] = True
        result['stdout'] = capture.get_stdout()
        result['stderr'] = capture.get_stderr()
        result['figures'] = capture.figures
        
        # 嘗試序列化返回值
        if return_value is not None:
            try:
                if isinstance(return_value, pd.DataFrame):
                    result['return_value'] = {
                        'type': 'dataframe',
                        'data': return_value.to_dict('records'),
                        'columns': return_value.columns.tolist(),
                        'shape': list(return_value.shape)
                    }
                elif isinstance(return_value, pd.Series):
                    result['return_value'] = {
                        'type': 'series',
                        'data': return_value.to_dict(),
                        'name': return_value.name
                    }
                elif isinstance(return_value, np.ndarray):
                    result['return_value'] = {
                        'type': 'ndarray',
                        'data': return_value.tolist(),
                        'shape': list(return_value.shape),
                        'dtype': str(return_value.dtype)
                    }
                else:
                    result['return_value'] = json.loads(json.dumps(return_value, default=str))
            except:
                result['return_value'] = str(return_value)
        
    except SyntaxError as e:
        result['error'] = str(e)
        result['error_type'] = 'SyntaxError'
        result['stderr'] = capture.get_stderr()
        
    except Exception as e:
        result['error'] = str(e)
        result['error_type'] = type(e).__name__
        result['traceback'] = traceback.format_exc()
        result['stdout'] = capture.get_stdout()
        result['stderr'] = capture.get_stderr()
        
        # 捕獲執行過程中可能生成的圖表
        try:
            capture.capture_figures()
            result['figures'] = capture.figures
        except:
            pass
    
    return result


def main():
    """主函數 - 從 stdin 讀取代碼，執行後輸出 JSON 結果"""
    # 從 stdin 讀取輸入
    input_data = sys.stdin.read()
    
    try:
        # 解析輸入
        request = json.loads(input_data)
        code = request.get('code', '')
        
        if not code:
            result = {
                'success': False,
                'error': 'No code provided',
                'error_type': 'ValueError'
            }
        else:
            result = execute_code(code)
            
    except json.JSONDecodeError as e:
        # 如果不是 JSON，直接當作代碼執行
        result = execute_code(input_data)
    except Exception as e:
        result = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
    
    # 輸出 JSON 結果
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
