import React from 'react';
import ReactMarkdown from 'react-markdown';

interface EnhancedMarkdownProps {
  children: string;
  className?: string;
}

const EnhancedMarkdown: React.FC<EnhancedMarkdownProps> = ({ children, className }) => {
  // Process the entire text to find and replace URLs, emails, and phone numbers
  const processText = (text: string) => {
    let result = text;

    // Step 1: Fix malformed markdown links from backend (e.g., "text](url)" -> "[text](url)")
    // This handles cases where the opening bracket is missing
    result = result.replace(/([^[\n])([\w\s,.-]+)\]\((https?:\/\/[^)\s]+)\)/g, (match, before, linkText, url) => {
      // If there's text before the link text and it's not already a bracket
      if (before && before !== '[') {
        return `${before}[${linkText}](${url})`;
      }
      return match;
    });

    // Step 2: Fix cases where link text ends with extra parentheses (e.g., "link](url))")
    result = result.replace(/\[([^\]]+)\]\(([^)]+)\)\)+/g, '[$1]($2)');

    // Simple but effective regex patterns
    const patterns = [
      // URLs - must start with http/https, exclude trailing punctuation
      // Skip if already in markdown link format
      {
        regex: /(?<!\]\()(?<!\[)(https?:\/\/[^\s\]]+?)(?=[.!?;,]*(?:\s|$))/g,
        replacement: (match: string) => `[${match}](${match})`
      },
      // Emails
      {
        regex: /(?<!\]\()([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g,
        replacement: (match: string) => `[${match}](mailto:${match})`
      },
      // Phone numbers - match international numbers with various separators
      {
        regex: /(\+\d{1,4}[\s\-\(\)]*\d{1,4}[\s\-\(\)]*\d{3}[\s\-]*\d{3}[\s\-]*\d{4})/g,
        replacement: (match: string) => {
          const cleanPhone = match.replace(/[\s\-\(\)]/g, '');
          return `[${match}](tel:${cleanPhone})`;
        }
      }
    ];

    // Apply each pattern
    patterns.forEach(pattern => {
      result = result.replace(pattern.regex, pattern.replacement);
    });

    return result;
  };

  const processedText = processText(children);

  return (
    <div className={className}>
      <ReactMarkdown
        components={{
          // Custom components for better styling
          strong: ({ children }) => <strong className="enhanced-bold">{children}</strong>,
          a: ({ href, children }) => {
            const linkText = String(children);
            let linkClass = "enhanced-link";
            
            // Determine link type for styling
            if (href?.startsWith('mailto:')) {
              linkClass += " enhanced-email";
            } else if (href?.startsWith('tel:')) {
              linkClass += " enhanced-phone";
            } else if (href?.startsWith('http')) {
              linkClass += " enhanced-url";
            }
            
            return (
              <a 
                href={href} 
                target={href?.startsWith('http') ? "_blank" : undefined}
                rel={href?.startsWith('http') ? "noopener noreferrer" : undefined}
                className={linkClass}
              >
                {linkText}
              </a>
            );
          },
        }}
      >
        {processedText}
      </ReactMarkdown>
    </div>
  );
};

export default EnhancedMarkdown;