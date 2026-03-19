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
    except PermissionError:
        print(f"Permission denied: {log_file}")
    except IsADirectoryError:
        print(f"Expected a file, but found a directory: {log_file}")
    except UnicodeDecodeError:
        print(f"Failed to decode log file as UTF-8: {log_file}")
    except OSError as e:
        # 기타 운영체제 수준 파일 입출력 예외 처리
        print(f"Failed to read log file: {e}")


if __name__ == "__main__":
    main()