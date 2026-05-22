# -*- coding: utf-8 -*-
"""
📁 Mirae Asset Auto Git Sync Watcher
----------------------------------------------------------------------------------
• 이 스크립트는 백그라운드에서 실행되며 감시 파일(app.py, report_parser.py 등)의 수정을 감지합니다.
• 파일 변경이 확인되면 자동으로 Git staging, Commit, Pull(rebase) 및 Push를 처리하여
  깃허브 저장소를 항상 최신 상태로 유지해 줍니다.
• 실행: python auto_git_sync.py
----------------------------------------------------------------------------------
"""
import os
import time
import subprocess

# 감시 대상 파일 목록
WATCH_FILES = ["app.py", "report_parser.py", "make_samples.py"]

# 검색된 GitHub Desktop 내장 Git 실행 파일 절대 경로
GIT_PATH = r"C:\Users\이상훈\AppData\Local\GitHubDesktop\app-3.5.9\resources\app\git\cmd\git.exe"

def run_git(args):
    """지정된 Git 바이너리를 통해 Git 명령을 실행합니다."""
    cmd = [GIT_PATH] + args
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        return None, e.stderr.strip()

def sync_file(filepath):
    print(f"\n⚡ [{time.strftime('%Y-%m-%d %H:%M:%S')}] 파일 변경 감지됨: {filepath}")
    
    # 1. 파일 스테이징
    print("  Staging file...")
    _, err = run_git(["add", filepath])
    if err:
        print(f"  ❌ Add 실패: {err}")
        return
        
    # 2. 실제 스테이징된 변경 사항이 있는지 사전 체크
    status, _ = run_git(["status", "--porcelain"])
    if not status:
        print("  ℹ️ 실제 변경된 코드 내용이 없어 동기화를 건너뜁니다.")
        return

    # 3. 자동 커밋 생성
    commit_msg = f"auto: {os.path.basename(filepath)} 수정사항 자동 동기화"
    print(f"  Committing: '{commit_msg}'...")
    _, err = run_git(["commit", "-m", commit_msg])
    if err:
        print(f"  ❌ Commit 실패: {err}")
        return

    # 4. 원격 저장소와 동기화 (충돌 방지를 위한 rebase pull)
    print("  원격 변경 사항 동기화 중 (Pull & Rebase)...")
    env = os.environ.copy()
    # vi 에디터가 안 뜨도록 더미 파이썬 코드를 임시 에디터로 주입하여 충돌 없는 자동 리베이스 처리
    env["GIT_EDITOR"] = "python -c \"import sys; sys.exit(0)\""
    try:
        subprocess.run([GIT_PATH, "pull", "--rebase", "origin", "main"], 
                       env=env, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ Pull/Rebase 경고 (자동 병합 또는 수동 충돌 해결 필요 가능성): {e.stderr.strip()}")
        # 푸시를 계속 시도합니다 (원격에 새로운 내역이 이미 풀 된 상태일 수 있음)
        
    # 5. 깃허브 푸시
    print("  GitHub에 업로드 중 (Pushing)...")
    _, err = run_git(["push", "origin", "main"])
    if err:
        print(f"  ❌ GitHub 동기화 실패: {err}")
    else:
        print(f"  🎯 깃허브 자동 업데이트 성공!")

def main():
    print("====================================================")
    print("📁 Mirae Asset Auto Git Sync Watcher 시작")
    print("====================================================")
    print(f"• 감시 대상: {', '.join(WATCH_FILES)}")
    print(f"• Git 경로 : {GIT_PATH}")
    print("• 상태     : 작동 중... 파일을 편집 및 저장하면 실시간 자동 푸시됩니다.")
    print("• 종료하려면 창에서 Ctrl+C를 누르세요.\n")

    # 파일들의 마지막 수정일자 초기화
    last_mtimes = {}
    for f in WATCH_FILES:
        if os.path.exists(f):
            last_mtimes[f] = os.path.getmtime(f)
        else:
            last_mtimes[f] = 0.0

    try:
        while True:
            time.sleep(2.0)  # 2초 단위 폴링
            for f in WATCH_FILES:
                if not os.path.exists(f):
                    continue
                current_mtime = os.path.getmtime(f)
                if last_mtimes.get(f) is None:
                    last_mtimes[f] = current_mtime
                    continue
                
                # 파일 수정 감지 시
                if current_mtime > last_mtimes[f]:
                    # 파일 저장 작성이 완전히 끝날 때까지 0.5초 대기
                    time.sleep(0.5)
                    sync_file(f)
                    # 중복 실행 방지를 위해 수정한 최신 마크 타임 기록
                    last_mtimes[f] = os.path.getmtime(f)
                    
    except KeyboardInterrupt:
        print("\n👋 Auto Git Sync Watcher를 종료합니다.")

if __name__ == "__main__":
    main()
