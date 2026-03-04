import React, { useState, useRef } from "react";

interface ChatInputProps {
  onSendMessage: (text: string, files?: File[]) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage }) => {
  const [message, setMessage] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() || selectedFiles.length > 0) {
      onSendMessage(
        message,
        selectedFiles.length > 0 ? selectedFiles : undefined
      );
      setMessage("");
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const validateAndAddFiles = (files: FileList | File[]) => {
    const validFiles: File[] = [];
    const allowedTypes = [
      "image/jpeg",
      "image/jpg",
      "image/png",
      "image/gif",
      "application/pdf",
      "text/csv",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ];
    const maxSize = 10 * 1024 * 1024; // 10MB

    const fileArray = Array.from(files);
    for (const file of fileArray) {
      if (!allowedTypes.includes(file.type)) {
        alert(
          `File "${file.name}" is not supported. Please upload image files (JPG, PNG, GIF), PDF documents, or data files (CSV, Excel).`
        );
        continue;
      }

      if (file.size > maxSize) {
        alert(
          `File "${file.name}" is too large. File size must be less than 10MB.`
        );
        continue;
      }

      validFiles.push(file);
    }

    if (validFiles.length > 0) {
      setSelectedFiles((prevFiles) => [...prevFiles, ...validFiles]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files) {
      validateAndAddFiles(files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      validateAndAddFiles(files);
    }
  };

  const removeFile = (indexToRemove: number) => {
    setSelectedFiles((prevFiles) =>
      prevFiles.filter((_, index) => index !== indexToRemove)
    );
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const textarea = e.target;
    setMessage(textarea.value);

    // Auto-resize textarea
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 80)}px`;
  };

  return (
    <div className="space-y-2">
      {selectedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1 sm:gap-2 mb-1">
          {selectedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 text-xs rounded-full bg-[#e8f5ed] text-[#2f5f3b] font-quicksand"
            >
              <span>
                {file.type.startsWith("image/")
                  ? "🖼️"
                  : file.type.includes("csv") ||
                    file.type.includes("excel") ||
                    file.type.includes("sheet")
                  ? "📊"
                  : "📄"}
              </span>
              <span className="max-w-[100px] sm:max-w-[140px] truncate text-xs">{file.name}</span>
              <button
                type="button"
                className="text-[#c85c5c] text-sm hover:text-red-600"
                onClick={() => removeFile(index)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div 
          className={`flex items-end gap-2 p-2 sm:p-3 rounded-lg transition-all duration-200 relative ${
            isDragOver 
              ? 'bg-[#e8f5ed] border-2 border-dashed border-[#4f8f5e]' 
              : 'bg-transparent'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {isDragOver && (
            <div className="absolute inset-0 flex items-center justify-center bg-[#e8f5ed] bg-opacity-90 rounded-lg z-10 pointer-events-none">
              <div className="text-[#4f8f5e] text-center">
                <div className="text-xl sm:text-2xl mb-1 sm:mb-2">📁</div>
                <div className="text-xs sm:text-sm font-medium">Drop files here</div>
                <div className="text-xs text-[#7aa487]">CSV, Excel, Images, PDF</div>
              </div>
            </div>
          )}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept="image/*,.pdf,.csv,.xls,.xlsx"
            multiple
            style={{ display: "none" }}
          />

          <button
            type="button"
            className="h-8 w-8 sm:h-10 sm:w-10 flex items-center justify-center rounded-full border border-[#4f8f5e] text-[#4f8f5e] hover:bg-[#4f8f5e] hover:text-white transition-colors"
            onClick={() => fileInputRef.current?.click()}
            title="Attach file or drag & drop files here"
          >
            <svg
              width="16"
              height="16"
              className="sm:w-5 sm:h-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>

          <div className="flex-1">
            <textarea
              value={message}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Message HCO Assistant..."
              className="w-full resize-none bg-[#e8f0eb] text-[#4f8f5e] px-3 sm:px-4 py-2 rounded-none text-xs sm:text-sm placeholder-[#9bb7a4] outline-none font-quicksand"
              rows={1}
              maxLength={2000}
            />
          </div>

          <button
            type="submit"
            className={`h-8 sm:h-10 px-3 sm:px-5 inline-flex items-center justify-center text-xs sm:text-sm font-medium font-quicksand rounded-none transition-colors ${
              !message.trim() && selectedFiles.length === 0
                ? "bg-[#b8cbbf] text-white cursor-not-allowed"
                : "bg-[#4f8f5e] text-white hover:bg-[#3f724d]"
            }`}
            disabled={!message.trim() && selectedFiles.length === 0}
          >
            <svg width="14" height="14" className="sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none">
              <path
                d="M7 11l5-5m0 0l5 5m-5-5v12"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInput;
