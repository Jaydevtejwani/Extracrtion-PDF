pip install pdf2image pytesseract opencv-python numpy pillow reportlab ocrmypdf
import io
import os
import threading
import cv2
import numpy as np
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import reportlab.pdfgen.canvas
from reportlab.lib.units import inch

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Set Tesseract binary path if not in system environment (uncomment & modify if needed):
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# ----------------------------------------------------
# 1. Advanced OpenCV Image Pre-processing Engine
# ----------------------------------------------------
def preprocess_image_advanced(pil_img):
    """Enhances low-quality, dark, or noisy scans for maximum OCR accuracy."""
    # Convert PIL Image to OpenCV Format (BGR)
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    # 1. Convert to Grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 2. Rescale/Denoise (Bilateral Filter preserves text edges while removing noise)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # 3. Contrast Stretching / CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(denoised)

    # 4. Adaptive Thresholding (Binarization for clean black & white text)
    binary = cv2.adaptiveThreshold(
        contrast,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        15,
    )

    # Convert back to PIL Image
    return Image.fromarray(binary)


# ----------------------------------------------------
# 2. Searchable PDF Generator from Images + OCR
# ----------------------------------------------------
def create_searchable_pdf_custom(input_pdf_path, output_pdf_path):
    """Converts PDF pages into images, cleans them, extracts text coordinates,

    and generates a crystal-clear searchable PDF.
    """
    # Convert PDF to high-res images (300 DPI)
    pages = convert_from_path(input_pdf_path, dpi=300)
    pdf_bytes_list = []

    for page_img in pages:
        # Pre-process page image
        cleaned_img = preprocess_image_advanced(page_img)

        # Extract hOCR data from Tesseract
        hocr_data = pytesseract.image_to_pdf_or_hocr(
            cleaned_img, extension="pdf", config="--oem 1 --psm 6"
        )
        pdf_bytes_list.append(hocr_data)

    # Combine generated PDF page bytes into a single output file
    with open(output_pdf_path, "wb") as f_out:
        if len(pdf_bytes_list) == 1:
            f_out.write(pdf_bytes_list[0])
        else:
            # Use PyPDF/pypdf or ocrmypdf fallback if multi-page merge is needed
            from pypdf import PdfMerger

            merger = PdfMerger()
            for pdf_bytes in pdf_bytes_list:
                merger.append(io.BytesIO(pdf_bytes))
            merger.write(f_out)
            merger.close()


# ----------------------------------------------------
# 3. Tkinter GUI Application
# ----------------------------------------------------
class AdvancedPDFConverterGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("Enterprise Scanned PDF to Searchable PDF Converter")
        self.root.geometry("680x520")
        self.root.resizable(False, False)

        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        # Input Frame
        frame_in = ttk.LabelFrame(
            self.root, text=" 1. Select Input Folder (Scanned PDFs) ", padding=10
        )
        frame_in.pack(fill="x", padx=15, pady=10)

        ttk.Entry(frame_in, textvariable=self.input_folder, width=54).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            frame_in, text="Browse Folder", command=self.browse_input
        ).pack(side="left")

        # Output Frame
        frame_out = ttk.LabelFrame(
            self.root,
            text=" 2. Select Output Folder (Searchable PDFs) ",
            padding=10,
        )
        frame_out.pack(fill="x", padx=15, pady=10)

        ttk.Entry(frame_out, textvariable=self.output_folder, width=54).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(
            frame_out, text="Browse Folder", command=self.browse_output
        ).pack(side="left")

        # Start Button
        self.btn_start = ttk.Button(
            self.root,
            text="Start Advanced Processing Pipeline",
            command=self.start_conversion,
        )
        self.btn_start.pack(pady=10)

        # Progress Bar
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", mode="determinate", length=640
        )
        self.progress.pack(padx=15, pady=5)

        # Log Frame
        frame_log = ttk.LabelFrame(
            self.root, text=" Processing Log ", padding=10
        )
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

    def append_log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
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

        threading.Thread(
            target=self.process_conversion,
            args=(in_dir, out_dir),
            daemon=True,
        ).start()

    def process_conversion(self, in_dir, out_dir):
        pdf_files = [f for f in os.listdir(in_dir) if f.lower().endswith(".pdf")]

        if not pdf_files:
            self.append_log("No PDF files found in the input folder.")
            self.btn_start.config(state="normal")
            return

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        self.append_log(
            f"Found {len(pdf_files)} PDF file(s). Starting Advanced Pipeline...\n"
        )
        self.progress["maximum"] = len(pdf_files)
        self.progress["value"] = 0

        for idx, file in enumerate(pdf_files, start=1):
            input_pdf = os.path.join(in_dir, file)
            output_pdf = os.path.join(out_dir, f"Searchable_{file}")

            self.append_log(
                f"[{idx}/{len(pdf_files)}] Pre-processing & Converting: {file}"
            )

            try:
                # Primary Strategy: OpenCV Image Cleaning + Direct Tesseract PDF Generation
                create_searchable_pdf_custom(input_pdf, output_pdf)
                self.append_log(
                    f"   -> SUCCESS: Saved Searchable_{file} using OpenCV + Tesseract Engine"
                )
            except Exception as e_primary:
                self.append_log(
                    f"   -> Primary Engine failed ({e_primary}). Attempting fallback engine..."
                )
                try:
                    # Secondary Strategy: ocrmypdf Engine Fallback
                    import ocrmypdf

                    ocrmypdf.ocr(
                        input_pdf,
                        output_pdf,
                        force_ocr=True,
                        deskew=True,
                        progress_bar=False,
                    )
                    self.append_log(
                        f"   -> SUCCESS: Saved Searchable_{file} via Fallback Engine"
                    )
                except Exception as e_fallback:
                    self.append_log(
                        f"   -> ERROR: Failed both conversion methods for {file}: {e_fallback}"
                    )

            self.progress["value"] = idx

        self.append_log(
            f"\nAll files processed! Output folder:\n{os.path.abspath(out_dir)}"
        )
        messagebox.showinfo(
            "Complete", f"Conversion completed!\nSaved to:\n{out_dir}"
        )
        self.btn_start.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedPDFConverterGUI(root)
    root.mainloop()
