"""Windows control panel for source-first Local Alpha."""
from __future__ import annotations

import multiprocessing
from pathlib import Path
import subprocess
import sys
import traceback

from .alpha_controller import AlphaController
from .version import VERSION

ROOT = Path(__file__).resolve().parents[1]


class AlphaApp:
    def __init__(self, window, root: Path = ROOT, *, controller=None, ready_check=None) -> None:
        import tkinter as tk
        from tkinter import ttk
        from tools.alpha_setup import readiness

        self.window = window
        self.root = root
        self.controller = controller or AlphaController(root)
        self.ready_check = ready_check or readiness
        self.closing = False
        self.archive: Path | None = None
        self.last_error = ""

        window.title("POE2 Việt Hóa — Local Alpha")
        window.geometry("620x600")
        window.minsize(600, 560)
        window.configure(bg="#151b24")
        window.protocol("WM_DELETE_WINDOW", self.close)

        style = ttk.Style(window)
        style.theme_use("clam")
        style.configure("Alpha.TButton", font=("Segoe UI", 10), padding=(12, 10))
        style.configure("Alpha.Horizontal.TProgressbar", background="#63b59c", troughcolor="#263344")

        body = tk.Frame(window, bg="#151b24", padx=26, pady=22)
        self.body = body
        body.pack(fill="both", expand=True)

        def label(text="", **kwargs):
            widget = tk.Label(body, text=text, bg="#151b24", fg="#e8edf4", anchor="w", **kwargs)
            widget.pack(fill="x")
            return widget

        label("POE2 VIỆT HÓA", font=("Segoe UI", 19, "bold"))
        label(f"Local Alpha {VERSION}", font=("Segoe UI", 10), pady=5)
        label("Renly: Introduction / The Miller  •  Una: Home / Clearfell",
              font=("Segoe UI", 10), pady=7)

        self.status = label("Sẵn sàng", font=("Segoe UI", 12, "bold"), pady=6)
        self.detail = label("Bắt đầu để chơi, hoặc chọn QC 60 giây để gửi kết quả.",
                            font=("Segoe UI", 10), wraplength=560, justify="left")
        self.timer = label("Thời gian trong game: 0 giây", font=("Segoe UI", 10), pady=9)
        self.progress = ttk.Progressbar(body, maximum=60, style="Alpha.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 9))
        self.counters = label("Đã hiện: 0  •  Chưa có bản dịch: 0  •  Lỗi: 0", font=("Segoe UI", 10))

        row = tk.Frame(body, bg="#151b24")
        row.pack(fill="x", pady=18)
        self.play_button = ttk.Button(row, text="Bắt đầu", style="Alpha.TButton", command=lambda: self.start("alpha"))
        self.qc_button = ttk.Button(row, text="QC 60 giây", style="Alpha.TButton", command=lambda: self.start("qc_alpha"))
        self.stop_button = ttk.Button(row, text="Dừng & tạo ZIP", style="Alpha.TButton", command=self.stop, state="disabled")
        for button in (self.play_button, self.qc_button, self.stop_button):
            button.pack(side="left", padx=(0, 9))

        self.file_label = label("Kết quả sẽ xuất hiện ở đây sau khi dừng hoặc QC xong.",
                                font=("Segoe UI", 9), wraplength=560, justify="left", pady=7)
        self.open_button = ttk.Button(body, text="Mở file kết quả", style="Alpha.TButton", command=self.open_result, state="disabled")
        self.open_button.pack(anchor="w", pady=(2, 8))
        label("Bắt đầu sẽ thu nhỏ cửa sổ. Alt+Tab quay lại đây để Dừng.\n"
              "Chế độ chơi lưu log nhẹ; QC mới lưu ảnh vùng hội thoại.",
              font=("Segoe UI", 9), wraplength=560, justify="left", pady=7)

        ready, message = self.ready_check(root)
        self.ready = ready
        self.detail.configure(text=message)
        if not ready:
            self.status.configure(text="Cần thiết lập")
            self.play_button.configure(state="disabled")
            self.qc_button.configure(state="disabled")
        self.restore_result()
        self.fit_panel()
        window.after(100, self.poll)

    def fit_panel(self) -> None:
        # Tk's point fonts grow at higher Windows DPI. Fit actual widget sizes
        # rather than assuming the 100% DPI height used by the first prototype.
        self.window.update_idletasks()
        width = min(self.window.winfo_screenwidth() - 60,
                    max(620, self.window.winfo_width(), self.body.winfo_reqwidth()))
        height = min(self.window.winfo_screenheight() - 80,
                     max(600, self.window.winfo_height(), self.body.winfo_reqheight()))
        self.window.geometry(f"{width}x{height}")

    def restore_result(self) -> None:
        candidates = []
        for name in ("LAST_ALPHA_RESULT.txt", "LAST_QC_RESULT.txt"):
            try:
                for line in (self.root / name).read_text(encoding="utf-8").splitlines():
                    candidate = self.root / Path(line.strip()).name
                    if (candidate.name.startswith(("ALPHA_RESULT_", "QC_PHASE3_RESULT_", "QC_PHASE4_RESULT_"))
                            and candidate.suffix == ".zip" and candidate.is_file()):
                        candidates.append(candidate)
            except OSError:
                continue
        if candidates:
            self.archive = max(candidates, key=lambda p: p.stat().st_mtime)
            self.file_label.configure(text=f"Kết quả lần trước: {self.archive.name}")
            self.open_button.configure(state="normal")

    def start(self, mode: str) -> None:
        ready, message = self.ready_check(self.root)
        self.ready = ready
        if not ready:
            self.status.configure(text="Cần thiết lập")
            self.detail.configure(text=message)
            return
        try:
            if not self.controller.start(mode):
                return
        except Exception as exc:
            self.status.configure(text="Không khởi động được")
            self.detail.configure(text=str(exc))
            return
        self.archive = None
        self.last_error = ""
        self.open_button.configure(state="disabled")
        self.play_button.configure(state="disabled")
        self.qc_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status.configure(text="Đang khởi động")
        self.detail.configure(text="Chuyển sang PoE2 để bắt đầu nhận hội thoại.")
        self.timer.configure(text="Thời gian trong game: 0 giây")
        self.counters.configure(text="Đã hiện: 0  •  Chưa có bản dịch: 0  •  Lỗi: 0")
        self.progress.configure(value=0)
        self.file_label.configure(text="Đang chạy; file ZIP được tạo khi dừng hoặc QC xong.")
        self.window.iconify()

    def stop(self) -> None:
        self.controller.stop()
        self.status.configure(text="Đang dừng và tạo ZIP…")
        self.stop_button.configure(state="disabled")

    def update_message(self, message) -> None:
        if message["type"] == "status":
            if self.controller.stop_at is not None:
                return
            state = message["state"]
            names = {"starting": "Đang khởi động", "waiting": "Đang chờ PoE2",
                     "paused": "Tạm dừng", "running": "Đang chạy", "error": "Có lỗi"}
            self.status.configure(text=names.get(state, state))
            self.detail.configure(text=message["message"])
            if state == "error":
                self.last_error = message["message"]
            self.update_stats(message)
        elif message["type"] in {"finished", "failed"}:
            summary = message.get("summary", {})
            result = summary.get("result", "ERROR")
            success = message["type"] == "finished" and result in {"STOPPED", "TECHNICAL_PASS"}
            self.status.configure(text="QC hoàn tất" if success and result == "TECHNICAL_PASS"
                                  else "Đã dừng" if success else "Kết quả cần kiểm tra")
            self.detail.configure(text=("Đã tạo ZIP. Bấm Mở file kết quả để gửi lại trong chat." if success
                                        else message.get("message") or summary.get("last_error") or self.last_error
                                        or "Phiên chưa hoàn tất hoặc có lỗi. Gửi ZIP để kiểm tra."))
            self.update_stats({"active_seconds": summary.get("active_seconds", 0), "stats": summary})
            path_text = message.get("archive", "")
            if path_text:
                self.archive = Path(path_text)
                self.file_label.configure(text=f"File cần gửi: {self.archive.name}")
                self.open_button.configure(state="normal")
            else:
                self.file_label.configure(text="Chưa tạo được file ZIP. Chụp cửa sổ này để gửi lỗi.")
        self.fit_panel()

    def update_stats(self, message) -> None:
        active = message.get("active_seconds", 0)
        is_qc = self.controller.mode == "qc_alpha"
        self.timer.configure(text=f"Thời gian trong game: {active:.1f}" + (" / 60 giây" if is_qc else " giây"))
        self.progress.configure(value=min(60, active) if is_qc else 0)
        stats = message.get("stats", {})
        errors = sum(stats.get(k, 0) for k in ("ocr_errors", "overlay_errors", "runtime_errors"))
        self.counters.configure(text=f"Đã hiện: {stats.get('overlay_updates', 0)}  •  "
                               f"Chưa có bản dịch: {stats.get('unmatched', 0)}  •  Lỗi: {errors}")

    def poll(self) -> None:
        try:
            for message in self.controller.poll():
                self.update_message(message)
        except Exception as exc:
            self.status.configure(text="Có lỗi điều khiển")
            self.detail.configure(text=str(exc))
            self.controller.stop()
        if not self.controller.busy:
            self.stop_button.configure(state="disabled")
            self.play_button.configure(state="normal" if self.ready else "disabled")
            self.qc_button.configure(state="normal" if self.ready else "disabled")
            if self.closing:
                self.window.destroy()
                return
        self.window.after(100, self.poll)

    def open_result(self) -> None:
        if self.archive is None or not self.archive.exists():
            self.detail.configure(text="Không tìm thấy file kết quả. Hãy chạy lại QC.")
            return
        try:
            subprocess.Popen(["explorer.exe", "/select,", str(self.archive.resolve())])
        except OSError as exc:
            self.detail.configure(text=f"Không mở được Explorer: {exc}. File: {self.archive}")

    def close(self) -> None:
        self.closing = True
        if self.controller.busy:
            self.stop()
        else:
            self.window.destroy()


def main() -> None:
    multiprocessing.freeze_support()
    try:
        if sys.platform != "win32":
            raise RuntimeError("Local Alpha cần Windows.")
        import tkinter as tk
        from .replacement_overlay import enable_per_monitor_dpi_awareness
        enable_per_monitor_dpi_awareness()
        window = tk.Tk()
        AlphaApp(window)
        window.mainloop()
    except Exception:
        text = traceback.format_exc()
        (ROOT / "ALPHA_STARTUP_ERROR.txt").write_text(text, encoding="utf-8")
        try:
            from tkinter import messagebox
            messagebox.showerror("POE2 Việt Hóa", "Không mở được Alpha. Gửi ALPHA_STARTUP_ERROR.txt để kiểm tra.")
        except Exception:
            pass
        raise SystemExit(1)


if __name__ == "__main__":
    main()
