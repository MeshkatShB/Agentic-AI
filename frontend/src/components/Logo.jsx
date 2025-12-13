import React from "react";

/**
 * Logo component combining Shield (Privacy First) and Chatbot/AI (Locality Second)
 * Represents the motto: "Privacy First, Locality Second"
 */
const Logo = ({ className = "w-6 h-6", color = "currentColor" }) => {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Shield base - Privacy First (outer layer) */}
      <path
        d="M32 8L12 16V30C12 42 20 52 32 56C44 52 52 42 52 30V16L32 8Z"
        fill={color}
        fillOpacity="0.9"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Shield inner detail - adds depth */}
      <path
        d="M32 12L16 18.5V30C16 40 22.5 48 32 51C41.5 48 48 40 48 30V18.5L32 12Z"
        fill="none"
        stroke={color}
        strokeWidth="1"
        strokeOpacity="0.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Chatbot/AI head - Locality Second (inside shield) */}
      <circle
        cx="32"
        cy="28"
        r="8"
        fill={color}
        fillOpacity="0.3"
        stroke={color}
        strokeWidth="1.5"
      />

      {/* AI eyes - representing intelligence */}
      <circle cx="29" cy="26" r="1.5" fill={color} />
      <circle cx="35" cy="26" r="1.5" fill={color} />

      {/* AI mouth/chat indicator */}
      <path
        d="M28 30C28 30 29.5 32 32 32C34.5 32 36 30 36 30"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* Chat message bubble - representing communication */}
      <path
        d="M32 36L28 40L32 44L36 40L32 36Z"
        fill={color}
        fillOpacity="0.7"
      />

      {/* Small dots - representing data/processing (locality) */}
      <circle cx="24" cy="38" r="1" fill={color} fillOpacity="0.5" />
      <circle cx="40" cy="38" r="1" fill={color} fillOpacity="0.5" />
    </svg>
  );
};

export default Logo;
