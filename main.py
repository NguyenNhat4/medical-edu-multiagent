from flow import create_medical_agent_flow
import os

def main():
    shared = {
        "history": [],
        "requirements": {},
        "plan_outline": None,
        "generated_content": {}
    }

    print("Khởi động Hệ thống Multi-Agent Y Khoa...")

    try:
        flow = create_medical_agent_flow()
        flow.run(shared)
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")
        return
    except Exception as e:
        print(f"\nĐã xảy ra lỗi: {e}")
        import traceback
        traceback.print_exc()
        return

    # Save outputs
    print("\n--- KẾT QUẢ ---")
    results = shared.get("generated_content", {})
    if not results:
        print("Không có nội dung nào được tạo.")
        return

    os.makedirs("output", exist_ok=True)

    topic_slug = shared['requirements'].get('topic', 'doc').replace(" ", "_")
    # limit filename length
    topic_slug = topic_slug[:30]

    for art_type, content in results.items():
        filename = f"output/{art_type}_{topic_slug}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Đã lưu: {filename}")

    print("\nHoàn tất! Các file nằm trong thư mục output/")

if __name__ == "__main__":
    main()
