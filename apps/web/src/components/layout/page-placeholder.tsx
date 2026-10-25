// Temporary body for routes whose real screen lands in a later ticket.
export function PagePlaceholder({
  title,
  ticket,
}: {
  title: string;
  ticket: string;
}) {
  return (
    <section>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="text-muted-foreground mt-2 text-sm">
        Halaman ini akan dikerjakan di {ticket}.
      </p>
    </section>
  );
}
