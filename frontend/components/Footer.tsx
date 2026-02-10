export default function Footer() {
  return (
    <footer className="border-t border-[var(--valo-gray-light)] bg-[var(--valo-darker)]/80 backdrop-blur-md px-6 py-4 mt-auto relative">
      {/* Animated accent line at top */}
      <div className="accent-line absolute top-0 left-0 right-0" />

      <div className="flex items-center justify-between text-xs text-[var(--valo-text-dim)]">
        <div>
          <span className="text-[var(--valo-text)] font-semibold">PaperPlane</span> © {new Date().getFullYear()} •
          <span className="ml-1">Automated Job Application System</span>
        </div>

        <div className="text-right max-w-xl">
          <p>
            PaperPlane is an open-source project that automates job applications.
            Built with Next.js, FastAPI, and Playwright.
          </p>
        </div>
      </div>
    </footer>
  );
}
