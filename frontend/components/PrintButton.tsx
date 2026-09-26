"use client";

import { Icon } from "./icons";

export function PrintButton() {
  return (
    <button className="btn btn-primary" type="button" onClick={() => window.print()}>
      <Icon name="printer" />
      <span>Imprimer / PDF</span>
    </button>
  );
}
