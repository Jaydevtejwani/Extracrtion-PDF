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


class PDFExtractorApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Scanned PDF Processing & Table Extractor")
        self.root.geometry("700x620")
        self.root.resizable(False, False)

        # Variables
        self.folder_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.action_var = tk.StringVar(value="pytesseract")

        self.setup_ui()

    def setup_ui(self):
        # 1. Input Folder Selection Frame
        frame_input = ttk.LabelFrame(
            self.root, text=" 1. Select Folder Containing Scanned PDFs ", padding=10
        )
        frame_input.pack(fill="x", padx=15, pady=8)

        ttk.Entry(
            frame_input, textvariable=self.folder_path, width=56
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            frame_input, text="Browse Folder", command=self.browse_folder
        ).pack(side="left")

        # 2. Output Path Selection Frame
        self.frame_output = ttk.LabelFrame(
            self.root,
            text=" 2. Output Destination (Excel File / Output Directory) ",
            padding=10,
        )
        self.frame_output.pack(fill="x", padx=15, pady=8)

        ttk.Entry(
            self.frame_output, textvariable=self.output_path, width=56
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            self.frame_output, text="Browse...", command=self.browse_output
        ).pack(side="left")

        # 3. Action Selection Frame
        frame_action = ttk.LabelFrame(
            self.root, text=" 3. Select Action ", padding=10
        )
        frame_action.pack(fill="x", padx=15, pady=8)

        ttk.Radiobutton(
            frame_action,
            text="Extract Table Data to Excel (PyTesseract OCR)",
            variable=self.action_var,
            value="pytesseract",
            command=self.update_output_label,
        ).pack(anchor="w", pady=2)

        rb_camelot = ttk.Radiobutton(
            frame_action,
            text="Extract Table Data to Excel (Camelot Engine)",
            variable=self.action_var,
            value="camelot",
            command=self.update_output_label,
        )
        rb_camelot.pack(anchor="w", pady=2)

        rb_ocr_only = ttk.Radiobutton(
            frame_action,
            text="Convert Scanned PDFs to Searchable PDFs (Save as PDF files)",
            variable=self.action_var,
            value="ocr_only",
            command=self.update_output_label,
        )
        rb_ocr_only.pack(anchor="w", pady=2)

        if not CAMELOT_AVAILABLE:
            rb_camelot.config(state="disabled")
            rb_ocr_only.config(state="disabled")

        # Start Processing Button
        self.btn_start = ttk.Button(
            self.root,
            text="Start Processing",
            command=self.start_processing,
        )
        self.btn_start.pack(pady=10)

        # Progress Bar
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", mode="determinate", length=660
        )
        self.progress.pack(padx=15, pady=5)

        # Processing Log Display
        frame_log = ttk.LabelFrame(self.root, text=" Output Log ", padding=10)
        frame_log.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_text = tk.Text(frame_log, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def update_output_label(self):
        action = self.action_var.get()
        folder = self.folder_path.get().strip()

        if action in ["pytesseract", "camelot"]:
            self.frame_output.config(text=" 2. Destination Excel File Path ")
            if folder and (
                not self.output_path.get()
                or self.output_path.get().endswith("/")
            ):
                self.output_path.set(
                    os.path.join(folder, "Extracted_PDF_Data.xlsx")
                )
        else:
            self.frame_output.config(
                text=" 2. Output Directory for Searchable PDFs "
            )
            if folder:
                self.output_path.set(os.path.join(folder, "Searchable_PDFs"))

    def browse_folder(self):
        selected = filedialog.askdirectory(title="Select Input Directory")
        if selected:
            self.folder_path.set(selected)
            self.update_output_label()

    def browse_output(self):
        action = self.action_var.get()
        if action in ["pytesseract", "camelot"]:
            selected = filedialog.asksaveasfilename(
                title="Save Output Excel File As",
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx")],
            )
        else:
            selected = filedialog.askdirectory(
                title="Select Output Directory for PDFs"
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
                "Error", "Please specify an output file or folder destination."
            )
            return

        self.btn_start.config(state="disabled")
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

        threading.Thread(
            target=self.run_task,
            args=(folder, output, self.action_var.get()),
            daemon=True,
        ).start()

    def run_task(self, folder, output, action):
        pdf_files = [
            f for f in os.listdir(folder) if f.lower().endswith(".pdf")
        ]

        if not pdf_files:
            self.append_log("No PDF files found in the specified folder.")
            self.btn_start.config(state="normal")
            return

        self.append_log(
            f"Found {len(pdf_files)} PDF file(s). Selected Action: '{action.upper()}'\n"
        )
        self.progress["maximum"] = len(pdf_files)
        self.progress["value"] = 0

        if action == "ocr_only":
            # Action: Convert Scanned PDFs to Searchable PDFs
            if not os.path.exists(output):
                os.makedirs(output)

            for idx, file in enumerate(pdf_files, start=1):
                input_pdf = os.path.join(folder, file)
                output_pdf = os.path.join(output, f"Searchable_{file}")

                self.append_log(
                    f"[{idx}/{len(pdf_files)}] Converting to searchable PDF: {file}"
                )
                try:
                    ocrmypdf.ocr(
                        input_pdf,
                        output_pdf,
                        skip_text=True,
                        force_ocr=True,
                        progress_bar=False,
                    )
                    self.append_log(
                        f"   -> Saved searchable PDF to: {output_pdf}"
                    )
                except Exception as e:
                    self.append_log(f"   -> ERROR processing {file}: {str(e)}")

                self.progress["value"] = idx

            self.append_log(f"\nCompleted! All PDFs saved in:\n{output}")
            messagebox.showinfo("Success", f"Searchable PDFs saved to:\n{output}")

        else:
            # Actions: Extract to Excel
            master_data = []
            for idx, file in enumerate(pdf_files, start=1):
                pdf_path = os.path.join(folder, file)
                self.append_log(
                    f"[{idx}/{len(pdf_files)}] Extracting data: {file}"
                )

                try:
                    if action == "pytesseract":
                        rows = self.extract_with_tesseract(pdf_path, file)
                    else:
                        rows = self.extract_with_camelot(pdf_path, file)

                    master_data.extend(rows)
                    self.append_log(
                        f"   -> Successfully extracted {len(rows)} row(s)."
                    )
                except Exception as e:
                    self.append_log(f"   -> ERROR processing {file}: {str(e)}")

                self.progress["value"] = idx

            if master_data:
                self.append_log("\nWriting extracted data to Excel...")
                df = pd.DataFrame(master_data)
                df.to_excel(output, index=False)
                self.append_log(
                    f"DONE! Data saved to Excel:\n{os.path.abspath(output)}"
                )
                messagebox.showinfo(
                    "Success", f"Extraction finished!\nSaved to: {output}"
                )
            else:
                self.append_log("\nNo data extracted from the files.")
                messagebox.showwarning(
                    "Warning", "No data extracted from PDF files."
                )

        self.btn_start.config(state="normal")

    def extract_with_tesseract(self, pdf_path, filename):
        all_rows = []
        pages = convert_from_path(pdf_path, dpi=300)

        for page_num, page_img in enumerate(pages, start=1):
            text = pytesseract.image_to_string(page_img)

            for line in text.splitlines():
                line_str = line.strip()
                if not line_str:
                    continue

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

    def extract_with_camelot(self, pdf_path, filename):
        all_rows = []
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            temp_pdf_path = temp_pdf.name

        try:
            ocrmypdf.ocr(
                pdf_path,
                temp_pdf_path,
                skip_text=True,
                force_ocr=True,
                progress_bar=False,
            )
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
    app = PDFExtractorApp(root)
    root.mainloop()
