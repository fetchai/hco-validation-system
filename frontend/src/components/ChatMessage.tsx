import React from "react";
import EnhancedMarkdown from "./EnhancedMarkdown";

interface Message {
  id: string;
  text: string;
  sender: "user" | "assistant";
  timestamp: Date;
  image?: File;
  imageUrl?: string;
}

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  // Remove unused formatTime function
  // const formatTime = (timestamp: Date) => {
  //   return timestamp.toLocaleTimeString('en-US', {
  //     hour: '2-digit',
  //     minute: '2-digit'
  //   });
  // };

  const isAssistant = message.sender === "assistant";

  return (
    <div
      className={`mb-3 flex ${
        isAssistant ? "items-start" : "items-end justify-end"
      } text-sm`}
    >
      {isAssistant && (
        <div className="mr-2 mt-1 h-8 w-8 rounded-full bg-[#e0efe4] flex items-center justify-center">
          <img src="/HCO-Logo.avif" alt="HCO" className="h-6 w-auto" />
        </div>
      )}

      <div
        className={`max-w-[80%] rounded-none px-4 py-3 shadow-sm ${
          isAssistant
            ? "bg-white border border-[#e0efe4] text-[#2f5f3b]"
            : "bg-[#4f8f5e] text-white"
        }`}
      >
        {isAssistant && (
          <div className="mb-1 text-xs font-semibold text-[#7aa487] font-quicksand">
            HCO Assistant
          </div>
        )}

        {message.imageUrl && (
          <div className="mb-2">
            <img
              src={message.imageUrl}
              alt="Uploaded certificate"
              className="rounded-none border border-[#e0efe4] max-h-48 object-contain"
            />
            <div className="mt-1 flex justify-between text-[11px] text-[#7aa487] font-quicksand">
              <span>{message.image?.name}</span>
              {message.image && (
                <span>{`${(message.image.size / 1024 / 1024).toFixed(
                  2
                )} MB`}</span>
              )}
            </div>
          </div>
        )}

        {message.text && (
          <div className="prose prose-sm max-w-none">
            <EnhancedMarkdown className={isAssistant ? "" : ""}>
              {message.text}
            </EnhancedMarkdown>
          </div>
        )}

        {!isAssistant && (
          <div className="mt-1 text-[11px] opacity-80 text-right font-quicksand">
            You
          </div>
        )}
      </div>

      {!isAssistant && (
        <div className="ml-2 mb-1 h-7 w-7 rounded-full bg-[#e0efe4] flex items-center justify-center text-[#4f8f5e]">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>
        </div>
      )}
    </div>
  );
};

export default ChatMessage;
