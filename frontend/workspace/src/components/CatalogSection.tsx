import type { PropsWithChildren } from "react";

interface CatalogSectionProps extends PropsWithChildren {
  title: string;
  description: string;
}

export function CatalogSection({
  title,
  description,
  children,
}: CatalogSectionProps) {
  return (
    <section className="panel">
      <div className="section-head">
        <h2 className="panel-title">{title}</h2>
        <p className="section-copy">{description}</p>
      </div>
      {children}
    </section>
  );
}
