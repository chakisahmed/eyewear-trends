import Link from "next/link";

import { EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <EmptyState title="Page introuvable" actions={<Link className="btn btn-secondary" href="/">Retour à la vue d&apos;ensemble</Link>}>
      Cet attribut ou cette page n&apos;existe pas dans la taxonomie.
    </EmptyState>
  );
}
