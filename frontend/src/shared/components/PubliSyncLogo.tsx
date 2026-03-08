interface PubliSyncLogoProps {
  collapsed?: boolean;
  size?: 'sm' | 'md' | 'lg';
  /** Use 'dark' for light backgrounds (sidebar), 'light' for dark backgrounds or login pages */
  textColor?: 'white' | 'dark';
}

const SIZES = {
  sm: { icon: 24, font: 16, gap: 6 },
  md: { icon: 32, font: 20, gap: 8 },
  lg: { icon: 48, font: 28, gap: 10 },
} as const;

/**
 * PubliSync SVG logo mark + wordmark.
 * Shows only the icon when `collapsed` is true.
 */
export default function PubliSyncLogo({ collapsed = false, size = 'md', textColor = 'white' }: PubliSyncLogoProps) {
  const { icon, font, gap } = SIZES[size];

  return (
    <span
      className="inline-flex items-center"
      style={{ gap, lineHeight: 1 }}
      aria-label="PubliSync"
    >
      {/* Abstract icon: stylised "P" formed by a rounded square + circle cutout */}
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 48 48"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Background rounded square */}
        <rect x="2" y="2" width="44" height="44" rx="12" fill="#1677ff" />

        {/* Stylised "P" stem */}
        <rect x="14" y="10" width="6" height="28" rx="3" fill="white" />

        {/* Stylised "P" bowl — half circle */}
        <path
          d="M17 10 C17 10, 36 10, 36 22 C36 34, 17 34, 17 22"
          stroke="white"
          strokeWidth="5"
          strokeLinecap="round"
          fill="none"
        />

        {/* Accent dot representing connectivity / sync */}
        <circle cx="34" cy="36" r="4" fill="#60a5fa" />
      </svg>

      {/* Wordmark — hidden when collapsed */}
      {!collapsed && (
        <span
          className={`font-bold whitespace-nowrap ${textColor === 'dark' ? 'text-gray-900' : 'text-white'}`}
          style={{ fontSize: font }}
        >
          PubliSync
        </span>
      )}
    </span>
  );
}
