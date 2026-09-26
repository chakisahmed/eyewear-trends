"use client";

import { Icon } from "@/components/icons";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="card error-card" role="alert">
      <Icon name="alert" />
      <div>
        <h2>Impossible d&apos;afficher cette page</h2>
        <p>{error.message || "Une erreur inattendue s'est produite."}</p>
        <button className="btn btn-secondary" type="button" onClick={reset}>
          <Icon name="refresh" />
          Réessayer
        </button>
      </div>
    </div>
  );
}
