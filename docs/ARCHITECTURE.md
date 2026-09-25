# Media Downloader PRO — Architecture & Layering Diagram

> [!NOTE]
> **Language Policy**: The official documentation, design files, and project rules for Media Downloader PRO are maintained in Thai.

เอกสารนี้ระบุความสัมพันธ์และการจัดแบ่ง Layer ตามสถาปัตยกรรมที่ระบุไว้ใน `PROJECT_RULES.md`

## Architecture Boundaries

สถาปัตยกรรมแบ่งออกเป็น 4 ชั้นหลัก โดยการเรียกใช้งานต้องเป็นทิศทางแบบ **บนลงล่าง (top-down)** เสมอ:
1. **UI Layer** (หน้าตาแอปพลิเคชัน หน้า และ components ต่างๆ)
2. **Services Layer** (จัดการพฤติกรรมของระบบปฏิบัติการและประวัติการทำงาน)
3. **Domain Layer** (โมเดลข้อมูล ตัวแปลงและคำนวณ Preset และ engine ของ yt-dlp)
4. **Core Layer** (การทำงานพื้นฐานของระบบ เช่น การเก็บข้อมูล JSON การตั้งค่า ตัวบันทึก log และกลไก self-updater)

```mermaid
graph TD
    %% Define Layers
    subgraph UI ["UI Layer (src/ui)"]
        ui_main["main_window.py"]
        ui_pages["pages/"]
        ui_comp["components/"]
        ui_work["workers/"]
    end

    subgraph Services ["Services Layer (src/services)"]
        srv_hist["history_manager.py"]
        srv_plat["platform_actions.py"]
    end

    subgraph Domain ["Domain Layer (src/domain)"]
        dom_dl["media_downloader.py (yt-dlp Engine)"]
        dom_opt["yt_options.py"]
        dom_pre["presets.py"]
        dom_mod["models.py (MediaType, JobState, etc.)"]
    end

    subgraph Core ["Core Layer (src/core)"]
        core_cfg["config.py"]
        core_store["json_store.py"]
        core_upd["updater.py"]
        core_log["logger.py"]
        core_rt["runtime.py"]
    end

    %% Dependency flow
    ui_main --> ui_pages
    ui_pages --> ui_comp
    ui_pages --> ui_work
    
    ui_work --> dom_dl
    ui_main --> srv_hist
    
    srv_hist --> core_store
    srv_hist --> core_cfg
    
    dom_dl --> dom_opt
    dom_dl --> dom_mod
    dom_opt --> dom_pre
    dom_pre --> dom_mod
    dom_dl --> core_cfg
    
    core_cfg --> core_store
    core_upd --> core_store
    core_log --> core_store
```

## Boundary Rules

- **UI Isolation**: โค้ดใน UI Layer ห้ามเรียกใช้งานเครือข่าย ห้ามจัดการไฟล์ดาวน์โหลดตรงๆ และห้ามติดต่อกับ yt-dlp โดยไม่ผ่าน Domain/Workers
- **Domain Independence**: โค้ดใน Domain และ Services Layer ห้ามทำการนำเข้า (import) โค้ดใดๆ จาก UI Layer เป็นอันขาด
- **Single Session Isolation**: งานดาวน์โหลดแต่ละงานต้องมี session และ cancellation token แยกเป็นของตนเอง ห้ามแชร์ mutable global state
