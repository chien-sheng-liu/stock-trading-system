#!/usr/bin/env python3
"""
AI Trading Pro API 簡化啟動腳本
"""
import uvicorn
import sys
import os


def main():
    print("🚀 AI Trading Pro API 啟動中...")
    print("📍 服務器: http://127.0.0.1:5000")
    print("📚 API文檔: http://127.0.0.1:5000/docs")
    print("💊 健康檢查: http://127.0.0.1:5000/health")
    print("🔄 熱重載已啟用")
    print("⏹️  按 Ctrl+C 停止服務器")
    print("-" * 50)

    try:
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=5000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服務器已停止")
    except Exception as e:
        print(f"❌ 啟動錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()