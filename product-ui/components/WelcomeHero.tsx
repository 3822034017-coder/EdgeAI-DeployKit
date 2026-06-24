import Link from "next/link";

export function WelcomeHero() {
  return (
    <main className="edgeai-welcome-page">
      <section className="welcome-launch-card welcome-launch-card-minimal">
        <h1 className="welcome-minimal-title">Edge AI</h1>

        <Link href="/workspace" className="welcome-launch-button welcome-launch-button-minimal">
          <span>Launch Workspace</span>
          <span className="welcome-arrow">→</span>
        </Link>
      </section>
    </main>
  );
}
