import os
import re
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pdf2image import convert_from_path
import pandas as pd
import pytesseract

# Optional imports for Camelot & OCRmyPDF
try:
    import camelot
    import ocrmypdf

    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False


class PDFTableExtractorApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Scanned PDF Table Extractor GUI")
        self.root.geometry("680x580")
        self.root.resizable(False, False)

        # Variables
        self.folder_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.engine_var = tk.StringVar(value="pytesseract")

        self.setup_ui()

    def setup_ui(self):
        # 1. Input Folder Selection Frame
        frame_input = ttk.LabelFrame(
            self.root, text=" 1. Select Folder Containing Scanned PDFs ", padding=10
        )
        frame_input.pack(fill="x", padx=15, pady=8)

        ttk.Entry(
            frame_input, textvariable=self.folder_path, width=54
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            frame_input, text="Browse Folder", command=self.browse_folder
        ).pack(side="left")

        # 2. Output File Selection Frame
        frame_output = ttk.LabelFrame(
            self.root, text=" 2. Destination Excel File Path ", padding=10
        )
        frame_output.pack(fill="x", padx=15, pady=8)

        ttk.Entry(
            frame_output, textvariable=self.output_path, width=54
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            frame_output, text="Save As...", command=self.browse_output
        ).pack(side="left")

        # 3. Extraction Method Selection Frame
        frame_engine = ttk.LabelFrame(
            self.root, text=" 3. Select Extraction Engine ", padding=10
        )
        frame_engine.pack(fill="x", padx=15, pady=8)

        rb_tesseract = ttk.Radiobutton(
            frame_engine,
            text="Method 1: PyTesseract OCR (Recommended for scanned PDFs)",
            variable=self.engine_var,
            value="pytesseract",
        )
        rb_tesseract.pack(anchor="w", pady=2)

        rb_camelot = ttk.Radiobutton(
            frame_engine,
            text="Method 2: Camelot Library (via OCRmyPDF layer generation)",
            variable=self.engine_var,
            value="camelot",
        )
        rb_camelot.pack(anchor="w", pady=2)

        if not CAMELOT_AVAILABLE:
            rb_camelot.config(state="disabled")

        # Start Processing Button
        self.btn_start = ttk.Button(
            self.root,
            text="Start Batch Extraction",
            command=self.start_processing,
        )
        self.btn_start.pack(pady=10)

        # Progress Bar
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", mode="determinate", length=640
        )
        self.progress.pack(padx=15, pady=5)

        # Processing Log Display Area
        frame_log = ttk.LabelFrame(self.root, text=" Output Log ", padding=10)
        frame_log.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_text = tk.Text(frame_log, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def browse_folder(self):
        selected = filedialog.askdirectory(title="Select Input Directory")
        if selected:
            self.folder_path.set(selected)
            if not self.output_path.get():
                self.output_path.set(
                    os.path.join(selected, "Extracted_PDF_Data.xlsx")
                )

    def browse_output(self):
        selected = filedialog.asksaveasfilename(
            title="Save Output Excel File As",
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
        )
        if selected:
            self.output_path.set(selected)

    def append_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def start_processing(self):
        folder = self.folder_path.get().strip()
        output = self.output_path.get().strip()

        if not folder or not os.path.exists(folder):
            messagebox.showerror(
                "Error", "Please select a valid folder containing PDF files."
            )
            return

        if not output:
            messagebox.showerror(
                "Error", "Please specify a destination path for the Excel file."
            )
            return

        self.btn_start.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

        # Run task in a background thread to prevent UI freezing
        threading.Thread(
            target=self.run_extraction_task,
            args=(folder, output, self.engine_var.get()),
            daemon=True,
        ).start()

    def run_extraction_task(self, folder, output, engine):
        pdf_files = [
            f for f in os.listdir(folder) if f.lower().endswith(".pdf")
        ]

        if not pdf_files:
            self.append_log("No PDF files found in the specified directory.")
            self.btn_start.config(state="normal")
            return

        self.append_log(
            f"Found {len(pdf_files)} PDF file(s). Engine: '{engine.upper()}'\n"
        )
        master_data = []

        self.progress["maximum"] = len(pdf_files)
        self.progress["value"] = 0

        for idx, file in enumerate(pdf_files, start=1):
            pdf_path = os.path.join(folder, file)
            self.append_log(f"[{idx}/{len(pdf_files)}] Processing file: {file}")

            try:
                if engine == "pytesseract":
                    rows = self.extract_with_tesseract(pdf_path, file)
                else:
                    rows = self.extract_with_camelot(pdf_path, file)

                master_data.extend(rows)
                self.append_log(f"   -> Successfully extracted {len(rows)} row(s).")
            except Exception as e:
                self.append_log(f"   -> ERROR processing {file}: {str(e)}")

            self.progress["value"] = idx

        if master_data:
            self.append_log("\nWriting data to Excel...")
            df = pd.DataFrame(master_data)
            df.to_excel(output, index=False)
            self.append_log(
                f"DONE! Data successfully exported to:\n{os.path.abspath(output)}"
            )
            messagebox.showinfo("Success", f"Extraction finished!\nSaved to: {output}")
        else:
            self.append_log("\nNo data could be extracted from the provided files.")
            messagebox.showwarning(
                "Warning", "No data extracted from PDF files."
            )

        self.btn_start.config(state="normal")

    # ----------------------------------------------------
    # Method 1: PyTesseract Engine
    # ----------------------------------------------------
    def extract_with_tesseract(self, pdf_path, filename):
        all_rows = []
        pages = convert_from_path(pdf_path, dpi=300)

        for page_num, page_img in enumerate(pages, start=1):
            text = pytesseract.image_to_string(page_img)

            for line in text.splitlines():
                line_str = line.strip()
                if not line_str:
                    continue

                # Split row items by 2 or more space gaps
                columns = re.split(r"\s{2,}", line_str)

                row = {
                    "File Name": filename,
                    "Page No": page_num,
                    "Raw Line Text": line_str,
                }

                for idx, col in enumerate(columns, start=1):
                    row[f"Column_{idx}"] = col

                all_rows.append(row)

        return all_rows

    # ----------------------------------------------------
    # Method 2: Camelot Engine (with OCR Pre-processing)
    # ----------------------------------------------------
    def extract_with_camelot(self, pdf_path, filename):
        all_rows = []
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf_path = temp_pdf.name

        try:
            # Step 1: Create searchable PDF via OCRmyPDF
            ocrmypdf.ocr(
                pdf_path,
                temp_pdf_path,
                skip_text=True,
                force_ocr=True,
                progress_bar=False,
            )

            # Step 2: Run Camelot stream extraction
            tables = camelot.read_pdf(temp_pdf_path, pages="all", flavor="stream")

            for table in tables:
                page_num = table.page
                df_table = table.df

                for _, row_series in df_table.iterrows():
                    row_values = row_series.tolist()
                    if not any(str(val).strip() for val in row_values):
                        continue

                    row_dict = {"File Name": filename, "Page No": page_num}
                    for idx, val in enumerate(row_values, start=1):
                        row_dict[f"Column_{idx}"] = str(val).strip()

                    all_rows.append(row_dict)
        finally:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

        return all_rows


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFTableExtractorApp(root)
    root.mainloop()