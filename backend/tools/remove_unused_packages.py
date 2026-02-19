#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사용되지 않는 패키지를 삭제합니다.
주의: 이 스크립트는 실제로 패키지를 삭제하므로 신중하게 사용하세요.
"""
import subprocess
import sys

def read_unused_packages():
    """unused_packages.txt에서 패키지 목록을 읽습니다."""
    try:
        with open('unused_packages.txt', 'r', encoding='utf-8') as f:
            packages = [line.strip() for line in f if line.strip()]
        return packages
    except FileNotFoundError:
        print("오류: unused_packages.txt 파일을 찾을 수 없습니다.")
        return []

def remove_packages(packages, dry_run=True):
    """패키지를 삭제합니다."""
    if not packages:
        print("삭제할 패키지가 없습니다.")
        return

    if dry_run:
        print(f"[DRY RUN] {len(packages)}개 패키지를 삭제할 예정입니다.")
        print("\n삭제될 패키지 목록 (처음 30개):")
        for i, pkg in enumerate(packages[:30], 1):
            print(f"  {i}. {pkg}")
        if len(packages) > 30:
            print(f"  ... 외 {len(packages) - 30}개")
        print("\n실제로 삭제하려면 dry_run=False로 실행하세요.")
        return

    print(f"[실제 삭제] {len(packages)}개 패키지를 삭제합니다...")

    # 배치로 삭제 (한 번에 너무 많이 삭제하면 문제가 될 수 있으므로)
    batch_size = 50
    for i in range(0, len(packages), batch_size):
        batch = packages[i:i+batch_size]
        print(f"\n[{i+1}-{min(i+batch_size, len(packages))}/{len(packages)}] 삭제 중...")

        cmd = ['pip', 'uninstall', '-y'] + batch
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                print(f"  → 성공: {len(batch)}개 패키지")
            else:
                print(f"  → 일부 실패 (출력 확인 필요)")
                print(result.stderr[:500])
        except Exception as e:
            print(f"  → 오류: {e}")

def main():
    print("=" * 60)
    print("사용되지 않는 패키지 삭제 스크립트")
    print("=" * 60)

    unused_packages = read_unused_packages()

    if not unused_packages:
        return

    print(f"\n총 {len(unused_packages)}개 패키지가 식별되었습니다.")

    # 중요한 패키지는 보호 목록에 추가
    protected_packages = {
        'pip', 'setuptools', 'wheel', 'conda', 'anaconda-client',
        'jupyter', 'ipython', 'notebook', 'jupyterlab',
        'torch', 'torchvision', 'torchaudio',  # PyTorch 관련
        'numpy', 'pandas', 'scipy', 'scikit-learn',  # 데이터 과학 필수
        'fastapi', 'uvicorn', 'pydantic',  # 백엔드 필수
        'sqlalchemy', 'psycopg', 'psycopg2-binary',  # 데이터베이스
        'langchain', 'langchain-core', 'langchain-classic',  # LangChain
        'transformers', 'sentence-transformers',  # NLP
        'pdfplumber', 'PyMuPDF',  # PDF 처리
        'python-dotenv',  # 환경 변수
        # conda 의존성 패키지들
        'frozendict', 'boltons', 'archspec', 'charset-normalizer',
        'conda-package-handling', 'distro', 'platformdirs', 'pluggy',
        'pycosat', 'ruamel-yaml', 'truststore', 'zstandard',
        'urllib3', 'requests', 'idna', 'menuinst',
    }

    # 보호 목록에서 제외
    to_remove = [pkg for pkg in unused_packages if pkg.lower() not in {p.lower() for p in protected_packages}]
    protected = [pkg for pkg in unused_packages if pkg.lower() in {p.lower() for p in protected_packages}]

    if protected:
        print(f"\n[보호됨] 다음 {len(protected)}개 패키지는 보호 목록에 있어 삭제하지 않습니다:")
        for pkg in protected[:10]:
            print(f"  - {pkg}")
        if len(protected) > 10:
            print(f"  ... 외 {len(protected) - 10}개")

    print(f"\n[삭제 예정] {len(to_remove)}개 패키지")

    # DRY RUN 모드로 먼저 실행
    remove_packages(to_remove, dry_run=True)

    print("\n" + "=" * 60)
    print("실제로 삭제하려면:")
    print("  python remove_unused_packages.py --execute")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="사용되지 않는 패키지 삭제")
    parser.add_argument('--execute', action='store_true', help='실제로 삭제 실행')
    args = parser.parse_args()

    if args.execute:
        unused_packages = read_unused_packages()
        protected_packages = {
            'pip', 'setuptools', 'wheel', 'conda', 'anaconda-client',
            'jupyter', 'ipython', 'notebook', 'jupyterlab',
            'torch', 'torchvision', 'torchaudio',
            'numpy', 'pandas', 'scipy', 'scikit-learn',
            'fastapi', 'uvicorn', 'pydantic',
            'sqlalchemy', 'psycopg', 'psycopg2-binary',
            'langchain', 'langchain-core', 'langchain-classic',
            'transformers', 'sentence-transformers',
            'pdfplumber', 'PyMuPDF',
            'python-dotenv',
            # conda 의존성 패키지들
            'frozendict', 'boltons', 'archspec', 'charset-normalizer',
            'conda-package-handling', 'distro', 'platformdirs', 'pluggy',
            'pycosat', 'ruamel-yaml', 'truststore', 'zstandard',
            'urllib3', 'requests', 'idna', 'menuinst',
        }
        to_remove = [pkg for pkg in unused_packages if pkg.lower() not in {p.lower() for p in protected_packages}]
        remove_packages(to_remove, dry_run=False)
    else:
        main()

