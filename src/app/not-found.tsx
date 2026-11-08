import { ButtonLink, Container } from "@/components/ui";

export default function NotFound() {
  return (
    <Container className="flex min-h-[60vh] flex-col items-start justify-center gap-4 py-20">
      <p className="m-0 text-sm font-semibold tracking-[0.08em] text-accent uppercase">404</p>
      <h1 className="m-0 font-display text-4xl font-bold">This page doesn&apos;t exist.</h1>
      <p className="m-0 text-muted">The link may be out of date. Try the projects list instead.</p>
      <div className="flex gap-3">
        <ButtonLink href="/projects">See all projects</ButtonLink>
        <ButtonLink href="/" variant="secondary">
          Home
        </ButtonLink>
      </div>
    </Container>
  );
}
