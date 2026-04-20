import type { SidebarIconName } from "./types";

export function SidebarIcon({
  name,
  className,
}: {
  name: SidebarIconName;
  className?: string;
}) {
  if (name === "dashboard") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M4 18.5V8.5l4.2-3.2 3.8 2.6 4.4-3.4L20 7.2v11.3H4Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path d="M8 18.5v-4.3h8v4.3" fill="none" stroke="currentColor" strokeWidth="1.8" />
      </svg>
    );
  }

  if (name === "github") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 3.7a8.8 8.8 0 0 0-2.8 17.1c.4.1.5-.2.5-.4v-1.6c-2.3.5-2.8-1-2.8-1-.4-.8-.9-1.1-.9-1.1-.7-.4.1-.4.1-.4.8.1 1.2.8 1.2.8.7 1.2 1.8.9 2.2.7.1-.5.3-.9.5-1.1-1.9-.2-4-1-4-4.3 0-.9.3-1.6.8-2.2-.1-.2-.4-1 .1-2.1 0 0 .7-.2 2.3.8a8 8 0 0 1 4.2 0c1.6-1 2.3-.8 2.3-.8.5 1.1.2 1.9.1 2.1.5.6.8 1.3.8 2.2 0 3.3-2 4.1-4 4.3.3.2.6.7.6 1.5v2.2c0 .2.1.5.5.4A8.8 8.8 0 0 0 12 3.7Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    );
  }

  if (name === "agents") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="7" r="2.3" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <circle cx="6.5" cy="16" r="2" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <circle cx="17.5" cy="16" r="2" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <path
          d="M10.5 8.8 7.7 14M13.5 8.8l2.8 5.2M8.5 16h7"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    );
  }

  if (name === "mcp") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4" y="6" width="6" height="5" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <rect x="14" y="4" width="6" height="7" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <rect x="9" y="14" width="6" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <path
          d="M10 8.5h4M17 11v3M7 11v3M10.5 17h-1.4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    );
  }

  if (name === "skills") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M7 7.5h10M7 12h10M7 16.5h6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <rect
          x="4.5"
          y="4.5"
          width="15"
          height="15"
          rx="2.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        />
      </svg>
    );
  }

  if (name === "workspaces") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M4.5 7.5A2.5 2.5 0 0 1 7 5h3l1.4 1.8H17a2.5 2.5 0 0 1 2.5 2.5v7.2A2.5 2.5 0 0 1 17 19H7a2.5 2.5 0 0 1-2.5-2.5V7.5Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M7.5 12h9"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
    );
  }

  if (name === "supply") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M10 8H7a3.5 3.5 0 1 0 0 7h3"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <path
          d="M14 16h3a3.5 3.5 0 1 0 0-7h-3"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <path d="M8.5 12h7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }

  if (name === "grid") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4" y="4" width="6" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <rect x="14" y="4" width="6" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <rect x="4" y="14" width="6" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
        <rect x="14" y="14" width="6" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
      </svg>
    );
  }

  if (name === "megaphone") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M15.5 7.5 20 5v12l-4.5-2.5H9.5v-7h6Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          d="M9.5 8v6H6.8a2.3 2.3 0 0 1-2.3-2.3v-1.4A2.3 2.3 0 0 1 6.8 8H9.5Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        />
      </svg>
    );
  }

  if (name === "settings") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 8.2A3.8 3.8 0 1 1 8.2 12 3.8 3.8 0 0 1 12 8.2Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
        />
        <path
          d="M19 12a7 7 0 0 0-.1-1.1l2-1.5-2-3.4-2.4 1a7.8 7.8 0 0 0-1.9-1.1l-.4-2.6h-4l-.4 2.6A7.8 7.8 0 0 0 7.9 7l-2.4-1-2 3.4 2 1.5A7 7 0 0 0 5 12c0 .4 0 .7.1 1.1l-2 1.5 2 3.4 2.4-1a7.8 7.8 0 0 0 1.9 1.1l.4 2.6h4l.4-2.6a7.8 7.8 0 0 0 1.9-1.1l2.4 1 2-3.4-2-1.5c.1-.4.1-.7.1-1.1Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  if (name === "document") {
    return (
      <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M7 4.5h7l3 3V19a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-12.5a2 2 0 0 1 2-2Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path d="M14 4.5V8h3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
        <path d="M8.5 12h7M8.5 15.5h7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }

  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 20.5a8.5 8.5 0 1 0-8.5-8.5A8.5 8.5 0 0 0 12 20.5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M9.7 9.3a2.8 2.8 0 1 1 4.4 2.2c-.9.6-1.6 1.2-1.6 2.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <circle cx="12" cy="17" r="1" fill="currentColor" />
    </svg>
  );
}

export function TopBarIcon() {
  return (
    <svg className="ssc-topbar-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function ChevronIcon() {
  return (
    <svg className="ssc-chevron" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="m8 10 4 4 4-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ButterflyMark() {
  return (
    <svg viewBox="0 0 120 84" className="ssc-butterfly-mark" aria-hidden="true">
      <path d="M57 42c-9-18-28-24-39-19-9 4-13 16-9 26 5 11 18 18 30 16 8-1 14-8 18-23Z" />
      <path d="M63 42c9-18 28-24 39-19 9 4 13 16 9 26-5 11-18 18-30 16-8-1-14-8-18-23Z" />
      <path d="M57 42c-9 18-28 24-39 19-9-4-13-16-9-26 5-11 18-18 30-16 8 1 14 8 18 23Z" />
      <path d="M63 42c9 18 28 24 39 19 9-4 13-16 9-26-5-11-18-18-30-16-8 1-14 8-18 23Z" />
      <path d="M60 24v36" />
      <path d="M60 22c-3-5-7-8-12-10M60 22c3-5 7-8 12-10" />
    </svg>
  );
}
