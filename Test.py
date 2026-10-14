import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import ocrmypdf


class PDFConverterGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Scanned PDF to Searchable PDF Converter")
        self.root.geometry("640x480")
        self.root.resizable(False, False)

        # Path variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        # 1. Input Folder Selection Frame
        frame_input = ttk.LabelFrame(
            self.root, text=" 1. Select Input Folder (Scanned PDFs) ", padding=10
        )
        frame_input.pack(fill="x", padx=15, pady=10)

        ttk.Entry(
            frame_input, textvariable=self.input_folder, width=52
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            frame_input, text="Browse Folder", command=self.browse_input
        ).pack(side="left")

        # 2. Output Folder Selection Frame
        frame_output = ttk.LabelFrame(
            self.root,
            text=" 2. Select Output Folder (Searchable PDFs) ",
            padding=10,
        )
        frame_output.pack(fill="x", padx=15, pady=10)

        ttk.Entry(
            frame_output, textvariable=self.output_folder, width=52
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            frame_output, text="Browse Folder", command=self.browse_output
        ).pack(side="left")

        # Start Processing Button
        self.btn_start = ttk.Button(
            self.root, text="Start Conversion", command=self.start_conversion
        )
        self.btn_start.pack(pady=10)

        # Progress Bar
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", mode="determinate", length=600
        )
        self.progress.pack(padx=15, pady=5)

        # Output Log Box
        frame_log = ttk.LabelFrame(self.root, text=" Output Log ", padding=10)
        frame_log.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_text = tk.Text(frame_log, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def browse_input(self):
        folder = filedialog.askdirectory(title="Select Directory with Scanned PDFs")
        if folder:
            self.input_folder.set(folder)
            if not self.output_folder.get():
                self.output_folder.set(os.path.join(folder, "Searchable_PDFs"))

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Destination Directory")
        if folder:
            self.output_folder.set(folder)

    def append_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def start_conversion(self):
        in_dir = self.input_folder.get().strip()
        out_dir = self.output_folder.get().strip()

        if not in_dir or not os.path.exists(in_dir):
            messagebox.showerror(
                "Error", "Please select a valid input directory containing PDFs."
            )
            return

        if not out_dir:
            messagebox.showerror(
                "Error", "Please select a valid output directory."
            )
            return

        self.btn_start.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

        # Run conversion in a separate thread to keep UI responsive
        threading.Thread(
            target=self.process_conversion,
            args=(in_dir, out_dir),
            daemon=True,
        ).start()

    def process_conversion(self, in_dir, out_dir):
        pdf_files = [f for f in os.listdir(in_dir) if f.lower().endswith(".pdf")]

        if not pdf_files:
            self.append_log("No PDF files found in the selected input directory.")
            self.btn_start.config(state="normal")
            return

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        self.append_log(f"Found {len(pdf_files)} PDF file(s). Starting OCR processing...\n")
        self.progress["maximum"] = len(pdf_files)
        self.progress["value"] = 0

        for idx, file in enumerate(pdf_files, start=1):
            input_pdf = os.path.join(in_dir, file)
            output_pdf = os.path.join(out_dir, f"Searchable_{file}")

            self.append_log(f"[{idx}/{len(pdf_files)}] Converting: {file}")

            try:
                ocrmypdf.ocr(
                    input_pdf,
                    output_pdf,
                    skip_text=True,   # Keeps existing text layers intact
                    force_ocr=True,   # Performs OCR on scanned image pages
                    progress_bar=False,
                )
                self.append_log(f"   -> Saved: Searchable_{file}")
            except Exception as e:
                self.append_log(f"   -> ERROR processing {file}: {e}")

            self.progress["value"] = idx

        self.append_log(f"\nCompleted! All searchable PDFs are saved in:\n{os.path.abspath(out_dir)}")
        messagebox.showinfo("Complete", f"Conversion completed!\nSaved to:\n{out_dir}")
        self.btn_start.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFConverterGUI(root)
    root.mainloop()
