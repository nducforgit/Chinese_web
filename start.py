"""
Launcher local: khởi động Streamlit + ngrok.
Để chạy local: venv/bin/python start.py
Để deploy cloud: dùng Streamlit Community Cloud (không cần file này).
"""
import subprocess
import sys
import os

NGROK_TOKEN_FILE = ".ngrok_token"
PORT = 8501


def _read_file(path):
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return None


def _write_file(path, value):
    with open(path, "w") as f:
        f.write(value.strip())


def start():
    print("=" * 50)
    print("  🌸 Học Tiếng Trung - Mai Hương")
    print("=" * 50)

    # --- Lấy ngrok token ---
    token = _read_file(NGROK_TOKEN_FILE)
    if not token:
        print("\n🔑 Cần nhập ngrok Authtoken.")
        print("   Đăng ký miễn phí tại: https://ngrok.com")
        print("   Vào Dashboard → Your Authtoken → Copy\n")
        token = input("Nhập authtoken: ").strip()
        if not token:
            print("❌ Không có token, thoát.")
            sys.exit(1)
        _write_file(NGROK_TOKEN_FILE, token)
        print("✅ Đã lưu token.\n")

    # --- Cấu hình ngrok ---
    from pyngrok import ngrok, conf
    conf.get_default().auth_token = token

    # --- Mở tunnel ---
    print("🚇 Đang mở tunnel ngrok...")
    try:
        tunnel = ngrok.connect(PORT, "http")
        public_url = tunnel.public_url
    except Exception as e:
        print(f"❌ Lỗi ngrok: {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print(f"  ✅ App đang chạy!")
    print(f"  📱 Truy cập từ mọi nơi:")
    print(f"     {public_url}")
    print(f"  💻 Truy cập nội bộ:")
    print(f"     http://localhost:{PORT}")
    print("=" * 50)
    print("\n  (Nhấn Ctrl+C để dừng)\n")

    # --- Khởi động Streamlit ---
    streamlit_path = os.path.join(os.path.dirname(sys.executable), "streamlit")
    try:
        subprocess.run(
            [streamlit_path, "run", "app.py",
             "--server.port", str(PORT),
             "--server.headless", "true",
             "--browser.gatherUsageStats", "false"],
            check=True
        )
    except KeyboardInterrupt:
        pass
    finally:
        print("\n⏹️  Đang dừng ngrok...")
        ngrok.disconnect(public_url)
        ngrok.kill()
        print("👋 Tạm biệt!")


if __name__ == "__main__":
    start()
