#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트에서 실제로 사용되는 패키지를 분석합니다.
"""
import ast
import os
import re
from pathlib import Path
from collections import defaultdict

def extract_imports_from_file(file_path):
    """파일에서 import 문을 추출합니다."""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # AST로 파싱
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
        except:
            # AST 파싱 실패 시 정규식으로 대체
            import_pattern = r'^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
            for line in content.split('\n'):
                match = re.match(import_pattern, line.strip())
                if match:
                    imports.add(match.group(1).split('.')[0])
    except:
        pass

    return imports

def scan_project_for_imports(root_dir='.'):
    """프로젝트 전체를 스캔하여 사용되는 패키지를 찾습니다."""
    used_packages = set()

    # 스캔할 디렉토리
    scan_dirs = [
        'backend',
        'data',
        'libs',
        'scripts',
    ]

    # 제외할 디렉토리
    exclude_dirs = {
        '__pycache__',
        '.git',
        'node_modules',
        '.venv',
        'venv',
        'env',
        'build',
        'dist',
        '.pytest_cache',
        '.mypy_cache',
    }

    # 제외할 파일 확장자
    exclude_extensions = {'.pyc', '.pyo', '.pyd', '.so', '.dll'}

    for scan_dir in scan_dirs:
        if not os.path.exists(scan_dir):
            continue

        for root, dirs, files in os.walk(scan_dir):
            # 제외 디렉토리 필터링
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    imports = extract_imports_from_file(file_path)
                    used_packages.update(imports)

    return used_packages

def get_installed_packages():
    """설치된 패키지 목록을 가져옵니다."""
    import subprocess
    result = subprocess.run(['pip', 'list', '--format=freeze'],
                          capture_output=True, text=True, encoding='utf-8')
    packages = {}
    for line in result.stdout.strip().split('\n'):
        if '==' in line:
            name, version = line.split('==', 1)
            packages[name.lower()] = name
    return packages

def main():
    print("[1/3] 프로젝트에서 사용되는 패키지 분석 중...")
    used_packages = scan_project_for_imports()
    print(f"  → {len(used_packages)}개 패키지가 import되었습니다.")

    print("[2/3] 설치된 패키지 목록 가져오기 중...")
    installed_packages = get_installed_packages()
    print(f"  → {len(installed_packages)}개 패키지가 설치되어 있습니다.")

    # 표준 라이브러리는 제외
    stdlib_modules = {
        'sys', 'os', 're', 'json', 'csv', 'datetime', 'time', 'random',
        'math', 'collections', 'itertools', 'functools', 'operator',
        'pathlib', 'shutil', 'glob', 'tempfile', 'io', 'codecs',
        'urllib', 'http', 'email', 'html', 'xml', 'sqlite3',
        'threading', 'multiprocessing', 'queue', 'asyncio',
        'unittest', 'doctest', 'pdb', 'logging', 'warnings',
        'abc', 'typing', 'dataclasses', 'enum', 'copy', 'pickle',
        'hashlib', 'base64', 'secrets', 'uuid', 'struct',
        'argparse', 'getopt', 'configparser', 'readline',
        'ctypes', 'platform', 'subprocess', 'signal', 'socket',
        'ssl', 'gzip', 'zipfile', 'tarfile', 'shlex', 'textwrap',
        'string', 'unicodedata', 'locale', 'gettext', 'keyword',
        'tokenize', 'ast', 'dis', 'inspect', 'traceback', 'trace',
        'gc', 'weakref', 'types', 'copyreg', 'marshal', 'dbm',
        'shelve', 'mmap', 'select', 'selectors', 'asyncio',
        'concurrent', 'multiprocessing', 'queue', 'sched',
        'contextvars', 'contextlib', 'functools', 'operator',
        'statistics', 'decimal', 'fractions', 'numbers', 'cmath',
        'array', 'bisect', 'heapq', 'collections', 'collections.abc',
        'atexit', 'gc', 'inspect', 'site', 'sysconfig', 'builtins',
        '__future__', 'importlib', 'pkgutil', 'modulefinder',
        'runpy', 'zipimport', 'pkgutil', 'imp', 'importlib',
    }

    # 사용되는 패키지 중 표준 라이브러리가 아닌 것들
    used_non_stdlib = {pkg for pkg in used_packages if pkg not in stdlib_modules}

    # 설치된 패키지 중 사용되지 않는 것들 찾기
    unused_packages = []
    for installed_name, original_name in installed_packages.items():
        # 패키지 이름 매핑 (예: PyYAML -> yaml)
        package_mappings = {
            'pyyaml': 'yaml',
            'pillow': 'pil',
            'beautifulsoup4': 'bs4',
            'python-dateutil': 'dateutil',
            'pywin32': 'win32',
            'pymupdf': 'fitz',
        }

        mapped_name = package_mappings.get(installed_name, installed_name)

        # 사용 여부 확인
        is_used = False
        for used in used_non_stdlib:
            if used.lower() == installed_name.lower() or used.lower() == mapped_name.lower():
                is_used = True
                break
            # 하위 모듈 체크 (예: langchain.core -> langchain)
            if '.' in used:
                top_level = used.split('.')[0]
                if top_level.lower() == installed_name.lower() or top_level.lower() == mapped_name.lower():
                    is_used = True
                    break

        if not is_used:
            unused_packages.append(original_name)

    print(f"[3/3] 분석 완료")
    print(f"\n사용되는 패키지: {len(used_non_stdlib)}개")
    print(f"사용되지 않는 패키지: {len(unused_packages)}개")

    # 결과 저장
    with open('used_packages.txt', 'w', encoding='utf-8') as f:
        for pkg in sorted(used_non_stdlib):
            f.write(f"{pkg}\n")

    with open('unused_packages.txt', 'w', encoding='utf-8') as f:
        for pkg in sorted(unused_packages):
            f.write(f"{pkg}\n")

    print(f"\n결과가 저장되었습니다:")
    print(f"  - used_packages.txt: 사용되는 패키지 목록")
    print(f"  - unused_packages.txt: 사용되지 않는 패키지 목록")

    # 상위 20개 미사용 패키지 출력
    print(f"\n사용되지 않는 패키지 (상위 20개):")
    for i, pkg in enumerate(sorted(unused_packages)[:20], 1):
        print(f"  {i}. {pkg}")

    if len(unused_packages) > 20:
        print(f"  ... 외 {len(unused_packages) - 20}개")

if __name__ == "__main__":
    main()

