def main() -> None:
    print("Hello Mars")

    # 실행 위치와 관계없이 main.py와 같은 폴더의 로그 파일을 찾는다.
    base_dir = __file__.replace("/", "\\").rsplit("\\", 1)[0]
    log_file = f"{base_dir}\\mission_computer_main.log"
    try:
        # 로그 파일을 열고 전체 내용을 읽어 화면에 출력
        with open(log_file, "r", encoding="utf-8") as f:
            log_text = f.read()
        print(log_text)
    except FileNotFoundError:
        print(f"Log file not found: {log_file}")
    except OSError as e:
        # 파일 경로/권한 등 읽기 과정에서 발생할 수 있는 예외 처리
        print(f"Failed to read log file: {e}")


if __name__ == "__main__":
    main()